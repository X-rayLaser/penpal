import React from 'react';

import { getConversationText, includeSystemMessage } from './tree';
import { GenericFetchJson } from './generic_components';
import {
    useLocation,
    useNavigate,
    useParams
} from "react-router-dom";


export const withRouter = WrappedComponent => props => {
    let location = useLocation();
    let navigate = useNavigate();
    let params = useParams();
    return (
        <WrappedComponent
            {...props}
            router={{ location, navigate, params }}
        />
    );
};


export class SimpleTextCompletionGenerator {
    constructor(inferenceConfig, llmSettings, leafId, tokenStreamer, socketSessionId) {
        this.inferenceConfig = inferenceConfig;
        this.llmSettings = llmSettings;
        this.leafId = leafId;
        this.onChunk = chunk => {};
        this.onPaused = textSegment => {};
        this.streamer = tokenStreamer;
        this.socketSessionId = socketSessionId;

        if (!this.streamer) {
            this.streamer = new JsonResponseStreamer('/chats/generate_reply/', 'POST');
        }
    }

    generate(messages) {
        return new Promise((resolve, reject) => {
            let generatedText = "";
            let body = this.prepareBody(messages);

            this.streamer.onChunk = chunk => {
                generatedText += chunk;
                this.onChunk(chunk);
            };

            this.streamer.stream(body).then(() => {
                resolve(generatedText);
            }).catch(reason => {
                console.error(reason);
                reject(reason.error);
            });
        });
    }

    prepareBody(prompt) {
        return {
            prompt,
            inference_config: this.inferenceConfig,
            clear_context: true,
            llm_settings: this.llmSettings,
            parent: this.leafId,
            socketSessionId: this.socketSessionId
        };
    }
}

export class ToolAugmentedCompletionGenerator extends SimpleTextCompletionGenerator {
    constructor(inferenceConfig, llmSettings, leafId, tokenStreamer, socketSessionId, chatTemplate) {
        super(inferenceConfig, llmSettings, leafId, tokenStreamer, socketSessionId);
        this.chatTemplate = chatTemplate;
    }

    generate(prompt) {
        let body = this.prepareBody(prompt);

        this.streamer.onChunk = chunk => {
            this.onChunk(chunk);
        };
        this.streamer.onPaused = (segment) => {
            this.onPaused(segment);
        };

        return new Promise((resolve, reject) => {
            this.streamer.stream(body).then(() => {
                resolve();
            }).catch(reason => {
                console.error(reason);
                reject(reason.error);
            });
        });
    }
}


//deprecated
export function streamJsonResponse(url, method, data, handleChunk, handleDone) {
    return new Promise((resolve, reject) => {
        fetch(url, {
            method: method,
            body: JSON.stringify(data),
            headers: {
                "Content-Type": "application/json"
            }
        }).then(response => {
            let reader = response.body.getReader();

            if (!response.ok) {
                throw {
                    error: response.statusText
                };
            }

            // handle server error
            reader.read().then(function pump({ done, value }) {
                console.log('ok?', response.ok)
                if (done) {
                    handleDone();
                    resolve();
                    return;
                }

                let chunk = new TextDecoder().decode(value);

                handleChunk(chunk);
                
                return reader.read().then(pump).catch(reason => {
                    console.error(reason);
                    reject(reason);
                });
            }).catch(reason => {
                console.error(reason);
                reject(reason);
            });
        });
    });
}


class BaseResponseStreamer {
    constructor(url, method) {
        this.url = url;
        this.method = method || 'POST';

        this.onChunk = function(chunk) {}
        this.onDone = function() {};
        this.onPaused = function(segment) {}
    }

    stream(data) {
        data = data || {};
        return this.getStreamPromise(data);
    }

    getStreamPromise(data) {
        return undefined;
    }
}


export class JsonResponseStreamer extends BaseResponseStreamer {
    getStreamPromise(data) {
        return streamJsonResponse(this.url, this.method, data, this.onChunk, this.onDone);
    }
}

