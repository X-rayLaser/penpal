# Introduction

The repository offers a user-friendly web interface for interacting with Large Language Models (LLMs). Users can install it by cloning the GitHub repository and running it locally. The app supports multiple LLMs such as Llama and Mistral, accessible through its chat interface.


Features include:
- Regenerating LLM responses
- Branching conversations
- Saving and loading chat sessions
- Customizable generation settings
- Customizable system messages
- Integration of user-defined APIs/tools
- Availability of various pre-installed tools for LLMs (coming later)


Users can customize the application's functionality according to their preferences. The integration of external tools and APIs enables enhanced capabilities for LLMs during conversations.

# Status: early development stage

This project is still under early development. It may have bugs and/or limitations. Use it at your own risk.
Web-based GUI is not yet complete, some important GUI elements are missing and certain features are experimental and may be removed later.

# Installation

To get started with our application, follow these steps to install it on your local environment:

## Prerequisites

1. Install Node.js: Follow the official instructions for your operating system.

2. Install Python: If you haven't already, follow the official instructions to download and install Python 3.x.

3. Install pipenv if you don't have it yet:
```
pip install --user pipenv 
```

## Actual installation


To get started, clone the repository:

```
git clone https://github.com/X-rayLaser/penpal.git
cd penpal
```

Create a new virtual environment using the command:
```
python -m venv myvenv
```

Activate it with (on linux):
```
source myvenv/bin/activate
```

On Windows, use:
```
myvenv\Scripts\activate
```

Install Python dependencies using pip:
```
pip install -r requirements.txt
```

Install javascript dependencies:
```
npm install
```

Create a secrets.py file in the mysite directory and add your secret key:

```
SECRET_KEY = 'your-secret-key'
```

You can generate the key with a command:
```
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Build frontend code
```
npx webpack --config webpack.config.js
```

Apply django migrations
```
python manage.py migrate
```

# Getting Started

To get started with using the web app to interact with Large Language Models (LLMs), follow the steps below.

## Prerequisites

- Clone and build the llama.cpp project, which includes an LLM server.
- Obtain a Large Language Model in GGUF format. You may download models from sources like Hugging Face or convert existing models to this format using utilities provided in the llama.cpp project.

## Setting Up Your Local LLM Server

Clone the llama.cpp project:
```
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
```

Build it by running make:
```
make
```

Run the server and test it. On unix-based systems (Linux, macOS, etc.):
```
./server -m models/7B/ggml-model.gguf -c 2048 --port 9000
```

On Windows:
```
server.exe -m models\7B\ggml-model.gguf -c 2048 --port 9000
```

Try generating a few tokens for a prompt:
```
curl --request POST \
    --url http://localhost:9000/completion \
    --header "Content-Type: application/json" \
    --data '{"prompt": "Building a website can be done in 10 simple steps:","n_predict": 128}'
```

Refer to [LLama.cpp repository](https://github.com/ggerganov/llama.cpp) for more information on building options (including on how to build it with support for CUDA) as well as information about a server app.

After you make sure that it works, you can stop it and change the working directory back:
```
cd ..
```

Finally, run llm_services/llamacpp.py:
```
python llm_services/llamacpp.py <model> --port 9000 -c 512 -ngl 0
```

Replace model with a path to your model file in GGUF format. Use --port option to specify a port number for the LLM server. Use -c option to specify context size. Use -ngl option to specify a number of layers to offload to GPU.

## Configuring Your Web App

1. Create a new file named local_settings.py in the project directory of your web app (mysite).

2. Add the following configuration to the file:
```
LLM_SETTINGS = {
    "generator": {
        "class": "llm_utils.generators.RemoteLLM",
        "kwargs": {
            "host": "localhost",
            "port": 9000
        }
    }
}
```

Now your web app is configured to communicate with your local LLM server and use it for token generation.

## Running the app
```
python manage.py runserver 8000
```

If you are running the code in Vagrant or inside virtual machine, 
make sure to forward 8000 port and run server this way:
```
python manage.py runserver 0.0.0.0:8000
```

Open a browser and navigate to http://localhost:8000. You should see a web app.
