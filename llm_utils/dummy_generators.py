import time
import json
import random
from .base import TokenGenerator
from pygentify.llm_backends import BaseLLM


class DummyGenerator(TokenGenerator):
    def stream_tokens(self, generation_spec):
        words = ["likes", "words", "and", "everyone", "playing", "with"]

        for i in range(10):
            time.sleep(0.125)
            word = random.choice(words)
            yield word + " "

        yield random.choice(words)


class DummyPhraseGenerator(TokenGenerator):
    def stream_tokens(self, generation_spec):
        words = ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog", "."]

        for word in words:
            sleep_secs = random.random()
            time.sleep(sleep_secs)
            yield word + " "

        for word in words:
            sleep_secs = random.random()
            time.sleep(sleep_secs)
            yield word + " "


class DummyMarkdownGenerator(TokenGenerator):
    def stream_tokens(self, generation_spec):
        tokens = ["Of", " ", "course", ".", " ", "Here" " ", "is", " ", "the", " ", "code", ":", "\n", 
                  "``", "`", "python", "\n", "for", " ", "i", " in", " ", "range", "(", "5", ")", 
                  ":", "\n", "    ", "print", "(", "'", "hello", " ", "world", "'", ")", "\n", "```"]
        for token in tokens:
            time.sleep(0.125)
            yield token


class DummyToolUseGenerator(TokenGenerator):
    def stream_tokens(self, generation_spec):
        data = {'tool_name': 'add', 'args': dict(num1=2, num2=3)}
        tokens1 = ["one ", "two ", "three ", "<", "|tool_use_start|>", json.dumps(data),
                   "<|tool_use_end|>", " rest", " to be ", "discarded "]
        tokens2 = ["four", "five", "six"]
        
        seq = tokens1 if random.random() > 0.5 else tokens2
        for token in seq:
            time.sleep(0.5)
            yield token


response_with_code = """
Hello, world. Here is some code
```javascript

function MainComponent(props) {
    return <div className="red-div">Hello, world</div>
}

css

.red-div {
    background-color: red;
}
```
"""


class DummyCodeGenerator(TokenGenerator):
    def stream_tokens(self, generation_spec):
        for ch in response_with_code:
            time.sleep(0.1)
            yield ch


class DummyExceptionRaisingGenerator(TokenGenerator):
    def stream_tokens(self, generation_spec):
        yield 5 / 0
        yield "hey"


class DummyAdapter(BaseLLM):
    def __init__(self, dummy_generator):
        self.generator = dummy_generator

    def __call__(self, text):
        yield from self.generator.stream_tokens(None)
