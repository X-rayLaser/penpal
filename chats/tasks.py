import threading
import time
from queue import Queue
import json
import os
from celery import shared_task
import redis
from django.core.files.base import ContentFile
import llm_utils
import tts
from chats.models import SpeechSample, Message
from tools.api_calls import (
    find_api_call,
    make_api_call,
    ApiFunctionCall,
    ApiCallNotFoundError
)

from tools import get_specification

TOKEN_STREAM = 'token_stream'
SPEECH_CHANNEL = 'speech_stream'
STOPWORD = "[|END_OF_STREAM|]"
STOP_SPEECH = "[|END_OF_SPEECH|]"


def synthesize_speech(text):
    speech_data = tts.tts_backend(text)
    sample = SpeechSample()
    if speech_data:
        audio_file = ContentFile(speech_data, name="tts-audio-file.wav")
        sample.audio = audio_file
        sample.text = text
        sample.save()
    return sample


class Consumer(threading.Thread):
    def __init__(self, queue, redis_bus, socket_session_id):
        super().__init__()
        self.queue = queue
        self.redis_bus = redis_bus
        self.session_id = socket_session_id

    def run(self):
        speech_channel = f'{SPEECH_CHANNEL}:{self.session_id}'
        while True:
            sentence = self.queue.get()
            if sentence == '':
                self.queue.task_done()
                break

            
            t0 = time.time()
            try:
                sample = synthesize_speech(sentence)
            except Exception as e:
                url = None
                sample_id = None
            else:
                url = sample.get_absolute_url()
                sample_id = sample.pk

            elapsed = time.time() - t0
            message = dict(text=sentence, url=url, gen_time_seconds=elapsed, id=sample_id)
            self.redis_bus.publish(speech_channel, json.dumps(message))
            self.queue.task_done()


def parse_attachment(attachment):
    print("parsing attachment")
    name = attachment.original_name

    # todo: support pdf, csv and other document files
    content = ''
    _, extension = os.path.splitext(name)
    if extension == '.txt':
        with open(attachment.file.path) as f:
            content = f.read()
            print(content)
    elif extension in ['.csv']:
        print("Csv documents are not supported")
    elif extension == '.pdf':
        print("PDF files are not supported")

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


@shared_task
def generate_llm_response(generation_spec_dict, socket_session_id):
    generation_spec = llm_utils.GenerationSpec(**generation_spec_dict)
    token_channel = f'{TOKEN_STREAM}:{socket_session_id}'

    attachments_text = ""
    id = generation_spec.parent_message_id

    launch_params = generation_spec.inference_config.get('launch_params')
    if launch_params and "mmprojector" in launch_params:
        chat_encoder_cls = ChatRendererToList
    else:
        chat_encoder_cls = ChatRendererToString

    if id:
        q = Message.objects.filter(pk=id)
        if q.exists():
            message = q.first()
            for attachment in message.attachments.all():
                attachments_text += parse_attachment(attachment)

            message.attachments_text = attachments_text
            message.save()

            generation_spec.prompt = get_prompt(message, chat_encoder_cls)

    queue = Queue()
    r = redis.Redis()

    consumer = Consumer(queue, r, socket_session_id)
    consumer.start()

    sentence = ''
    generated_text = ''

    while True:
        for token in llm_utils.stream_tokens(generation_spec):
            sentence += token
            generated_text += token

            msg = {'event': 'tokens_arrived', 'data': token}
            r.publish(token_channel, json.dumps(msg))

            if "." in token or "!" in token or "?" in token:
                print("got sentence", sentence)
                queue.put(sentence)
                sentence = ''

        try:
            api_call, offset = find_api_call(generated_text)
            api_call_string = make_api_call(api_call)
            finalized_segment = generated_text[:offset] + api_call_string

            generation_spec.prompt = chat_encoder_cls.concatenate(
                generation_spec.prompt, finalized_segment
            )
            generated_text = ''

            msg = {'event': 'generation_paused', 'data': finalized_segment}
            r.publish(token_channel, json.dumps(msg))
        except ApiCallNotFoundError:
            break

    r.publish(token_channel, STOPWORD)
    queue.put('')
    consumer.join()
    r.publish(f'{SPEECH_CHANNEL}:{socket_session_id}', STOP_SPEECH)