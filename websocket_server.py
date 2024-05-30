import asyncio
import json
import argparse
import websockets
import redis.asyncio as redis

STOPWORD = "[|END_OF_STREAM|]"
TOKEN_STREAM = "token_stream"


r = redis.from_url("redis://localhost")


async def handler(websocket):
    async with r.pubsub() as pubsub:
        socket_session_id = await websocket.recv()
        print(f"<<< Got web socket session id: {socket_session_id}")

        channel = f'{TOKEN_STREAM}:{socket_session_id}'

        await pubsub.subscribe(channel)
        
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message is not None:
                text = message["data"].decode()

                if text == STOPWORD:
                    message = json.dumps({'event': 'end_of_stream', 'data': text})
                else:
                    message = json.dumps({'event': 'tokens_arrived', 'data': text})
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

    args = parser.parse_args()

    asyncio.run(main(args.host, args.port))
