import React from 'react';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Pagination from 'react-bootstrap/Pagination';
import Alert from 'react-bootstrap/Alert';
import ButtonGroup from 'react-bootstrap/ButtonGroup';
import Badge from 'react-bootstrap/Badge';
import Accordion from 'react-bootstrap/Accordion';
import ListGroup from 'react-bootstrap/ListGroup';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';

import { withRouter, guessChatEncoder, ChatEncoder, 
    WebsocketResponseStreamer, SimpleTextCompletionGenerator, ToolAugmentedCompletionGenerator,
    BufferringAudioAutoPlayer, captureAndPlaySpeech
} from "./utils";
import { 
    fetchTree, addNode, addMessage, selectThread, appendThread, collapseThread,
    getNodeById, getThreadMessages, getConversationText, isHumanText, includeSystemMessage
} from './tree';
import { CollapsibleLLMSettings } from './presets';
import { CollapsibleEditableSystemMessage } from './components';
import { GenericFetchJson, csrftoken } from './generic_components';


const LLAMA3_MODEL = "llama_3";
const MISTRAL_8B_MODEL = "mistral_8b";


function ConversationTree(props) {
    let messages = getThreadMessages(props.tree, props.treePath);

    const items = messages.map(msg => {
        if (isHumanText(msg.key)) {
            return <HumanMessage key={msg.key} text={msg.text} pathItem={msg.pathItem} 
                    message={msg} onBranchSwitch={props.onBranchSwitch} />
        } else {
            return <AIMessage key={msg.key} text={msg.text} pathItem={msg.pathItem} message={msg}
                    onBranchSwitch={props.onBranchSwitch}
                    onRegenerate={props.onRegenerate} />
        }
    });

    return (
        <div className="mt-3">{items}</div>
    )
}


function traverseTree(tree, path) {
    //check if path is empty, then return tree root
    if (path.length === 0) {
        return tree;
    }

    let item = path[path.length - 1];

    return getNodeById(tree, item.nodeId);
}


class Message extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            medium: 'html_view'
        };

        this.handleDebugView = this.handleDebugView.bind(this);
        this.handleTextView = this.handleTextView.bind(this);
        this.handleHtmlView = this.handleHtmlView.bind(this);
    }

    handleDebugView() {
        this.setState({
            medium: 'tokens_view'
        });
    }

    handleTextView() {
        this.setState({
            medium: 'text_view'
        });
    }

    handleHtmlView() {
        this.setState({
            medium: 'html_view'
        });
    }

    render() {
        let props = this.props;
        let pathItem = props.pathItem;
        let message = props.message;
        let numSiblings = message.numSiblings;
        let active = pathItem.branchIndex + 1;
        let items = [];
        
        let onRegenerate = props.onRegenerate;

        function getHandler(key) {
            return e => {
                if (key !== active) {
                    let newBranchId = key - 1;
                    props.onBranchSwitch(message, newBranchId);
                }
            }
        }
        
        for (let i = 1; i <= numSiblings; i++) {
            const handler = getHandler(i);
            items.push(
                <Pagination.Item key={i} active={i === active} onClick={handler}>
                {i}
                </Pagination.Item>
            );
        }

        let innerHtml = {
            __html: message.data.html || message.data.text
        };

        let attachmentsHtml = {
            __html: message.data.attachments_text
        };

        let cleanText = message.data.clean_text || message.data.text;

        let prerenderedHtml = <pre dangerouslySetInnerHTML={innerHtml} style={{whiteSpace: 'break-spaces'}} />;

        let element;

        if (this.state.medium === 'tokens_view') {
            element = <div>{message.data.text}</div>;
        } else if (this.state.medium === 'text_view') {
            element = <div>{cleanText}</div>;
        } else {
            element = prerenderedHtml;
        }

        let bg = props.bg;
        let buttonVariant = bg === 'secondary' || bg === 'dark' ? 'outline-light' : 'outline-secondary';
        return (        
            <Card bg={props.bg} text={props.color} className="mb-3" style={{color:'red'}}>
                <Card.Header>{props.header}</Card.Header>
                <Card.Body>
                    <ButtonGroup className="mb-3" size="sm">
                        <Button variant={buttonVariant} onClick={this.handleDebugView}
                            active={this.state.medium === 'tokens_view'}
                        >
                            Raw view
                        </Button>
                        <Button variant={buttonVariant} onClick={this.handleTextView}
                            active={this.state.medium === 'text_view'}
                        >
                            Text view
                        </Button>
                        <Button variant={buttonVariant} onClick={this.handleHtmlView}
                            active={this.state.medium === 'html_view'}
                        >
                            HTML view
                        </Button>
                    </ButtonGroup>
                    {element}

                    {message.data.audio && (
                        <audio controls className="mt-3">
                            <source src={message.data.audio} type="audio/wav" />
                            Your browser does not support the audio element.
                        </audio>
                    )}

                    {message.data.attached_files && message.data.attached_files.length > 0 && (
                        <div className="mt-3">
                            <Accordion>
                                <Accordion.Item eventKey="0">
                                    <Accordion.Header>Attached documents</Accordion.Header>
                                    <Accordion.Body>
                                        <ul>
                                            {message.data.attached_files.map((file, idx) => <li key={idx}>{file}</li>)}
                                        </ul>
                                        <pre dangerouslySetInnerHTML={attachmentsHtml} style={{whiteSpace: 'break-spaces'}} />
                                    </Accordion.Body>
                                </Accordion.Item>
                            </Accordion>
                        </div>
                    )}

                    {message.data.image && (
                        <div className="mt-3">
                            <img src={message.data.image} alt="User uploaded image" style={{ height: '200px'}} />
                        </div>
                    )}
                </Card.Body>
                <Card.Footer>
                    <div>
                        <Pagination size="sm">{items}</Pagination>
                    </div>

                    {onRegenerate && 
                        <Button onClick={e => onRegenerate(pathItem) }>Regenerate</Button>
                    }
                </Card.Footer>
            </Card>
        );
    }
};


