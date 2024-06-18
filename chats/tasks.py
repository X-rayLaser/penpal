import threading
import time
from queue import Queue
import json
from celery import shared_task
import redis
from django.core.files.base import ContentFile
import llm_utils
import tts
from chats.models import SpeechSample

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


@shared_task
def generate_llm_response(generation_spec_dict, socket_session_id):
    generation_spec = llm_utils.GenerationSpec(**generation_spec_dict)
    token_channel = f'{TOKEN_STREAM}:{socket_session_id}'

    queue = Queue()
    r = redis.Redis()

    consumer = Consumer(queue, r, socket_session_id)
    consumer.start()

    sentence = ''
    for token in llm_utils.stream_tokens(generation_spec):
        sentence += token
        r.publish(token_channel, token)

        if "." in token or "!" in token or "?" in token:
            print("got sentence", sentence)
            queue.put(sentence)
            sentence = ''

    r.publish(token_channel, STOPWORD)
    queue.put('')
    consumer.join()
    r.publish(f'{SPEECH_CHANNEL}:{socket_session_id}', STOP_SPEECH)