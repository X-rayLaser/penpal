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


class ChatEncoder:
    def __init__(self, templateSpec, useBos=False):
        self.spec = templateSpec
        self.useBos = useBos

    def __call__(self, systemMessage, messages):
        questionTemplate = self.spec['question']
        answerTemplate = self.spec['answer']

        conversation = ''

        system_template = self.spec['systemMessage']

        if systemMessage:
            conversation += system_template.replace('%message', systemMessage)

        for i, msg in enumerate(messages):
            template = questionTemplate if i % 2 == 0 else answerTemplate
            conversation += template.replace('%message', msg)

        conversation = conversation + self.spec['promptSuffix']
        if (self.useBos):
            conversation = self.spec.startOfText + conversation
        return conversation


def get_prompt(message):
    chat_history = [message]
    while message.parent:
        message = message.parent
        chat_history.append(message)

    config = message.chat.configuration
    template_spec = (config and config.template_spec) or chatTemplate

    chat_encoder = ChatEncoder(template_spec)
    
    messages = []
    for msg in reversed(chat_history):
        text = msg.text
        if msg.attachments_text:
            text += msg.attachments_text
        messages.append(text)

    system_message = message.chat.system_message or ''
    return chat_encoder(system_message, messages)


@shared_task
def generate_llm_response(generation_spec_dict, socket_session_id):
    generation_spec = llm_utils.GenerationSpec(**generation_spec_dict)
    token_channel = f'{TOKEN_STREAM}:{socket_session_id}'

    attachments_text = ""
    id = generation_spec.parent_message_id
    if id:
        q = Message.objects.filter(pk=id)
        if q.exists():
            message = q.first()
            for attachment in message.attachments.all():
                attachments_text += parse_attachment(attachment)

            message.attachments_text = attachments_text
            message.save()
            generation_spec.prompt = get_prompt(message)

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

            new_prompt = generation_spec.prompt + finalized_segment + chatTemplate['continuationPrefix']
            generation_spec.prompt = new_prompt
            generated_text = ''

            msg = {'event': 'generation_paused', 'data': finalized_segment}
            r.publish(token_channel, json.dumps(msg))
        except ApiCallNotFoundError:
            break

    r.publish(token_channel, STOPWORD)
    queue.put('')
    consumer.join()
    r.publish(f'{SPEECH_CHANNEL}:{socket_session_id}', STOP_SPEECH)