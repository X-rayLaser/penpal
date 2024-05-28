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

export class TextCompletionGenerator {
    constructor(inferenceConfig, llmSettings, tokenStreamer, socketSessionId) {
        this.inferenceConfig = inferenceConfig;
        this.llmSettings = llmSettings;
        this.onChunk = chunk => {};
        this.onPaused = textSegment => {};
        this.streamer = tokenStreamer;
        this.socketSessionId = socketSessionId;

        if (!this.streamer) {
            this.streamer = new JsonResponseStreamer('/chats/generate_reply/', 'POST');
        }
    }

    generate(prompt) {
        return new Promise((resolve, reject) => {
            const generateWithResolvedAPICalls = (currentPrompt) => {
                let generatedText = "";
                let body = this.prepareBody(currentPrompt);

                this.streamer.onChunk = chunk => {
                    generatedText += chunk;
                    this.onChunk(generatedText, chunk);
                };

                this.streamer.stream(body).then(() => {
                    let encodedText = encodeURIComponent(generatedText);
                    let findApiUrl = `/chats/find_api_call/?text=${encodedText}`;

                    fetch(findApiUrl).then(response => response.json()).then(data => {

                        if (data.hasOwnProperty('offset')) {
                            this.makeApiCall(data, generatedText).then(finalizedSegment => {
                                this.onPaused(finalizedSegment);
                                let newPrompt = currentPrompt + finalizedSegment;
                                generateWithResolvedAPICalls(newPrompt);
                            });
                        } else {
                            resolve(generatedText);
                        }
                    });
                }).catch(reason => {
                    console.error(reason);
                    reject(reason.error);
                });
            }

            generateWithResolvedAPICalls(prompt);
        });
    }

    prepareBody(prompt) {
        return {
            prompt,
            inference_config: this.inferenceConfig,
            clear_context: true,
            llm_settings: this.llmSettings,
            socketSessionId: this.socketSessionId
        };
    }

    makeApiCall(callInfo, generatedText) {
        let offset = callInfo.offset;
        let api_call = callInfo.api_call;

        let textSlice = generatedText.substring(0, offset);
        return fetch(api_call.url, {
            headers: {
                'Accept': 'application/json'
            }
        }).then(response => response.json()).then(data => {
            let finalizedSegment = textSlice + data.api_call_string;
            return finalizedSegment;
        });
    }
}


class ApiCall {
    constructor(name, argString, offset) {
        this.name = name;
        this.argString = argString;
        this.offset = offset;
    }

    renderWithResult(result) {
        return `<api>${this.name}(${this.argString})</api><result>${result}</result>`;
    }

    toUrlPath() {
        // todo: urlencode this
        let tool = this.name;
        let argString = encodeURIComponent(this.argString);

        return `/chats/call_api?tool=${tool}&arg_string=${argString}`;
    }
}

function findPendingApiCall(generatedText) {
    //returns first pending API call and its index, otherwise return null
    generatedText = generatedText.toLowerCase();
    let results = generatedText.match(/<api>[\s]*[a-z_]+\(.*<\/api>/);
    if (!results || results.length === 0) {
        return null;
    }

    let str = results[0];

    let offset = generatedText.indexOf(str);

    if (offset === -1) {
        const msg = "Found api call markup, but for some reason failed to pinpoint its position"
        console.error(msg);
        throw new Error(msg);
    }
    str = str.replace("<api>", "").replace("</api>", "");
    str = str.replace(/=.*/, "").trim();

    let name = str.match(/^[a-z_]+/)[0];
    let argString;
    if (!str.endsWith(")")) {
        str += ")";
    }
    argString = str.match(/\((.*)\)/)[1];

    console.log("argString: ", argString)
    return new ApiCall(name, argString, offset);
}

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


let chatTemplates = {
    llama3: {
        question: "<|start_header_id|>user<|end_header_id|>\n\n%message<|eot_id|>",
        answer: "<|start_header_id|>assistant<|end_header_id|>\n\n%message<|eot_id|>",
        systemMessage: "<|start_header_id|>system<|end_header_id|>\n\n%message<|eot_id|>",
        startOfText: "<|begin_of_text|>"
    },
    mistral_8b: {
        question: "[INST]%message[/INST]",
        answer: "%message",
        systemMessage: null,
        startOfText: "<s>"
    },
    openLlama_3b: {
        question: "<human>%message</human>",
        answer: "<bot>%message</bot>",
        systemMessage: null,
        startOfText: ""
    }
};

let rawTemplateSpec = {
    question: "%message\n",
    answer: "%message\n",
    systemMessage: null,
    startOfText: ""
};


export class ChatEncoder {
    constructor(templateSpec) {
        this.spec = templateSpec;
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

        conversation = this.spec.startOfText + conversation;
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
    return new ChatEncoder(templateSpec);
}