function HumanMessage(props) {
    return <Message bg="light" color="dark" header="Human" text={props.text} pathItem={props.pathItem} 
            message={props.message} onBranchSwitch={props.onBranchSwitch} />;
}

function AIMessage(props) {
    return <Message bg="secondary" color="light" header="AI" text={props.text} pathItem={props.pathItem}
            message={props.message} onBranchSwitch={props.onBranchSwitch} onRegenerate={props.onRegenerate} />;
}

function ReplyInProgress(props) {
    return (
        <Card bg="secondary" text="light" className="mb-3">
            <Card.Header>
                <span>AI  </span>
                <div style={{float: "right"}}>
                    <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                    />
                    <span>  Generating response...</span>
                </div>
            </Card.Header>
            <Card.Body>
                <Card.Text>{props.text}</Card.Text>
            </Card.Body>
        </Card>
    );
};


const RAW_MODE = "Raw mode";
const CHAT_MODE = "Chat mode";
const INSTRUCTION_MODE = "Instruction mode";


function ModeSelectionForm(props) {
    return (
        <Form className="mt-2">
            <Form.Check defaultChecked inline type='radio' value={RAW_MODE} name="mode" id="raw_mode_id" 
                label={RAW_MODE} onChange={props.onRawMode} />
            <Form.Check inline type='radio' value={CHAT_MODE} name="mode" id="chat_mode_id" 
                label={CHAT_MODE} onChange={props.onChatMode} />
            <Form.Check inline type='radio' value={INSTRUCTION_MODE} name="mode" id="instruction_mode_id" 
                label={INSTRUCTION_MODE} onChange={props.onInstructionMode} />
        </Form>
    );
}


