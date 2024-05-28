from celery import shared_task
import redis
import llm_utils


TOKEN_STREAM = 'token_stream'


@shared_task
def generate_llm_response(prompt, inference_config, clear_context, llm_settings, socket_session_id):
    r = redis.Redis()
    channel = f'{TOKEN_STREAM}:{socket_session_id}'
    for token in llm_utils.stream_tokens(prompt, inference_config, clear_context, llm_settings):
        r.publish(channel, token)
    
    r.publish(channel, "")