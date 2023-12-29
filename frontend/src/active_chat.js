import React from 'react';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Pagination from 'react-bootstrap/Pagination';
import { streamJsonResponse } from './utils';
import { withRouter } from "./utils";
import { 
    fetchTree, addNode, addMessage, selectThread, appendThread, collapseThread,
    getNodeById, getThreadMessages, getConversationText, isHumanText
} from './tree';


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
        <Card bg={props.bg} text={props.color} className="mb-3">
            <Card.Header>{props.header}</Card.Header>
            <Card.Body>
                <pre dangerouslySetInnerHTML={innerHtml} />
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


class ActiveChat extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            prompt: "",
            chatTree: {
                children: []
            },
            treePath: [],
            completion: "",
            inProgress: false,
            contextLoaded: false
        };

        this.handleInput = this.handleInput.bind(this);
        this.handleSubmitPrompt = this.handleSubmitPrompt.bind(this);
        this.handleGenerate = this.handleGenerate.bind(this);
        this.handleBranchSwitch = this.handleBranchSwitch.bind(this);
        this.handleRegenerate = this.handleRegenerate.bind(this);
    }

    componentDidMount() {
        const id = this.props.router.params.id;
        const url = `/chats/treebanks/${id}/`;

        fetchTree(url).then(result => {
            this.setState({
                chatTree: result.tree,
                treePath: result.path
            });
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
                    treePath: res.thread
                }
            }, this.generateData);
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
        return fetch('/chats/messages/', {
            method: 'POST',
            body: JSON.stringify(data),
            headers: {
                "Content-Type": "application/json"
            }
        }).then(response => {
            return response.json();
        });
    }

    handleGenerate() {
        this.setState({ inProgress: true }, this.generateData);
    }

    handleRegenerate(pathItem) {
        console.log(`handle regenerate: ${pathItem}`);
        console.log(pathItem);

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
        let generatedText = "";

        const handleChunk = chunk => {
            generatedText = generatedText + chunk;

            this.setState(prevState => {
                return {
                    completion: prevState.completion + chunk
                }
            });
        };

        let leaf = traverseTree(this.state.chatTree, this.state.treePath);

        const handleDone = () => {
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
                        treePath: res.thread
                    }
                });
            });
        }
        let body;
        let questionTemplate = new TextTemplate("%message\n");
        let answerTemplate = new TextTemplate("%message\n");

        if (this.state.contextLoaded) {
            body = {
                prompt: leaf.text + "\n"
            };
        } else {
            let conversation = getConversationText(
                this.state.chatTree, this.state.treePath, questionTemplate, answerTemplate
            );

            body = {
                prompt: conversation + "",
                clear_context: true
            };
        }

        streamJsonResponse('/chats/generate_reply/', 'POST', body, handleChunk, handleDone);
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

    render() {
        let textarea;
        let button;
        
        if (this.state.treePath.length % 2 === 1 && !this.state.inProgress) {
            return (
                <div>
                    <ConversationTree tree={this.state.chatTree} treePath={this.state.treePath}
                            onBranchSwitch={this.handleBranchSwitch} />
                    <div>It looks like AI did not reply for some reason</div>

                    <Button onClick={this.handleGenerate}>Generate reply</Button>
                </div>
            );
        }

        if (this.state.inProgress) {
            textarea = (<Form.Control as="textarea" rows={10} placeholder="Enter a prompt here"
                onInput={this.handleInput}
                value={this.state.prompt}
                disabled />);
            
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
            textarea = (<Form.Control as="textarea" rows={10} placeholder="Enter a prompt here"
                onInput={this.handleInput}
                value={this.state.prompt} />);
            
            button = <Button variant="primary" type="submit">Generate completion</Button>;
        }
        return (
            <div>
                <ConversationTree tree={this.state.chatTree} treePath={this.state.treePath}
                        onBranchSwitch={this.handleBranchSwitch}
                        onRegenerate={this.handleRegenerate} />
                {this.state.inProgress && <ReplyInProgress text={this.state.completion} />}
                {!this.state.inProgress && 
                <Form onSubmit={this.handleSubmitPrompt}>
                    <Form.Group className="mb-3" controlId="exampleForm.ControlTextarea1">
                        <Form.Label>Use LLM to complete your prompt</Form.Label>
                        {textarea}
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