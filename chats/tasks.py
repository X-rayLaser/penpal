import threading
import time
from queue import Queue
import json
import os
import uuid
import traceback
from celery import shared_task
import redis
from pypdf import PdfReader
from django.core.files.base import ContentFile
from django.conf import settings
import llm_utils
import tts
from chats.models import SpeechSample, Message
from .serializers import MessageSerializer
from tools.api_calls import (
    find_api_call,
    make_api_call,
    ApiFunctionCall,
    ApiCallNotFoundError
)
from .utils import join_wavs
from tools import get_specification

TOKEN_STREAM = 'token_stream'
SPEECH_CHANNEL = 'speech_stream'
STOPWORD = "[|END_OF_STREAM|]"
STOP_SPEECH = "[|END_OF_SPEECH|]"


def synthesize_speech(text, voice_id):
    speech_data = tts.tts_backend.synthesize(text, voice_id)
    if not speech_data:
        raise NoSpeechSampleError()
    
    sample = SpeechSample()
    audio_file = ContentFile(speech_data, name="tts-audio-file.wav")
    sample.audio = audio_file
    sample.text = text
    sample.save()

    return sample


class NoSpeechSampleError(Exception):
    pass


class Consumer(threading.Thread):
    def __init__(self, queue, redis_bus, socket_session_id, voice_id):
        super().__init__()
        self.queue = queue
        self.redis_bus = redis_bus
        self.session_id = socket_session_id
        self.voice_id = voice_id
        self.samples = []

    def run(self):
        speech_channel = f'{SPEECH_CHANNEL}:{self.session_id}'
        while True:
            sentence = self.queue.get()
            if sentence == '' or not self.voice_id:
                self.queue.task_done()
                break

            t0 = time.time()
            try:
                sample = synthesize_speech(sentence, self.voice_id)
                self.samples.append(sample)
            except Exception as e:
                url = None
                sample_id = None
                traceback.print_exc()
            else:
                url = sample.get_absolute_url()
                sample_id = sample.pk

            elapsed = time.time() - t0
            message = dict(text=sentence, url=url, gen_time_seconds=elapsed, id=sample_id)
            self.redis_bus.publish(speech_channel, json.dumps(message))
            self.queue.task_done()


def parse_attachment(attachment):
    name = attachment.original_name

    print("parsing attachment", name)

    allowed_text_files = ['.txt', '.py', '.rb', '.sh', '.cpp', '.c', '.hpp', '.h', '.js', '.html', '.css', '.ts', '.csv']

    # todo: support other document files
    content = ''
    _, extension = os.path.splitext(name)
    extension = extension.lower()
    if extension in allowed_text_files:
        with open(attachment.file.path) as f:
            content = f.read()
    elif extension in ['.xls']:
        print("Excel files are not supported. Ignoring", name)
    elif extension == '.pdf':
        reader = PdfReader(attachment.file.path)
        number_of_pages = len(reader.pages)
        content = ""

        for i in range(number_of_pages):
            page = reader.pages[i]
            content += page.extract_text()
    else:
        print(f"Files with extension '{extension}' are not supported. Ignoring")

    return content and f'{name}\n\n{content}\nEnd of file {name}\n\n'


LLAMA3_START_HEADER_ID = "<|start_header_id|>";
LLAMA3_END_HEADER_ID = "<|end_header_id|>";
LLAMA3_EOT_ID = "<|eot_id|>";


def llamaRoleTemplate(role):
    return f'{LLAMA3_START_HEADER_ID}{role}{LLAMA3_END_HEADER_ID}\n\n%message{LLAMA3_EOT_ID}'


chatTemplate = {
    'question': llamaRoleTemplate("user"),
    'answer': llamaRoleTemplate("assistant"),
    'systemMessage': llamaRoleTemplate("system"),
    'startOfText': "<|begin_of_text|>",
    'promptSuffix': f'{LLAMA3_START_HEADER_ID}assistant{LLAMA3_END_HEADER_ID}\n\n',
    'continuationPrefix': f'{LLAMA3_EOT_ID}{LLAMA3_START_HEADER_ID}assistant{LLAMA3_END_HEADER_ID}\n\n'
}


