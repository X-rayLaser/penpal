import React from 'react';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Accordion from 'react-bootstrap/Accordion';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Pagination from 'react-bootstrap/Pagination';
import Alert from 'react-bootstrap/Alert';
import { streamJsonResponse } from './utils';
import { withRouter, generateResponse } from "./utils";
import { 
    fetchTree, addNode, addMessage, selectThread, appendThread, collapseThread,
    getNodeById, getThreadMessages, getConversationText, isHumanText
} from './tree';
import { CollapsibleLLMSettings } from './presets';
import { 
    CollapsibleSystemMessage, CollapsibleEditableSystemMessage
} from './components';
import { GenericFetchJson } from './generic_components';

class TextTemplate {
    constructor(template) {
        this.template = template;
    }

    render(text) {
        return this.template.replace("%message", text);
    }
};


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


function Message(props) {
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
    
    return (        
        <Card bg={props.bg} text={props.color} className="mb-3" style={{color:'red'}}>
            <Card.Header>{props.header}</Card.Header>
            <Card.Body>
                <pre dangerouslySetInnerHTML={innerHtml} style={{whiteSpace: 'break-spaces'}} />
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
            system_message: null,
            configuration: null,
            chatTree: {
                children: []
            },
            treePath: [],
            completion: "",
            inProgress: false,
            contextLoaded: false,
            mode: RAW_MODE,
            
            //llm settings
            temperature: 0.8,
            top_k: 40,
            top_p: 0.95,
            min_p: 0.05,
            repeat_penalty: 1.1,
            n_predict: 1024,

            toolText: "",
            submissionErrors: [],
            generationError: ""
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
    }

    componentDidMount() {
        const id = this.props.router.params.id;
        const treeBankUrl = `/chats/treebanks/${id}/`;
        const chatUrl = `/chats/chats/${id}/`;

        fetchTree(treeBankUrl).then(result => {
            this.setState({
                chatTree: result.tree,
                treePath: result.path
            });
        });

        fetch(chatUrl, {
            headers: {
                "Accept": "application/json"
            }
        }).then(response => response.json()).then(data => {
            if (!data.configuration_ro) {
                return;
            }

            this.setState({
                system_message: data.configuration_ro.system_message_ro,
                configuration: data.configuration_ro
            });

            let preset = data.configuration_ro.preset_ro;
            console.log("preset:", preset, "data", data, "sys message", data.configuration_ro.system_message_ro);
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

            let config = data.configuration_ro;

            let tools = (config && config.tools) || [];

            if (tools.length > 0) {
                fetch(`/chats/tools-spec/?conf_id=${config.id}`).then(response => 
                    response.json()
                ).then(data => {
                    console.log("NEW DATA:", data)
                    this.setState({ toolText: data.spec });
                }).catch(reason => {
                    console.error(reason);
                    //add error handling here
                });
            }
            
            console.log(data);
        });

    }

    handleInput(event) {
        this.setState({ prompt: event.target.value, completion: "" });
    }

    handleSubmitPrompt(e) {

        e.preventDefault();

        console.log(this.state.chatTree);
        console.log(this.state.treePath);

        let leaf = traverseTree(this.state.chatTree, this.state.treePath);

        let chatId;
        if (this.state.treePath.length === 0) {
            chatId = this.props.router.params.id;
        } else {
            chatId = null;
        }

        let leafId = leaf.id || null;
        let promise = this.postText(this.state.prompt, leafId, chatId);

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
                    chatTree: res.tree,
                    treePath: res.thread,
                    submissionErrors: []
                }
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

    postText(text, parent, chatId) {
        let data = {
            text,
            parent
        };

        if (chatId) {
            data["chat"] = chatId;
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
        let leaf = traverseTree(this.state.chatTree, this.state.treePath);
        let committedText = "";

        const handleChunk = (generatedText, chunk) => {
            this.setState(prevState => {
                return {
                    completion: prevState.completion + chunk
                }
            });
        };

        const handlePause = textSegment => {
            //get request to the server to calculate something
            committedText += textSegment;

            this.setState({
                completion: committedText
            });
            return "0";
        }

        const handleDone = () => {
            let generatedText = this.state.completion;
            console.log(`handleDone called ${this.state.completion}`);
            console.log(generatedText);

            let promise = this.postText(generatedText, leaf.id);

            promise.then(message => {
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
            });
        }
        const handleError = reason => {
            this.setState({ 
                prompt: "",
                completion: "",
                inProgress: false,
                contextLoaded: true,
                generationError: reason
            });
        };

        //let prompt = this.preparePrompt(leaf);
        let prompt = this.preparePromptWithRecreatedConversation();

        console.log(`sys message: ${this.state.system_message}`)
        console.log("full prompt!!!:")
        console.log(prompt);

        let llmSettings = {
            temperature: this.state.temperature,
            top_k: this.state.top_k,
            top_p: this.state.top_p,
            min_p: this.state.min_p,
            n_predict: this.state.n_predict,
            repeat_penalty: this.state.repeat_penalty
        };

        generateResponse(prompt, llmSettings, handleChunk, handlePause, handleDone, handleError);
    }

    preparePrompt(leaf) {
        if (this.state.contextLoaded) {
            return leaf.data.text + "\n";
        } else {
            return this.preparePromptWithRecreatedConversation();
        }
    }

    preparePromptWithRecreatedConversation() {
        let questionTemplateText;
        let answerTemplateText;

        if (this.state.mode === RAW_MODE) {
            questionTemplateText = "%message ";
            answerTemplateText = questionTemplateText;
        } else if (this.state.mode === CHAT_MODE) {
            questionTemplateText = "<human>%message</human>";
            answerTemplateText = "<bot>%message</bot>"
        } else if (this.state.mode === INSTRUCTION_MODE) {
            questionTemplateText = "[INST]%message[/INST]";
            answerTemplateText = "%message";
        } else {
            console.error(`Unknown mode ${this.state.mode}`);
            throw `Unknown mode ${this.state.mode}`;
        }
        let questionTemplate = new TextTemplate(questionTemplateText);
        let answerTemplate = new TextTemplate(answerTemplateText);

        let sysMessageText = (this.state.system_message && this.state.system_message.text) || "";

        let toolText = this.state.toolText;
        if (toolText) {
            sysMessageText += toolText;
        }

        let conversation = getConversationText(
            this.state.chatTree, this.state.treePath,
            questionTemplate, answerTemplate, sysMessageText
        );

        if (this.state.mode === INSTRUCTION_MODE) {
            conversation = "<s>" + conversation;
        }

        if (this.state.mode === CHAT_MODE) {
            conversation += "<bot>";
        }

        return conversation;
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
        let newMessage;
        if (this.state.system_message) {
            newMessage = JSON.parse(JSON.stringify(this.state.system_message));
        } else {
            newMessage = {
                name: ""
            }
        }

        newMessage.text = e.target.value;

        this.setState({ system_message: newMessage });
    }

    render() {
        let textarea = (
            <Form.Control as="textarea" rows={10} placeholder="Enter a prompt here"
                          onInput={this.handleInput}
                          value={this.state.prompt}
                          disabled={this.state.inProgress} />
        );
        let radio = <ModeSelectionForm 
                        onRawMode={this.handleRawModeSwitch}
                        onChatMode={this.handleChatModeSwitch}
                        onInstructionMode={this.handleInstructionModeSwitch} />
        let button;

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

        let submissionErrorsAlerts = this.state.submissionErrors.map((error, index) =>
            <Alert key={index} variant="danger" className="mb-3">{error}</Alert>
        );

        if (this.hasNoReply()) {
            return (
                <div>
                    {radio}
                    {settingsWidget}
                    {this.state.system_message && systemMessageWidget}
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

        if (this.state.inProgress) {            
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
                <Button variant="primary" type="submit" disabled={this.state.prompt.length === 0}>
                    Generate completion
                </Button>
            );
        }
        return (
            <div>
                {radio}
                {settingsWidget}
                {this.state.system_message && systemMessageWidget}
                <ConversationTree tree={this.state.chatTree} treePath={this.state.treePath}
                        onBranchSwitch={this.handleBranchSwitch}
                        onRegenerate={this.handleRegenerate} />
                {this.state.inProgress && <ReplyInProgress text={this.state.completion} />}
                {!this.state.inProgress && 
                <Form onSubmit={this.handleSubmitPrompt}>
                    <Form.Group className="mb-3" controlId="exampleForm.ControlTextarea1">
                        <Form.Label>Use LLM to complete your prompt</Form.Label>
                        {textarea}

                        {submissionErrorsAlerts.length > 0 && 
                            <div className="mt-3">{submissionErrorsAlerts}</div>
                        }
                    </Form.Group>
                    {button}
                </Form>
                }
            </div>
        );
    }
};

ActiveChat = withRouter(ActiveChat);

export {
    ActiveChat
}