export class WebsocketResponseStreamer extends BaseResponseStreamer {
    constructor(url, method, websocket) {
        super(url, method);
        this.websocket = websocket;
    }

    getStreamPromise(data) {
        return new Promise((resolve, reject) => {
            let tokenString = "";
            const alistener = msgEvent => {
                let payload = JSON.parse(msgEvent.data);
                if (payload.event === "end_of_stream") {
                    this.websocket.removeEventListener("message", alistener);
                    this.onDone();
                    resolve(tokenString);
                } else if (payload.event === "tokens_arrived") {
                    tokenString += payload.data;
                    this.onChunk(payload.data);
                } else if (payload.event === "generation_paused") {
                    tokenString = payload.data;
                    this.onPaused(tokenString);
                }
            };

            this.websocket.addEventListener("message", alistener);
            let fetcher = new GenericFetchJson();
            fetcher.method = this.method;

            fetcher.body = data;
            fetcher.performFetch(this.url).catch(error => {
                reject(error);
                console.error('Failed to generate response', error);
            });
        });
    }
}


export class BufferringAudioAutoPlayer {
    constructor() {
        this.pieces = [];
        this.playing = false;
        this.bufferSize = null;
        this.player = new AudioPlaylistPlayer();
    }

    put(audioPiece) {
        this.pieces.push(audioPiece);

        if (!this.playing) {
            this.player.putNoPlay(audioPiece);
        } else {
            this.player.put(audioPiece);
        }

        if (this.bufferSize && this.getTotalChars() > this.bufferSize && !this.playing) {
            this.playback();
        }
    }

    playback() {
        this.playing = true;
        this.player.play();
    }

    calculateBufferSize(audioText) {
        let totalChars = 0;
        let totalGenerationTimeSecs = 0;
        this.pieces.forEach(piece => {
            totalChars += piece.text.length;
            totalGenerationTimeSecs += piece.gen_time_seconds;
        });

        let generationTimePerChar = totalGenerationTimeSecs / totalChars;
        let N = audioText.length;
        let t = generationTimePerChar;
        this.bufferSize = N * t / (t + 1);
    }

    getTotalChars() {
        let totalChars = 0;
        this.pieces.forEach(piece => {
            totalChars += piece.text.length;
        });
        return totalChars;
    }
}


class AudioPlaylistPlayer {
    constructor() {
        this.items = [];
        this.playInProgress = false;
    }

    play() {
        this.playInProgress = false;

        if (this.items.length === 0) {
            return;
        }

        let nextPiece = this.items.shift();

        if (!nextPiece.url) {
            //discarding items without url
            this.play();
            return;
        }

        this.playInProgress = true;
        let audio = new Audio(nextPiece.url);
        audio.addEventListener("ended", event => {
            this.play();
        });

        if (audio.readyState === HTMLMediaElement.HAVE_FUTURE_DATA) {
            audio.play();
        } else {
            audio.addEventListener("canplaythrough", event => {
                audio.play();
            });
        }
    }

    put(item) {
        this.items.push(item);

        if (!this.playInProgress) {
            this.play();
        }
    }

    putNoPlay(item) {
        this.items.push(item);
    }
}


export function captureAndPlaySpeech(websocket, bufferingPlayer) {
    return new Promise((resolve, reject) => {
        const alistener = msgEvent => {
            let payload = JSON.parse(msgEvent.data);

            if (payload.event === 'end_of_speech') {
                websocket.removeEventListener("message", alistener);
                if (!bufferingPlayer.playing) {
                    bufferingPlayer.playback();
                }

                resolve(bufferingPlayer);
            } else if (payload.event === 'speech_sample_arrived') {
                bufferingPlayer.put(payload.data);
            }
        };

        websocket.addEventListener('message', alistener);
    });
}


