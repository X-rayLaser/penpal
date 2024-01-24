import time
import random
from .base import TokenGenerator


class DummyGenerator(TokenGenerator):
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        words = ["likes", "words", "and", "everyone", "playing", "with"]

        for i in range(10):
            time.sleep(0.125)
            word = random.choice(words)
            yield word + " "

        yield random.choice(words)


class DummyMarkdownGenerator(TokenGenerator):
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        tokens = ["Of", " ", "course", ".", " ", "Here" " ", "is", " ", "the", " ", "code", ":", "\n", 
                  "``", "`", "python", "\n", "for", " ", "i", " in", " ", "range", "(", "5", ")", 
                  ":", "\n", "    ", "print", "(", "'", "hello", " ", "world", "'", ")", "\n", "```"]
        for token in tokens:
            time.sleep(0.125)
            yield token


class DummyToolUseGenerator(TokenGenerator):
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        tokens1 = ["one ", "two ", "three ", "<", "api>", "calculator", 
                  "(+,", "2,3)", "</api>", " rest", " to be ", "discarded "]
        tokens2 = ["four", "five", "six"]
        
        seq = tokens1 if random.random() > 0.5 else tokens2
        for token in seq:
            time.sleep(0.5)
            yield token


class DummyExceptionRaisingGenerator(TokenGenerator):
    def stream_tokens(self, prompt, clear_context=False, llm_settings=None):
        yield 5 / 0
        yield "hey"