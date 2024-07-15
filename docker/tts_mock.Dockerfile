FROM python:3.10

COPY ./tts_server_mock /tts_server_mock

WORKDIR /tts_server_mock
CMD ["python", "-u", "server.py", "--port", "9300"]