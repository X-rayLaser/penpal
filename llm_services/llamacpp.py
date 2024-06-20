import subprocess
import base64
import threading
import requests
import time
import json
import os
import shutil
import sys
from llama_cpp import Llama, LlamaCache
from llama_cpp.llama_chat_format import Llava15ChatHandler

sys.path.insert(0, ".")
from http.server import HTTPServer, BaseHTTPRequestHandler
from huggingface_hub import hf_hub_download
from llm_services.common import models_root, models_registry


def uri_from_image(image_b64_string):
    return f"data:image/png;base64,{image_b64_string}"


class LLaVaGenerator:
    def __init__(self, model_path, launch_config):
        mmprojector_file = launch_config['mmprojector']
        mmprojector_path = os.path.join(models_root, mmprojector_file)
        chat_handler = Llava15ChatHandler(clip_model_path=mmprojector_path)

        self.launch_config = launch_config
        context_size = self.launch_config.get('contextSize', 4096)
        num_gpu_layers = self.launch_config.get('ngl', 0)
        num_threads = self.launch_config.get('numThreads', 2)
        num_batch_threads = self.launch_config.get('numBatchThreads', num_threads)
        batch_size = self.launch_config.get('batchSize', 512)

        image_b64_string = launch_config.get('image_b64')

        self.n_predict = self.launch_config.get('nPredict', -1)
        self.image_b64_string = image_b64_string and image_b64_string.decode('utf-8')

        self.llm = Llama(
            model_path=model_path,
            chat_handler=chat_handler,
            n_ctx=context_size,
            n_gpu_layers=num_gpu_layers,
            n_threads=num_threads,
            n_threads_batch=num_batch_threads,
            n_batch=batch_size
        )

        self.cache = None

    def enable_caching(self, params):
        if 'cache_prompt' in params and self.cache is None:
            self.cache = LlamaCache
            self.llm.set_cache(self.cache)

    def __call__(self, messages, params):
        self.enable_caching(params)

        if len(messages) < 2:
            yield ""

        relevant_params = ['temperature', 'top_p', 'top_k', 'min_p', 'repeat_penalty', 'stop']
        sampling_params = {name: params[name] for name in relevant_params if name in params}
        sampling_params['max_tokens'] = params.get('n_predict', self.n_predict)

        it = self.llm.create_chat_completion(messages, stream=True, **sampling_params)

        def prepare_json_line(text, stop=False):
            padding = "_" * 6 # because client strips 6 first characters
            res = padding + json.dumps({"content": text, "stop": stop, "stopping_word": ""}) + '\n'
            return res

        for chunk in it:
            print(chunk)
            choices = chunk.get("choices")
            if not (choices and choices[0]):
                continue

            delta = choices[0].get("delta")
            if not delta:
                continue

            s = delta.get('content')
            if s:
                yield prepare_json_line(s)
        yield prepare_json_line("", stop=True)


