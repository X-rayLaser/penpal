import subprocess
import threading
import requests
import time
import json
import uuid
import os
from http.server import HTTPServer, BaseHTTPRequestHandler


models_root = "installed_models"
models_registry = os.path.join(models_root, "models_registry.json")


class LLMManager:
    def __init__(self):
        self.executable_path = ""
        self.model_path = ""
        self.host = ""
        self.port = ""
        self.context_size = ""

        self.process = None
        self.printing_thread = None
        self.download_threads = []

        self.downloads = {}

    def setup(self, exec_path, model_path, host, port, num_gpu_layers=0, context_size=512):
        self.executable_path = exec_path
        self.model_path = model_path
        self.host = host
        self.port = str(port)
        self.num_gpu_layers = str(num_gpu_layers)
        self.context_size = str(context_size)

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
            "-c", self.context_size,
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

    def start_download(self, repo_id, file_name):
        download_id = (repo_id, file_name)
        download_info = {
            'repo_id': repo_id,
            'file_name': file_name,
            'finished': False,
            'errors': []
        }
        self.downloads[download_id] = download_info

        download = DownloadThread(download_info, repo_id, file_name)
        self.download_threads.append(download)
        download.start()
        return download_id


class DownloadThread(threading.Thread):
    def __init__(self, download_info, repo_id, file_name):
        super().__init__()
        self.download_info = download_info
        self.repo_id = repo_id
        self.file_name = file_name

        self.download_path = ''

    def run(self) -> None:
        time.sleep(10)

        with threading.Lock():
            self.download_info['finished'] = True

            os.makedirs(models_root, exist_ok=True)

            if not os.path.exists(models_registry):
                with open(models_registry, "w") as f:
                    f.write(json.dumps([]))

            with open(models_registry) as f:
                content = f.read()
                entries = json.loads(content)

            metadata = dict(repo_id=self.repo_id, file_name=self.file_name)
            entries.append(metadata)

            with open(models_registry, "w") as f:
                entries_json = json.dumps(entries)
                f.write(entries_json)


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
            # when running llama.cpp server, clearing context is unnecessary
            self.send_response(200)
            self.end_headers()
        elif self.path == '/completion':
            self.handle_completion()
        elif self.path == '/download-llm':
            self.handle_download()
        elif self.path == '/download-status':
            self.handle_download_status()
        else:
            print("Unsupprted path", self.path)
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        self.protocol_version = 'HTTP/1.0'

        if self.path == '/downloads-in-progress':
            self.handle_downloads_inprogress()
        elif self.path == '/list-models':
            self.handle_list_models()
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

    def handle_download(self):
        body = self.parse_json_body()
        repo_id = body.get('repo_id')
        file_name = body.get('file_name')

        download_id = llm_manager.start_download(repo_id, file_name)
        response_data = dict(download_id=download_id)

        self.send_json_response(status_code=200, response_data=response_data)

    def handle_download_status(self):
        data = self.parse_json_body()
        repo_id = data.get('repo_id')
        file_name = data.get('file_name')
        download_status = llm_manager.downloads.get((repo_id, file_name))

        status_code = 200 if download_status else 404
        response_data = download_status if download_status else { 'reason': 'Not found' }
        self.send_json_response(status_code, response_data)

    def handle_downloads_inprogress(self):
        in_progress = [info for info in llm_manager.downloads.values()
                       if not info['finished']]
        self.send_json_response(status_code=200, response_data=in_progress)

    def handle_list_models(self):
        models_root = "installed_models"
        models_registry = os.path.join(models_root, "models_registry.json")
        if os.path.exists(models_registry):
            with open(models_registry) as f:
                content = f.read()
            registry = json.loads(content)

            response_data = []
            for model in registry:
                fields = ['repo_id', 'file_name']
                item = {key: model[key] for key in fields}
                response_data.append(item)
        else:
            response_data = []

        self.send_json_response(status_code=200, response_data=response_data)

    def parse_json_body(self):
        content_len = int(self.headers.get('Content-Length'))
        json_data = self.rfile.read(content_len)
        json_data = json_data.decode("utf-8")
        return json.loads(json_data)

    def send_json_response(self, status_code, response_data, encoding='utf-8'):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        response_json = json.dumps(response_data)
        self.wfile.write(bytes(response_json, encoding=encoding))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("model", type=str)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--ngl", type=int, default=0)
    parser.add_argument("-c", type=int, default=1024, help="Context size of the model")
    args = parser.parse_args()

    llm_manager.setup(exec_path="./llama.cpp/server",
                      model_path=args.model,
                      host="localhost",
                      port=9500,
                      num_gpu_layers=args.ngl,
                      context_size=args.c)

    server = HTTPServer((args.host, args.port), HttpHandler)
    server.serve_forever()
