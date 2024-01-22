import React from 'react';

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


export function generateResponse(prompt, llmSettings, onChunk, onPaused, onDone) {
    let generatedText = "";
    let lastChunk = "";

    let body = {
        prompt,
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

        let apiCallObject = findPendingApiCall(generatedText);


        console.log('handleDone in GENERATERESPONSE: apiCallObject', apiCallObject);
        console.log(generatedText);

        if (apiCallObject) {
            let textSlice = generatedText.substring(0, apiCallObject.offset);

            let url = apiCallObject.toUrlPath();
            fetch(url, {
                headers: {
                    'Accept': 'application/json'
                }
            }).then(response => response.json()).then(data => {
                let apiCallString = apiCallObject.renderWithResult(data.result);
                let finalizedSegment = textSlice + apiCallString;

                onPaused(finalizedSegment);
                let newPrompt = prompt + finalizedSegment;
                generateResponse(newPrompt, llmSettings, onChunk, onPaused, onDone);
            });
            
        } else {
            onDone(generatedText);
        }
    }

    streamJsonResponse('/chats/generate_reply/', 'POST', body, handleChunk, handleDone);
}

class ApiCall {
    constructor(name, argString, offset) {
        this.name = name;
        this.argString = argString;
        this.offset = offset;
    }

    renderWithResult(result) {
        return `<api>${this.name}(${this.argString})=${result}</api>`;
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
    let results = generatedText.match(/<api>[a-z_]+\(.*<\/api>/);
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
    str = str.replace(/=.*/, "");

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
    fetch(url, {
        method: method,
        body: JSON.stringify(data),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        let reader = response.body.getReader();

        // handle server error
        reader.read().then(function pump({ done, value }) {
            if (done) {
                handleDone();
                return;
            }

            let chunk = new TextDecoder().decode(value);

            handleChunk(chunk);
            
            return reader.read().then(pump);
        });
    });
}
