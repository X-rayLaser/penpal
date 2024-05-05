import React from 'react';

import { getConversationText, includeSystemMessage } from './tree';

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


export function generateResponse(prompt, inferenceConfig, llmSettings, onChunk, onPaused, onDone, onError) {
    let generatedText = "";
    let lastChunk = "";

    let body = {
        prompt,
        inference_config: inferenceConfig,
        clear_context: true,
        llm_settings: llmSettings
    };

    const handleChunk = chunk => {
        console.log('chunk:', chunk);
        generatedText += chunk;
        lastChunk = chunk;
        onChunk(generatedText, chunk);
    };

    
    const handleDone = () => {

        console.log('handleDone in GENERATERESPONSE');
        console.log(generatedText);

        let encodedText = encodeURIComponent(generatedText);
        let findApiUrl = `/chats/find_api_call/?text=${encodedText}`;
        fetch(findApiUrl).then(response => response.json()).then(data => {
            console.log("CALLED FIND API CALL", data)
            if (data.hasOwnProperty('offset')) {
                let offset = data.offset;
                let api_call = data.api_call;

                let textSlice = generatedText.substring(0, offset);
                console.log("APICALL URL", api_call.url);
                fetch(api_call.url, {
                    headers: {
                        'Accept': 'application/json'
                    }
                }).then(response => response.json()).then(data => {
                    let finalizedSegment = textSlice + data.api_call_string;
    
                    onPaused(finalizedSegment);
                    let newPrompt = prompt + finalizedSegment;
                    generateResponse(newPrompt, inferenceConfig, llmSettings, onChunk, onPaused, onDone, onError);
                });
            } else {
                console.log("API call not found");
                onDone(generatedText);
            }
        });
    }

    streamJsonResponse(
        '/chats/generate_reply/', 'POST', body, handleChunk, handleDone
    ).catch(reason => {
        onError(reason.error);
    });
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
    return fetch(url, {
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
                return;
            }

            let chunk = new TextDecoder().decode(value);

            handleChunk(chunk);
            
            return reader.read().then(pump).catch(reason => {
                console.error(reason);
            });
        }).catch(reason => {
            console.error(reason);
        });
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