export function renderSize(size) {
    const KB = 1000
    const MB = KB * 1000;
    const GB = MB * 1000;

    let newSize;
    let units;
    if (size > GB) {
        newSize = size / GB;
        units = 'GB';
    } else if (size > MB) {
        newSize = size / MB;
        units = 'MB';
    } else if (size > KB) {
        newSize = size / KB;
        units = 'KB';
        
    } else {
        newSize = size;
        units = 'B';
    }

    return `${Math.round(newSize * 10) / 10} ${units}`;
}


export class TextTemplate {
    constructor(template) {
        this.template = template;
    }

    render(text) {
        return this.template.replace("%message", text);
    }
};


const LLAMA3_START_HEADER_ID = "<|start_header_id|>";
const LLAMA3_END_HEADER_ID = "<|end_header_id|>";
const LLAMA3_EOT_ID = "<|eot_id|>";


function llamaRoleTemplate(role) {
    return `${LLAMA3_START_HEADER_ID}${role}${LLAMA3_END_HEADER_ID}\n\n%message${LLAMA3_EOT_ID}`;
}


let chatTemplates = {
    llama3: {
        question: llamaRoleTemplate("user"),
        answer: llamaRoleTemplate("assistant"),
        systemMessage: llamaRoleTemplate("system"),
        startOfText: "<|begin_of_text|>",
        promptSuffix: `${LLAMA3_START_HEADER_ID}assistant${LLAMA3_END_HEADER_ID}\n\n`,
        continuationPrefix: `${LLAMA3_EOT_ID}${LLAMA3_START_HEADER_ID}assistant${LLAMA3_END_HEADER_ID}\n\n`
    },
    mistral_8b: {
        question: "[INST]%message[/INST]",
        answer: "%message",
        systemMessage: null,
        startOfText: "<s>",
        promptSuffix: "",
        continuationPrefix: ""
    },
    openLlama_3b: {
        question: "<human>%message</human>",
        answer: "<bot>%message</bot>",
        systemMessage: null,
        startOfText: "",
        promptSuffix: "<bot>",
        continuationPrefix: "</bot><bot>"
    }
};

let rawTemplateSpec = {
    question: "%message\n",
    answer: "%message\n",
    systemMessage: null,
    startOfText: "",
    promptSuffix: "",
    continuationPrefix: ""
};


export class ChatEncoder {
    constructor(templateSpec, useBos) {
        this.spec = templateSpec;
        this.useBos = useBos;
    }

    encode(systemMessage, messages) {
        let questionTemplate = new TextTemplate(this.spec.question);
        let answerTemplate = new TextTemplate(this.spec.answer);

        let conversation;
        if (this.spec.systemMessage) {
            let systemTemplate = new TextTemplate(this.spec.systemMessage);
            conversation = getConversationText(messages, questionTemplate, answerTemplate, systemMessage, systemTemplate);
        } else {
            messages = includeSystemMessage(messages, systemMessage);
            conversation = getConversationText(messages, questionTemplate, answerTemplate);
        }

        conversation = conversation + this.spec.promptSuffix;
        if (this.useBos) {
            conversation = this.spec.startOfText + conversation;
        }
        return conversation;
    }
}


export function guessChatEncoder(configuration, instructMode) {
    let fileName = null;
    if (configuration && configuration.file_name) {
        fileName = configuration.file_name.toLowerCase();
    }

    let templateSpec = rawTemplateSpec;

    if (fileName && instructMode) {
        if (fileName.toLowerCase().match(/llama-?_?3/)) {
            templateSpec = chatTemplates.llama3;
        } else if (fileName.toLowerCase().match(/mistral/)) {
            templateSpec = chatTemplates.mistral_8b;
        } else if (fileName.toLowerCase().match(/open-?_?llama/)) {
            templateSpec = chatTemplates.openLlama_3b;
        }
    }

    console.log("using spec:", templateSpec);
    let useBos = false;
    return new ChatEncoder(templateSpec, useBos);
}