class ChatRenderer:
    def __init__(self, template_spec, use_bos=False):
        self.spec = template_spec
        self.use_bos = use_bos

    def __call__(self, system_message, messages):
        raise NotImplementedError

    @classmethod
    def concatenate(cls, old_prompt, continuation):
        raise NotImplementedError


class ChatRendererToString(ChatRenderer):
    def __call__(self, system_message, messages):
        questionTemplate = self.spec['question']
        answerTemplate = self.spec['answer']

        conversation = ''

        system_template = self.spec['systemMessage']

        if system_message:
            conversation += system_template.replace('%message', system_message)

        for i, msg in enumerate(messages):
            template = questionTemplate if i % 2 == 0 else answerTemplate
            text = msg.text
            if msg.attachments_text:
                text += msg.attachments_text
            conversation += template.replace('%message', text)

        conversation = conversation + self.spec['promptSuffix']
        if (self.use_bos):
            conversation = self.spec['startOfText'] + conversation
        return conversation

    @classmethod
    def concatenate(cls, old_prompt, continuation):
        return old_prompt + continuation + chatTemplate['continuationPrefix']


class ChatRendererToList(ChatRenderer):
    def __call__(self, system_message, messages):
        result = []

        if system_message:
            result.append(self.render_system_message(system_message))

        for i, msg in enumerate(messages):
            text = msg.text
            if msg.attachments_text:
                text += msg.attachments_text

            render = self.render_user_message if i % 2 == 0 else self.render_ai_message
            result.append(render(msg, text))

        return result

    def render_system_message(self, text):
        return {
            "role": "system",
            "content": text
        }

    def render_user_message(self, msg, text):
        content = [{
            "type": "text",
            "text": text
        }]

        if (msg.image_b64):
            content.push({
                "type": "image_url",
                "image_url": {
                    "url": msg.image_b64
                }
            })

        return {
            "role": "user",
            "content": content
        }

    def render_ai_message(self, msg, text):
        return {
            "role": "assistant",
            "content": [{ "type": "text", "text": text }]
        }

    @classmethod
    def concatenate(cls, old_prompt, continuation):
        new_prompt = old_prompt[:]
        last_message = new_prompt[-1]
        last_message["content"]["text"] += continuation
        return new_prompt


def get_prompt(message, chat_encoder_cls):
    chat_history = [message]
    while message.parent:
        message = message.parent
        chat_history.append(message)

    config = message.chat.configuration
    template_spec = (config and config.template_spec) or chatTemplate

    chat_encoder = chat_encoder_cls(template_spec)

    messages = reversed(chat_history)

    system_message = message.chat.system_message or ''

    if (config.tools):
        system_message += get_specification(config)

    return chat_encoder(system_message, messages)


class ToolAugmentedTextGenerator:
    def __init__(self, chat_renderer_cls):
        self.chat_renderer_cls = chat_renderer_cls

    def __call__(self, generation_spec):
        sentence = ''
        generated_text = ''
        response_text = ''

        while True:
            for token in llm_utils.stream_tokens(generation_spec):
                sentence += token
                generated_text += token
                self.process_token(token)

                if "." in token or "!" in token or "?" in token:
                    self.process_sentence(sentence)
                    sentence = ''

            finalized_segment = self._make_api_call(generated_text)

            if finalized_segment:
                generation_spec.prompt = self.chat_renderer_cls.concatenate(
                    generation_spec.prompt, finalized_segment
                )
                response_text += finalized_segment
                generated_text = ''
            else:
                response_text += generated_text
                break

        return response_text

    def _make_api_call(self, generated_text):
        try:
            api_call, offset = find_api_call(generated_text)
            api_call_string = make_api_call(api_call)
            finalized_segment = generated_text[:offset] + api_call_string
            self.process_api_call_segment(finalized_segment)
            return finalized_segment
        except ApiCallNotFoundError:
            return None

    def process_token(self, token):
        pass

    def process_sentence(self, sentence):
        pass

    def process_api_call_segment(self, text):
        pass