class ActiveChat extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            prompt: "",
            system_message: "",
            configuration: null,
            voice_id: "",
            chatTree: {
                children: []
            },
            treePath: [],
            completion: "",
            inProgress: false,
            contextLoaded: false,
            loadingConversation: true,
            mode: RAW_MODE,
            model_name: LLAMA3_MODEL,
            
            //llm settings
            temperature: 0.8,
            top_k: 40,
            top_p: 0.95,
            min_p: 0.05,
            repeat_penalty: 1.1,
            n_predict: 1024,

            toolText: "",
            tools: [],
            submissionErrors: [],
            generationError: "",

            imageUri: "",
            attachments: [],

            //ugly patch to force resetting the prompt form
            submitSuccessCounter: 0
        };

        this.handleInput = this.handleInput.bind(this);
        this.handleSubmitPrompt = this.handleSubmitPrompt.bind(this);
        this.handleGenerate = this.handleGenerate.bind(this);
        this.handleBranchSwitch = this.handleBranchSwitch.bind(this);
        this.handleRegenerate = this.handleRegenerate.bind(this);

        this.handleRawModeSwitch = this.handleRawModeSwitch.bind(this);
        this.handleChatModeSwitch = this.handleChatModeSwitch.bind(this);
        this.handleInstructionModeSwitch = this.handleInstructionModeSwitch.bind(this);

        this.handleTemperatureChange = this.handleTemperatureChange.bind(this);
        this.handleTopKChange = this.handleTopKChange.bind(this);
        this.handleTopPChange = this.handleTopPChange.bind(this);
        this.handleMinPChange = this.handleMinPChange.bind(this);
        this.handleMaxTokensChange = this.handleMaxTokensChange.bind(this);
        this.handleRepeatPenaltyChange = this.handleRepeatPenaltyChange.bind(this);
        this.handleSystemMessageChanged = this.handleSystemMessageChanged.bind(this);
        this.handleImageUpload = this.handleImageUpload.bind(this);
        this.handleDirectoryUpload = this.handleDirectoryUpload.bind(this);
    }

    componentDidMount() {
        const id = this.props.router.params.id;
        const treeBankUrl = `/chats/treebanks/${id}/`;
        const chatUrl = `/chats/chats/${id}/`;

        let loadedTree = false;
        let loadedSettings = false;

        const declareLoaded = () => {
            if (loadedTree && loadedSettings) {
                this.setState({ loadingConversation: false });
            }
        }

        fetchTree(treeBankUrl).then(result => {
            this.setState({
                chatTree: result.tree,
                treePath: result.path
            });
        }).finally(() => {
            loadedTree = true;
            declareLoaded();
        });

        let fetcher = new GenericFetchJson();

        fetcher.performFetch(chatUrl).then(data => {
            if (!data.configuration_ro) {
                return;
            }

            let config = data.configuration_ro;
            let tools = (config && config.tools) || [];
            let system_message = data.system_message || (config && config.system_message_ro && config.system_message_ro.text) || "";
            let voice_id = (config && config.voice_id) || "";

            this.setState({
                system_message,
                configuration: config,
                tools,
                voice_id
            });

            let preset = config.preset_ro;
            console.log("preset:", preset, "data", data, "sys message", system_message);
            if (preset) {
                this.setState({
                    temperature: preset.temperature,
                    top_k: preset.top_k,
                    top_p: preset.top_p,
                    min_p: preset.min_p,
                    repeat_penalty: preset.repeat_penalty,
                    n_predict: preset.n_predict
                });
            }

            if (tools.length > 0) {
                fetcher.performFetch(`/chats/tools-spec/?conf_id=${config.id}`).then(data => {
                    console.log("NEW DATA:", data)
                    this.setState({ toolText: data.spec });
                }).catch(reason => {
                    console.error(reason);
                    //add error handling here
                });
            }
            
            console.log(data);
        }).finally(() => {
            loadedSettings = true;
            declareLoaded();
        });

    }

    handleInput(text) {
        this.setState({ prompt: text, completion: "" });
    }

    handleSubmitPrompt(e) {
        e.preventDefault();

        let leaf = traverseTree(this.state.chatTree, this.state.treePath);

        let chatId;
        if (this.state.treePath.length === 0) {
            chatId = this.props.router.params.id;
        } else {
            chatId = null;
        }

        let leafId = leaf.id || null;
        this.setState({ inProgress: true });

        let promise = this.postUserMessage(
            this.state.prompt, leafId, chatId, this.state.imageUri, this.state.attachments
        );

        promise.then(message => {
            this.setState(prevState => {
                let res = addMessage(
                    prevState.chatTree, prevState.treePath, leafId, message
                );

                console.log("submit data")
                console.log(res.tree)
                console.log(res.thread)

                return {
                    inProgress: true,
                    completion: "",
                    imageUri: "",
                    attachments: [],
                    chatTree: res.tree,
                    treePath: res.thread,
                    submissionErrors: [],
                    submitSuccessCounter: prevState.submitSuccessCounter + 1
                };
            }, this.generateData);
        }).catch(reason => {
            console.error("Reason is ", reason)
            
            let submissionErrors;
            if (reason.hasOwnProperty("fieldErrors")) {
                submissionErrors = reason.fieldErrors.text;
            } else {
                submissionErrors = [reason.error];
            }

            this.setState({ submissionErrors });
        });
    }

    postUserMessage(text, parent, chatId, imageDataUri, attachments) {
        const formData = new FormData();
        formData.append("text", text);

        if (parent) {
            formData.append("parent", parent);
        }

        if (chatId) {
            formData.append("chat", chatId);
        }

        if (imageDataUri) {
            formData.append("image_data_uri", imageDataUri);
        }

        let relativePaths = {};

        if (attachments && attachments.length > 0) {
            for (let i = 0; i < attachments.length; i++) {
                const fileWrapper = attachments[i];
                const file = fileWrapper.file;
                let fileId = `File_${i}`;

                relativePaths[fileId] = {
                    path: fileWrapper.relativePath,
                    name: file.name
                }

                formData.append("attachments", file, fileId);
            }
        }

        if (relativePaths) {
            let pathsJson = JSON.stringify(relativePaths);
            formData.append("relative_paths", pathsJson);
        }

        //handle errors gracefully
        const params = {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrftoken
            }
        };

        return fetch('/chats/messages/', params).then(
            response => response.json()
        ).catch(reason => {
            console.error(reason);
        });
    }

    postMessage(text, parent, chatId, imageDataUri) {
        let data = {
            text,
            parent
        };

        if (chatId) {
            data["chat"] = chatId;
        }

        if (imageDataUri) {
            data["image_data_uri"] = imageDataUri;
        }

        let fetcher = new GenericFetchJson();
        fetcher.method = 'POST';
        fetcher.body = data;
 
        return fetcher.performFetch('/chats/messages/');
    }

    handleGenerate() {
        this.setState({ inProgress: true }, this.generateData);
    }

    handleRegenerate(pathItem) {
        let self = this;

        this.setState(prevState => {
            let node = getNodeById(prevState.chatTree, pathItem.nodeId);
            let prefix = collapseThread(prevState.treePath, node.parent.id);
            return {
                inProgress: true,
                completion: "",
                treePath: prefix,
                contextLoaded: false
            }
        }, function() {
            setTimeout(() => {
                self.generateData();
            }, 100);
        });
    }

    generateData() {
        this.saveSystemMessage();

        let leaf = traverseTree(this.state.chatTree, this.state.treePath);

        let llmSettings = {
            temperature: this.state.temperature,
            top_k: this.state.top_k,
            top_p: this.state.top_p,
            min_p: this.state.min_p,
            n_predict: this.state.n_predict,
            repeat_penalty: this.state.repeat_penalty
        };

        let inferenceConfig = {
            repo_id: this.state.configuration.model_repo,
            file_name: this.state.configuration.file_name,
            launch_params: this.state.configuration.launch_params
        };

        let voice_id = this.state.voice_id;

        let committedText = "";
        
        let streamer = new WebsocketResponseStreamer('/chats/generate_reply/', 'POST', this.props.websocket);
        
        let completionGenerator = new ToolAugmentedCompletionGenerator(
            inferenceConfig, llmSettings, leaf.id, streamer, this.props.socketSessionId, voice_id
        );

        completionGenerator.onChunk = (chunk) => {
            this.setState(prevState => ({
                completion: prevState.completion + chunk
            }));
        };

        completionGenerator.onPaused = textSegment => {
            committedText += textSegment;

            this.setState({ completion: committedText });
            return "0";
        };

        const socketListener = msgEvent => {
            let payload = JSON.parse(msgEvent.data);
            if (payload.event === "generation_complete") {
                this.props.websocket.removeEventListener("message", socketListener);
                let message = payload.data;

                this.setState(prevState => {
                    let res = addMessage(
                        prevState.chatTree, prevState.treePath, leaf.id, message
                    );
    
                    return {
                        prompt: "",
                        completion: "",
                        inProgress: false,
                        chatTree: res.tree,
                        contextLoaded: true,
                        treePath: res.thread,
                        generationError: ""
                    }
                });
            } else if (payload.event === "generation_error") {
                let reason = payload.data;
                console.error("Generation failed: ", reason);
                this.setState({
                    prompt: "",
                    completion: "",
                    inProgress: false,
                    contextLoaded: true,
                    generationError: reason
                });
            }
        };
        this.props.websocket.addEventListener("message", socketListener);

        let bufferingPlayer = new BufferringAudioAutoPlayer();
        captureAndPlaySpeech(this.props.websocket, bufferingPlayer);

        completionGenerator.generate().then(() => {
            let generatedText = this.state.completion;
            bufferingPlayer.calculateBufferSize(generatedText);
        });
    }

    saveSystemMessage() {
        const id = this.props.router.params.id;
        const url = `/chats/chats/${id}/`;
        const fetcher = new GenericFetchJson();
        fetcher.method = "PATCH";
        fetcher.body = {
            system_message: this.state.system_message
        };
        fetcher.performFetch(url);
    }

    handleBranchSwitch(message, newBranchId) {
        console.log("handle branch switch", message, newBranchId);

        if (newBranchId < 0 || newBranchId >= message.numSiblings) {
            throw Exception(`Out of bounds: ${newBranchId}`);
        }

        let node = getNodeById(this.state.chatTree, message.id);

        let newId = node.parent.replies[newBranchId].id;
        console.log('found node');
        console.log(node);
        let path = selectThread(this.state.chatTree, newId);
        console.log(path);
        console.log(this.state.treePath);

        this.setState({
            treePath: path,
            contextLoaded: false
        })
    }

    hasNoReply() {
        return this.state.treePath.length % 2 === 1 && !this.state.inProgress;
    }

    handleRawModeSwitch(e) {
        this.setState({ "mode": RAW_MODE });
    }

    handleChatModeSwitch(e) {
        this.setState({ "mode": CHAT_MODE });
    }

    handleInstructionModeSwitch(e) {
        this.setState({ "mode": INSTRUCTION_MODE });
    }

    handleTemperatureChange(e) {
        this.setState({ "temperature": e.target.value });
    }

    handleTopKChange(e) {
        this.setState({ "top_k": e.target.value });
    }

    handleTopPChange(e) {
        this.setState({ "top_p": e.target.value });
    }

    handleMinPChange(e) {
        this.setState({ "min_p": e.target.value });
    }

    handleMaxTokensChange(e) {
        this.setState({ "n_predict": e.target.value });
    }

    handleRepeatPenaltyChange(e) {
        this.setState({ "repeat_penalty": e.target.value });
    }

    handleSystemMessageChanged(e) {
        this.setState({ system_message: e.target.value });
    }

    handleImageUpload(dataUri) {
        this.setState({ imageUri: dataUri });
    }

    handleDirectoryUpload(attachments) {
        this.setState({ attachments });
    }
    render() {
        let radio = <ModeSelectionForm 
                        onRawMode={this.handleRawModeSwitch}
                        onChatMode={this.handleChatModeSwitch}
                        onInstructionMode={this.handleInstructionModeSwitch} />
 
        let eventHandlers = {
            onTemperatureChange: this.handleTemperatureChange,
            onTopKChange: this.handleTopKChange,
            onTopPChange: this.handleTopPChange,
            onMinPChange: this.handleMinPChange,
            onMaxTokensChange: this.handleMaxTokensChange,
            onRepeatPenaltyChange: this.handleRepeatPenaltyChange
        };

        let settings = {
            temperature: this.state.temperature,
            topK: this.state.top_k,
            topP: this.state.top_p,
            minP: this.state.min_p,
            nPredict: this.state.n_predict,
            repeatPenalty: this.state.repeat_penalty
        };

        let settingsWidget = (
            <CollapsibleLLMSettings settings={settings} eventHandlers={eventHandlers} />
        );

        let systemMessageWidget = (
            <CollapsibleEditableSystemMessage systemMessage={this.state.system_message} 
                inProgress={this.state.inProgress}
                onChange={this.handleSystemMessageChanged} />
        );

        let spinner = (
            <Spinner as="span"
                     animation="border"
                     size="lg"
                     role="status"
                     aria-hidden="true" />
        );

        if (this.state.loadingConversation && spinner) {
            return (
                <div>
                    <span>Loading the chat...</span>
                    {spinner}
                </div>
            );
        }

        let toolItems = this.state.tools.map((toolName, index) => 
            <Badge key={index} variant="primary">{toolName}</Badge>
        );

        if (this.hasNoReply()) {
            return (
                <div>
                    {settingsWidget}
                    {systemMessageWidget}
                    {this.state.tools.length > 0 && <div className="mt-3 mb-3">Tools used by LLM: {toolItems}</div>}
                    {radio}
                    <ConversationTree tree={this.state.chatTree} treePath={this.state.treePath}
                            onBranchSwitch={this.handleBranchSwitch} />
                    {this.state.generationError && <Alert variant="danger">
                        {this.state.generationError}</Alert>
                    }
                    <div>It looks like AI did not reply for some reason</div>

                    <Button onClick={this.handleGenerate}>Generate reply</Button>
                </div>
            );
        }

        return (
            <div>
                {settingsWidget}
                {systemMessageWidget}
                {this.state.tools.length > 0 && <div className="mt-3 mb-3">Tools used by LLM: {toolItems}</div>}
                {radio}
                <ConversationTree tree={this.state.chatTree} treePath={this.state.treePath}
                        onBranchSwitch={this.handleBranchSwitch}
                        onRegenerate={this.handleRegenerate} />
                {this.state.inProgress && <ReplyInProgress text={this.state.completion} />}
                <PromptForm submissionErrors={this.state.submissionErrors}
                    onSubmit={this.handleSubmitPrompt}
                    onTextChange={this.handleInput}
                    onImageUpload={this.handleImageUpload}
                    onDirectoryUpload={this.handleDirectoryUpload}
                    text={this.state.prompt}
                    imageUri={this.state.imageUri}
                    inProgress={this.state.inProgress}
                    key={this.state.submitSuccessCounter} />
            </div>
        );
    }
};


