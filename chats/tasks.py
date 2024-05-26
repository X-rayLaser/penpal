from celery import shared_task
import redis
import llm_utils


TOKEN_STREAM = 'token_stream:1'


@shared_task
def generate_llm_response(prompt, inference_config, clear_context, llm_settings):
    r = redis.Redis()
    for token in llm_utils.stream_tokens(prompt, inference_config, clear_context, llm_settings):
        r.publish(TOKEN_STREAM, token)
    
    r.publish(TOKEN_STREAM, "")