class LLMManager:
    def __init__(self):
        self.executable_path = ""
        self.host = ""
        self.port = ""
        self.context_size = ""

        self.model_path = ""
        self.launch_config = {}
        self.llava = False

        self.process = None
        self.printing_thread = None

        self.download_threads = []
        self.downloads = {}

        self.llava_generator = None

    def setup(self, exec_path, host, port):
        self.executable_path = exec_path
        self.host = host
        self.port = str(port)

    def configure_launch(self, model_path, launch_config):
        self.model_path = model_path
        self.launch_config = launch_config
        self.llava = 'mmprojector' in self.launch_config

        if self.llava:
            self.llava_generator = LLaVaGenerator(model_path, launch_config)

    def generate(self, data, content_type):
        if self.llava:
            params = json.loads(data)
            messages = params.get('prompt', [])
            yield from self.llava_generator(messages, params)
            return
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
        if not self.model_path:
            raise Exception('Improperfly configured: no model path set')

        if self.llava:
            return

        context_size = self.launch_config.get('contextSize', 512)
        num_gpu_layers = self.launch_config.get('ngl', 0)
        num_threads = self.launch_config.get('numThreads', 2)
        num_batch_threads = self.launch_config.get('numBatchThreads', num_threads)
        batch_size = self.launch_config.get('batchSize', 512)
        n_predict = self.launch_config.get('nPredict', -1)

        popen_args = [
            self.executable_path,
            "--model", self.model_path,
            "--threads", str(num_threads),
            #"--threads-batch", str(num_batch_threads),
            "--ctx-size", str(context_size),
            "--n-gpu-layers", str(num_gpu_layers),
            "--batch-size", str(batch_size),
            #"--n-predict", str(n_predict),
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

    def start_download(self, repo, file_name, size):
        repo_id = repo['id']
        download_id = (repo_id, file_name)
        download_info = {
            'repo_id': repo_id,
            'repo': repo,
            'file_name': file_name,
            'size': size,
            'finished': False,
            'errors': [],
            'started_at': time.time()
        }
        self.downloads[download_id] = download_info

        download = DownloadThread(download_info, repo, file_name, size)
        self.download_threads.append(download)
        download.start()
        return download_id


class DownloadThread(threading.Thread):
    def __init__(self, download_info, repo, file_name, size):
        super().__init__()
        self.download_info = download_info
        self.repo_id = repo['id']
        self.repo = repo
        self.file_name = file_name
        self.size = size

        self.download_path = ''

    def run(self) -> None:
        # todo: save model under corresponding repo_id folder
        try:
            self.download_path = hf_hub_download(self.repo_id, self.file_name, local_dir=models_root)
        except Exception as e:
            self.download_info['finished'] = True
            self.download_info['errors'] = [str(e)]
            return

        with threading.Lock():
            self.download_info['finished'] = True

            os.makedirs(models_root, exist_ok=True)

            if not os.path.exists(models_registry):
                with open(models_registry, "w") as f:
                    f.write(json.dumps([]))

            with open(models_registry) as f:
                content = f.read()
                entries = json.loads(content)

            metadata = dict(repo_id=self.repo_id, repo=self.repo, 
                            file_name=self.file_name, size=self.size)
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
        elif self.path == '/start-llm':
            self.handle_start_llm()
        else:
            print("Unsupprted path", self.path)
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        self.protocol_version = 'HTTP/1.0'

        if self.path == '/downloads-in-progress':
            self.handle_downloads_inprogress()
        elif self.path == '/failed-downloads':
            self.handle_failed_downloads()
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
        print("Got data", json_data[:100])

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        for line in llm_manager.generate(json_data, content_type):
            print("Got line:", line)
            self.wfile.write(bytes(line, encoding='utf-8'))

    def handle_download(self):
        body = self.parse_json_body()
        repo = body.get('repo')
        repo_id = repo['id']
        file_name = body.get('file_name')
        size = body.get('size')


        registry = self.get_models_registry()
        installed_matches = [info for info in registry 
                             if info['repo_id'] == repo_id and info['file_name'] == file_name]
        
        if installed_matches:
            response_data = dict(reason="Model already downloaded")
            self.send_json_response(status_code=400, response_data=response_data)
            return
        
        download = llm_manager.downloads.get((repo_id, file_name))
        if download:
            if not download['finished']:
                response_data = dict(reason="Model download is already in progress")
                self.send_json_response(status_code=400, response_data=response_data)
                return
            
            if download['finished'] and not download['errors']:
                response_data = dict(reason="Model was just installed")
                self.send_json_response(status_code=400, response_data=response_data)
                return

        download_id = llm_manager.start_download(repo, file_name, size)
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

    def handle_failed_downloads(self):
        failed = [info for info in llm_manager.downloads.values()
                  if info['finished'] and info['errors']]

        self.send_json_response(status_code=200, response_data=failed)

    def handle_list_models(self):
        registry = self.get_models_registry()
        
        response_data = []
        for model in registry:
            fields = ['repo_id', 'repo', 'file_name', 'size']
            item = {key: model.get(key, '') for key in fields}
            response_data.append(item)

        self.send_json_response(status_code=200, response_data=response_data)

    def handle_start_llm(self):
        data = self.parse_json_body()
        repo_id = data.get('repo_id')
        model_file = data.get('file_name')
        launch_config = data.get('launch_params')

        model_path = os.path.join(models_root, model_file)

        print("repo_id", repo_id, "model_file", model_file)
        print("launch config", launch_config)

        if os.path.exists(model_path):
            if llm_manager.model_path != model_path or llm_manager.launch_config != launch_config:
                llm_manager.configure_launch(model_path, launch_config)
                llm_manager.restart_llm()
            self.send_json_response(status_code=200, response_data={'ok': 'ok'})
        else:
            self.send_json_response(status_code=404, response_data={'reason': 'Not found'})

    def get_models_registry(self):
        if os.path.exists(models_registry):
            with open(models_registry) as f:
                content = f.read()
            registry = json.loads(content)
        else:
            registry = []
        return registry

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
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    llm_manager.setup(exec_path="./llama.cpp/server",
                      host="localhost",
                      port=9500)

    server = HTTPServer((args.host, args.port), HttpHandler)
    server.serve_forever()
