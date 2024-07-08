import asyncio
import json
import argparse
import websockets
import redis.asyncio as redis
import os

STOPWORD = "[|END_OF_STREAM|]"
TOKEN_STREAM = "token_stream"
SPEECH_STREAM = "speech_stream"
STOP_SPEECH = "[|END_OF_SPEECH|]"


async def handler(websocket):
    async with r.pubsub() as pubsub:
        socket_session_id = await websocket.recv()
        print(f"<<< Got web socket session id: {socket_session_id}")

        token_channel = f'{TOKEN_STREAM}:{socket_session_id}'
        speech_channel = f'{SPEECH_STREAM}:{socket_session_id}'

        await pubsub.subscribe(token_channel, speech_channel)
        
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message is not None:
                text = message["data"].decode()
                channel = message["channel"].decode()

                if channel == token_channel:
                    if text == STOPWORD:
                        message = json.dumps({'event': 'end_of_stream', 'data': text})
                    else:
                        message = text
                elif channel == speech_channel:
                    if text == STOP_SPEECH:
                        message = json.dumps({'event': 'end_of_speech', 'data': text})
                    else:
                        d = json.loads(text)
                        message = json.dumps({
                            'event': 'speech_sample_arrived',
                            'data': d
                        })
                else:
                    print("Unknown channel:", channel)

                print("about to send message", message)
                try:
                    await websocket.send(message)
                except (websockets.ConnectionClosed, websockets.ConnectionClosedOK):
                    print("Connection closed by the client. Quitting")
                    break


async def main(host, port):
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start websockets server")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--redis-host", type=str, default="localhost")
    args = parser.parse_args()

    redis_host = args.redis_host
    print("REDIS_HOST", redis_host)

    redis_host = "redis"

    r = redis.from_url(f"redis://{redis_host}")

    asyncio.run(main(args.host, args.port))