class PromptForm extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            starting: false,
            recording: false,
            processing: false,
            micError: "",
            recordingError: ""
        };

        this.startRecording = this.startRecording.bind(this);
        this.stopRecording = this.stopRecording.bind(this);

        this.handleInput = this.handleInput.bind(this);
        this.handleUploadedImage = this.handleUploadedImage.bind(this);
        this.handleDocumentsUpload = this.handleDocumentsUpload.bind(this);

        this.mediaRecorder = null;
        this.voice = [];
    }

    componentDidMount() {
        
    }
    
    handleInput(e) {
        this.props.onTextChange(e.target.value);
    }

    handleUploadedImage(e) {
        const fileList = e.target.files;
        if (fileList.length === 0) {
            return;
        }

        const file = fileList[0];
        const reader = new FileReader();
        reader.onload = (e) => {
            let imageUri = e.target.result;
            this.props.onImageUpload(imageUri);
        };
        reader.readAsDataURL(file);
    }

    handleDocumentsUpload(filesWithPath) {
        this.props.onDirectoryUpload(filesWithPath);
    }
    startRecording() {
        this.setState({ micError: "", recordingError: "", starting: true });
        this.voice = [];
        let self = this;

        if (this.mediaRecorder) {
            try {
                this.mediaRecorder.start();
                this.setState({ recording: true, starting: false });
                return;
            } catch (e) {
                this.mediaRecorder = null;
            }
        }

        navigator.mediaDevices.getUserMedia({ audio: true}).then(stream => {
            const mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.addEventListener("dataavailable",function(event) {
                self.voice.push(event.data);
            });
    
            mediaRecorder.addEventListener("stop", function() {
                self.sendRecording(self.voice);
            });

            self.mediaRecorder = mediaRecorder;
            this.mediaRecorder.start();
            this.setState({ recording: true });
        }).catch(reason => {
            console.error("Cannot use microphone: ", reason);
            this.setState({ micError: reason.message, processing: false, recording: false });
            this.mediaRecorder = null;
        }).finally(() => {
            this.setState({ starting: false });
        });
    }

    sendRecording(voiceRecording) {
        const url = '/chats/transcribe_speech/';
        const voiceBlob = new Blob(voiceRecording, {
            type: 'application/octet-stream'
        });

        this.setState({ processing: true });

        let fetcher = new GenericFetchJson();
        fetcher.body = voiceBlob;
        fetcher.method = 'POST';

        fetcher.performFetch(url).then(data => {
            this.props.onTextChange(this.props.text + data.text);
        }).catch(reason => {
            console.error(reason.error);
            this.setState({
                recordingError: "Spech-to-text backend/server is malfunctioning or unavailable"
            });
        }).finally(() => {
            this.setState({ processing: false });
        });
    }

    stopRecording() {
        this.mediaRecorder.stop();
        this.setState({ recording: false });
    }

    render() {
        let busy = this.state.recording || this.state.processing;
        let submissionErrorsAlerts = this.props.submissionErrors.map((error, index) =>
            <Alert key={index} variant="danger" className="mb-3">{error}</Alert>
        );

        let button;
        if (this.props.inProgress) {            
            button = <Button variant="primary" type="submit" disabled>
                <Spinner
                    as="span"
                    animation="border"
                    size="sm"
                    role="status"
                    aria-hidden="true"
                />
                <span>  Generating</span>
            </Button>;
        } else {            
            button = (
                <Button variant="primary" type="submit" disabled={this.props.text.length === 0}>
                    Generate completion
                </Button>
            );
        }

        return (
            <Form onSubmit={this.props.onSubmit}>
                <Form.Group className="mb-3" controlId="exampleForm.ControlTextarea1">
                    <Form.Label>Use LLM to complete your prompt</Form.Label>
                    <div style={{ position: 'relative', height: '100%' }}>
                    <Form.Control as="textarea" rows={10} placeholder="Enter a prompt here"
                            onInput={this.handleInput}
                            value={this.props.text}
                            disabled={busy || this.props.inProgress}
                            style={{ paddingTop: '34px' }} />
                    <div style={{ position: 'absolute', right: '0px', top: '-15px'}} className="mt-3">
                        {!busy && !this.props.inProgress && (
                            <Button variant="secondary" onClick={this.startRecording} disabled={this.state.starting}>
                                Start voice dictation
                            </Button>
                        )}
                        {this.state.recording && !this.state.processing && (
                            <Button variant="secondary" onClick={this.stopRecording}>
                                Stop voice dictation
                            </Button>
                        )}
                        </div>
                    </div>
                    {this.state.micError && (
                        <Alert variant="danger" className="mt-3">
                            Cannot use microphone (check permissions). The original error message: {this.state.micError}
                        </Alert>
                    )}
                    {this.state.recordingError && (
                        <Alert variant="danger" className="mt-3">{this.state.recordingError}</Alert>
                    )}
                    {this.state.recording && <div className="mt-3 mb-3">Speak, please</div>}
                    {this.state.processing && <div className="mt-3 mb-3">Speech recognition in progress...</div>}
                    {submissionErrorsAlerts.length > 0 && 
                        <div className="mt-3">{submissionErrorsAlerts}</div>
                    }
                </Form.Group>
                <details className="mb-3">
                    <summary>Attach files</summary>
                    <Form.Group controlId="imageFile" className="mt-3 mb-3">
                        <Row className="align-items-center">
                            <Form.Label column xs="auto">Upload image</Form.Label>
                            <Col xs="auto">
                                <Form.Control type="file" onChange={this.handleUploadedImage} />
                            </Col>
                        </Row>
                    </Form.Group>

                    <div className="mb-3">
                        {this.props.imageUri && <img src={this.props.imageUri} style={{ height: '200px'}} />}
                    </div>

                    <DocumentUploadComponent onDocumentsUpload={this.handleDocumentsUpload} className="mb-3" />
                </details>
                {button}
            </Form>
        );
    }
}


