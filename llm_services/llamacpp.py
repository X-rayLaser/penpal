import subprocess
import threading
import requests
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


class LLMManager:
    def __init__(self):
        self.executable_path = ""
        self.model_path = ""
        self.host = ""
        self.port = ""

        self.process = None
        self.printing_thread = None

    def setup(self, exec_path, model_path, host, port, num_gpu_layers=0):
        self.executable_path = exec_path
        self.model_path = model_path
        self.host = host
        self.port = str(port)
        self.num_gpu_layers = str(num_gpu_layers)

    def generate(self, data, content_type):
        if self.process is None:
            self.restart_llm()

        url = f"http://localhost:{self.port}/completion"
        headers = {'Content-Type': content_type}

        resp = self.post_with_retries(url, data, headers)
        for line in resp.iter_lines():
            if line:
                line = line.decode() + '\n'
                yield line

    def post_with_retries(self, url, data, headers):
        while True:
            try:
                return requests.post(url, data=data, headers=headers, stream=True)
            except requests.exceptions.ConnectionError:
                print(f"Connection error when posting to {url}")
                time.sleep(1)

    def restart_llm(self):
        popen_args = [
            self.executable_path,
            "-m", self.model_path,
            "-ngl", self.num_gpu_layers,
            "--host", self.host,
            "--port", self.port
        ]

        if self.process is not None:
            self.process.terminate()
            self.printing_thread.join()

        self.process = subprocess.Popen(popen_args,
                        universal_newlines=True,
                        stdout=subprocess.PIPE)

        self.printing_thread = PrintingThread(self.process)
        self.printing_thread.start()


class PrintingThread(threading.Thread):
    def __init__(self, proc, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proc = proc

    def run(self):
        stdout_printer = StandardStreamPrinter(self.proc.stdout, "LLM server")

        while self.proc.poll() is None and stdout_printer.in_progress:
            stdout_printer.print_next_line()
        
        self.proc.stdout.close()


class StandardStreamPrinter:
    def __init__(self, stream, display_name):
        self.stream_iterator = iter(stream.readline, "")
        self.display_name = display_name
        self.in_progress = True

    def print_next_line(self):
        try:
            line = next(self.stream_iterator)
            if line:
                print(f"{self.display_name:12}{line}")
        except StopIteration:
            self.in_progress = False


llm_manager = LLMManager()


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.protocol_version = 'HTTP/1.0'

        if self.path == '/clear-context':
            self.handle_clear_context()
        elif self.path == '/completion':
            self.handle_completion()
        else:
            print("Unsupprted path", self.path)
            self.send_response(404)
            self.end_headers()

    def handle_clear_context(self):
        print("Restarting LLM server...")
        llm_manager.restart_llm()
        print("LLM server restarted")
        self.send_response(200)
        self.end_headers()

    def handle_completion(self):
        content_type = self.headers.get('Content-Type', 'application/json')
        content_len = int(self.headers.get('Content-Length'))

        json_data = self.rfile.read(content_len)
        json_data = json_data.decode("utf-8")
        print("Got content type", content_type)
        print("Got data", json_data)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        for line in llm_manager.generate(json_data, content_type):
            print("Got line:", line)
            self.wfile.write(bytes(line, encoding='utf-8'))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("model", type=str)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--ngl", type=int, default=0)
    args = parser.parse_args()

    llm_manager.setup(exec_path="./llama.cpp/server",
                      model_path=args.model,
                      host="localhost",
                      port=9500,
                      num_gpu_layers=args.ngl)

    server = HTTPServer((args.host, args.port), HttpHandler)
    server.serve_forever()
