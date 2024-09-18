import threading
import time
import uuid
from queue import Queue
import json
import os
import uuid
import traceback
from celery import shared_task
import redis
from pypdf import PdfReader
import markdown
import bleach
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
from pygentify import Agent, OutputDevice, TextCache, WebInterpreter, TooManyRoundsError
from pygentify.llm_backends import LlamaCpp, GenerationSpec as PygentifySpec
from pygentify.messages import JinjaChatFactory
from pygentify.tool_calling import SimpleTagBasedToolUse, tool_registry

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
            content.append({
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


def get_saved_history(last_message):
    message = last_message
    chat_history = [message]
    while message.parent:
        message = message.parent
        chat_history.append(message)

    return list(reversed(chat_history))


def get_system_message(first_message):
    config = first_message.chat.configuration

    system_message = first_message.chat.system_message or ''

    if (config.tools):
        system_message += get_specification(config)
    return system_message


def get_prompt(message, chat_encoder_cls):
    messages = get_saved_history(message)
    first_message = messages[0]
    config = first_message.chat.configuration
    system_message = get_system_message(first_message)

    template_spec = (config and config.template_spec) or chatTemplate
    chat_encoder = chat_encoder_cls(template_spec)
    return chat_encoder(system_message, messages)


class ProcessorDevice(OutputDevice):
    def __init__(self, redis_obj, channel, sentence_processor):
        super().__init__()
        self.redis_obj = redis_obj
        self.channel = channel
        self.cache = TextCache()
        self.generated_text = ''
        self.sentence = ''
        self.sentence_processor = sentence_processor

    def on_token(self, token):
        self.cache.fill(token)

        # todo: save only tokens of text modality
        self.send(token)

    def __call__(self, new_text):
        new_text = self.cache(new_text)
        if new_text:
            new_text += '\n'
        self.send(new_text)

    def send(self, text):
        for ch in text:
            self.sentence += ch

            if ch in ".!?":
                self.sentence_processor.process_sentence(self.sentence)
                self.sentence = ''

        self.generated_text += text
        msg = {'event': 'tokens_arrived', 'data': text}
        self.redis_obj.publish(self.channel, json.dumps(msg))


class PygentifyTextGenerator:
    def __init__(self, redis_obj, tokens_channel):
        self.redis_obj = redis_obj
        self.tokens_channel = tokens_channel

    def __call__(self, generation_spec):
        llm = llm_utils.token_generator
        stop_word = ["<|tool_use_end|>"]
        #stop_word = generation_spec.stop_word # todo: this should work
        llm.set_spec(generation_spec.sampling_config, stop_word)

        output_device = ProcessorDevice(self.redis_obj, self.tokens_channel, self)
        temp_output_device = OutputDevice()
        default_interpreter_class = WebInterpreter

        tools = tool_registry
        agent = Agent(llm, tools=tools, system_message="", output_device=output_device,
                      temp_output_device=temp_output_device,
                      default_interpreter_class=default_interpreter_class, max_rounds=15)

        agent.add_listener("webpack_build_started", self.process_build_start)
        agent.add_listener("webpack_build_finished", self.process_build_finished)
        agent.add_listener("tool_call_started", self.process_tool_call)
        agent.add_listener("tool_call_finished", self.process_tool_result)
        
        agent.history = generation_spec.history[:-1]
        last_msg = generation_spec.history[-1].content.render()
        try:
            agent(last_msg, include_system_message=False, record_prompt=False, self_prompting=False)
        except TooManyRoundsError:
            print("TooManyRoundsError, stopped generating")
            pass

        return output_device.generated_text

    def process_token(self, token):
        pass

    def process_sentence(self, sentence):
        pass

    def process_tool_call(self, name, arg_dict):
        pass

    def process_tool_result(self, name, result, error):
        pass

    def process_api_call_segment(self, text):
        pass

    def process_build_start(self, build_id, files):
        pass

    def process_build_finished(self, build_id, result: dict):
        pass



def fix_linebreaks(s):
    return markdown.markdown(s.replace('\n', '\n\n'), extensions=['fenced_code'])


def format_code(code):
    code = f"```{code}```"
    return markdown.markdown(code, extensions=['fenced_code'])


def format_files(files):
    fixed_files = []
    for f in files:
        name = f['name']
        content = format_code(f['content'])
        fixed_files.append(dict(name=name, content=content))
    return fixed_files


class PygentifyProducer(PygentifyTextGenerator):
    def __init__(self, queue, redis_obj, tokens_channel, builds_channel):
        super().__init__(redis_obj, tokens_channel)
        self.queue = queue
        self.builds_channel = builds_channel

    def process_token(self, token):
        msg = {'event': 'tokens_arrived', 'data': token}
        self.redis_obj.publish(self.tokens_channel, json.dumps(msg))

    def process_sentence(self, sentence):
        self.queue.put(sentence)

    def process_tool_call(self, name, arg_dict):
        self._notify_about_tool_use('tool_call_started', {
            'name': name,
            'arguments': arg_dict
        })

    def process_tool_result(self, name, result=None, error=None):
        self._notify_about_tool_use('tool_call_finished', {
            'name': name,
            'result': result,
            'error': error
        })

    def _notify_about_tool_use(self, event_type, data):
        msg = {'event': event_type, 'data': data}
        self.redis_obj.publish(self.tokens_channel, json.dumps(msg))

    def process_api_call_segment(self, text):
        msg = {'event': 'generation_paused', 'data': text}
        self.redis_obj.publish(self.tokens_channel, json.dumps(msg))

    def process_build_start(self, build_id, files):
        msg = {
            'build_event': 'webpack_build_started',
            'id': build_id,
            'files': format_files(files)
        }
        self.redis_obj.publish(self.builds_channel, json.dumps(msg))

    def process_build_finished(self, build_id, result: dict):
        result = dict(result)
        result["stdout"] = fix_linebreaks(result["stdout"])
        result["stderr"] = fix_linebreaks(result["stderr"])
        result["files"] = format_files(result["files"])

        msg = dict(result)
        msg.update(dict(build_event='webpack_build_finished', id=build_id))
        self.redis_obj.publish(self.builds_channel, json.dumps(msg))


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


def encode_chat_thread(last_message):
    tool_use = SimpleTagBasedToolUse.create_default()
    msg_factory = JinjaChatFactory('llama3', tool_use)
    
    db_history = get_saved_history(last_message)
    system_message = get_system_message(db_history[0])

    history = []
    if system_message:
        msg = msg_factory.create_system_msg(system_message)
        history.append(msg)
    
    for i, db_msg in enumerate(db_history):
        if i % 2 == 0:
            text = db_msg.text
            if db_msg.attachments_text:
                text += db_msg.attachments_text
            msg = msg_factory.create_user_msg(text)
        else:
            msg = msg_factory.create_ai_msg(db_msg.text)
        history.append(msg)
    return history


def generate_response_message(generation_spec_dict, socket_session_id, redis_object):
    generation_spec = llm_utils.GenerationSpec(**generation_spec_dict)
    token_channel = f'{TOKEN_STREAM}:{socket_session_id}'
    builds_channel = f'build_events:{socket_session_id}'

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

    # todo: monkey patching will do for now
    generation_spec.history = encode_chat_thread(message)
    producer = PygentifyProducer(queue, redis_object, token_channel, builds_channel)
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
        traceback.print_exc()
        msg = {'event': 'generation_error', 'data': str(e)}
        redis_object.publish(token_channel, json.dumps(msg))
