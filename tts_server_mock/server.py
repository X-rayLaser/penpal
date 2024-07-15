import json
import os
import argparse

from http.server import HTTPServer, BaseHTTPRequestHandler

default_voice = "voice_sample"
audio_extension = ".wav"
samples_dir = "samples"


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.protocol_version = 'HTTP/1.0'

        if self.path == '/tts/':
            self.handle_tts()
        else:
            print("Unsupprted path", self.path)
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        self.protocol_version = 'HTTP/1.0'

        if self.path == '/voices/':
            self.handle_voices()
        else:
            print("Unsupprted path", self.path)
            self.send_response(404)
            self.end_headers()

    def handle_tts(self):
        content_type = self.headers.get('Content-Type', 'application/json')
        content_len = int(self.headers.get('Content-Length'))

        json_data = self.rfile.read(content_len)
        json_data = json_data.decode("utf-8")

        data_dict = json.loads(json_data)
        text = data_dict.get("text")
        voice_id = data_dict.get("voice_id")
        
        audio = self.read_speaker_file(text, voice_id)

        self.send_response(200)
        self.send_header("Content-Length", len(audio))
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()

        if audio:
            self.wfile.write(audio)

    def read_speaker_file(self, text, voice_id):
        audio = b""
        voice_id = voice_id or default_voice
        
        speaker_wav = os.path.join(samples_dir, voice_id) + audio_extension
        if not os.path.isfile(speaker_wav):
            return audio

        if text:
            with open(speaker_wav, "rb") as f:
                audio = f.read()

        return audio

    def handle_voices(self):
        voices = [name.rstrip(audio_extension) for name in os.listdir(samples_dir) if name.endswith(audio_extension)]
        self.send_json_response(status_code=200, response_data=voices)

    def send_json_response(self, status_code, response_data, encoding='utf-8'):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        response_json = json.dumps(response_data)
        self.wfile.write(bytes(response_json, encoding=encoding))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=str, default='9300')
    
    args = parser.parse_args()

    server = HTTPServer((args.host, int(args.port)), HttpHandler)
    server.serve_forever()