class FileWrapper {
    constructor(file, relativePath) {
        this.file = file;
        this.relativePath = relativePath || file.name;
    }
}

class DocumentUploadComponent extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            uploadedFiles: [],
            uploadedDirFiles: [],
            filteredFiles: [],
            ignoreList: [],
            pattern: ""
        };

        this.handleChangePattern = this.handleChangePattern.bind(this);
        this.handleAddPattern = this.handleAddPattern.bind(this);
        this.updateFilteredFilesAndNotifyParent = this.updateFilteredFilesAndNotifyParent.bind(this);
    }

    handleFilesUpload(e) {
        this.setState({
            uploadedFiles: e.target.files
        }, this.updateFilteredFilesAndNotifyParent);
    }

    handleDirectoryUpload(e) {
        this.setState({
            uploadedDirFiles: e.target.files
        }, this.updateFilteredFilesAndNotifyParent);
    }

    updateFilteredFilesAndNotifyParent() {
        let uploadedFiles = [...this.state.uploadedFiles];
        let uploadedDirFiles = [...this.state.uploadedDirFiles];

        let filteredFiles = this.filterAllFiles(uploadedFiles, uploadedDirFiles);

        this.setState({ filteredFiles });
        this.props.onDocumentsUpload(filteredFiles);
    }

    filterAllFiles(uploadedFiles, dirFiles) {
        function matches(str, patterns) {
            for (let pattern of patterns) {
                if (str.search(pattern) !== -1) {
                    return true;
                }
            }
            return false;
        }

        let filteredDirFiles = dirFiles.filter(file =>
            !matches(file.webkitRelativePath || file.name, this.state.ignoreList)
        ).map(file => new FileWrapper(file, file.webkitRelativePath || file.name));

        let filteredFiles = uploadedFiles.filter(file => 
            !matches(file.name, this.state.ignoreList)
        ).map(file => new FileWrapper(file));

        return [...filteredDirFiles, ...filteredFiles];
    }

    handleChangePattern(e) {
        this.setState({ pattern: e.target.value });
    }

    handleAddPattern() {
        this.setState((prevState) => ({
            ignoreList: [...prevState.ignoreList, prevState.pattern],
            pattern: ""
        }), this.updateFilteredFilesAndNotifyParent);
    }
    render() {
        const ignoreList = this.state.ignoreList.map((item, idx) => 
            <ListGroup.Item key={idx}>{item}</ListGroup.Item>
        );

        let filePaths = this.state.filteredFiles.map(item => item.relativePath);

        let filesToUpload = filePaths.map((item, idx) => <li key={idx}>{item}</li>);

        return (
            <div>
                <Form.Group controlId="documentUpload" className="mb-3">
                    <Row className="align-items-center">
                        <Form.Label column xs="auto">Upload document</Form.Label>
                        <Col xs="auto">
                            <Form.Control type="file" onChange={e => this.handleFilesUpload(e)} multiple  />
                        </Col>
                    </Row>
                </Form.Group>

                <Form.Group controlId="documentDirectoryUpload" className="mb-3">
                    <Row className="align-items-center">
                        <Form.Label column xs="auto">Upload document directory</Form.Label>
                        <Col xs="auto">
                            <Form.Control type="file" onChange={e => this.handleDirectoryUpload(e)} webkitdirectory="true" multiple  />
                        </Col>
                    </Row>
                </Form.Group>

                {filesToUpload.length > 0 && (
                    <div className="mb-3">
                        <header>
                            <h4>Files to be uploaded</h4>
                        </header>
                        <ul style={{ maxHeight: '300px', overflow: 'auto' }}>{filesToUpload}</ul>
                    </div>
                )}

                <h4>Optionally, add file path patterns to exclude certain files</h4>

                <ListGroup style={{ overflow: 'auto', maxHeight: '200px' }} className="mb-3">{ignoreList}</ListGroup>

                <Form.Group controlId="addExcludePattern" className="mb-3">
                    <Row>
                        <Col xs="auto">
                            <Form.Control value={this.state.pattern} onChange={this.handleChangePattern} type="text" />
                        </Col>
                        <Col xs="auto">
                            <Button onClick={this.handleAddPattern}>Add pattern</Button>
                        </Col>
                    </Row>
                </Form.Group>
            </div>
        );
    }
}

ActiveChat = withRouter(ActiveChat);

export {
    ActiveChat
}