class Producer(ToolAugmentedTextGenerator):
    def __init__(self, queue, redis_obj, redis_channel, chat_renderer_cls):
        super().__init__(chat_renderer_cls)
        self.queue = queue
        self.redis_obj = redis_obj
        self.redis_channel = redis_channel

    def process_token(self, token):
        msg = {'event': 'tokens_arrived', 'data': token}
        self.redis_obj.publish(self.redis_channel, json.dumps(msg))

    def process_sentence(self, sentence):
        self.queue.put(sentence)

    def process_api_call_segment(self, text):
        msg = {'event': 'generation_paused', 'data': text}
        self.redis_obj.publish(self.redis_channel, json.dumps(msg))


def get_last_message(generation_spec):
    id = generation_spec.parent_message_id

    message = None
    if id:
        q = Message.objects.filter(pk=id)
        if q.exists():
            message = q.first()
    
    if not message:
        raise Exception("Cannot generate text without any messages in the history")
    return message


def process_attachments(message):
    if message.attachments_text:
        return

    attachments_text = ""
    for attachment in message.attachments.all():
        try:
            attachments_text += parse_attachment(attachment)
        except UnicodeDecodeError as e:
            print('UnicodeDecodeError while processing file:', attachment.original_name)

    message.attachments_text = attachments_text
    message.save()


def create_response_message(parent, response_text, audio_samples):
    response_message = Message()
    response_message.text = response_text
    response_message.parent = parent

    if audio_samples:
        output_name = f'{uuid.uuid4().hex}.wav'
        output_path = os.path.join(settings.MEDIA_ROOT, output_name)
        audio_data = join_wavs(audio_samples, output_path)
        response_message.audio = ContentFile(audio_data, name="tts-audio-file.wav")

    response_message.save()
    
    return response_message


def generate_response_message(generation_spec_dict, socket_session_id, redis_object):
    generation_spec = llm_utils.GenerationSpec(**generation_spec_dict)
    token_channel = f'{TOKEN_STREAM}:{socket_session_id}'

    message = get_last_message(generation_spec)

    process_attachments(message)

    launch_params = generation_spec.inference_config.get('launch_params')
    if launch_params and "mmprojector" in launch_params:
        chat_renderer_cls = ChatRendererToList
    else:
        chat_renderer_cls = ChatRendererToString

    generation_spec.prompt = get_prompt(message, chat_renderer_cls)

    queue = Queue()

    consumer = Consumer(queue, redis_object, socket_session_id, generation_spec.voice_id)
    consumer.start()

    producer = Producer(queue, redis_object, token_channel, chat_renderer_cls)
    try:
        response_text = producer(generation_spec)
    except Exception as e:
        print('Generation failed:', str(e))
        raise
    finally:
        redis_object.publish(token_channel, STOPWORD)
        queue.put('')
        consumer.join()
        redis_object.publish(f'{SPEECH_CHANNEL}:{socket_session_id}', STOP_SPEECH)

    wav_samples = consumer.samples

    response_message = create_response_message(message, response_text, wav_samples)   
    serializer = MessageSerializer(response_message)
    serialized_msg = serializer.data
    
    msg = {'event': 'generation_complete', 'data': serialized_msg}
    redis_object.publish(token_channel, json.dumps(msg))


@shared_task
def generate_llm_response(generation_spec_dict, socket_session_id):
    token_channel = f'{TOKEN_STREAM}:{socket_session_id}'
    redis_object = redis.Redis(settings.REDIS_HOST)

    try:
        generate_response_message(generation_spec_dict, socket_session_id, redis_object)
    except Exception as e:
        msg = {'event': 'generation_error', 'data': str(e)}
        redis_object.publish(token_channel, json.dumps(msg))
