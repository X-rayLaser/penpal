import React from 'react';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Pagination from 'react-bootstrap/Pagination';
import { streamJsonResponse } from './utils';
import { withRouter } from "./utils";


class PathItem {
    constructor(branchId, prefixLength, node, parent) {
        this.branchId = branchId
        this.prefixLength = prefixLength
        this.node = node
        this.parent = parent
    }
}


function getConversationThread(chatTree, treePath) {
    let messages = [];

    treePath.forEach((item, index) => {
        messages.push({
            text: item.node.text,
            key: index,
            pathItem: item
        });
    });

    return messages;
}


function isHumanText(index) {
    return index % 2 === 0;
}


class TextTemplate {
    constructor(template) {
        this.template = template;
    }

    render(text) {
        return this.template.replace("%message", text);
    }
};


function getConversationText(chatTree, treePath, questionTemplate, answerTemplate) {
    let messages = getConversationThread(chatTree, treePath);
    let result = "";
    messages.forEach((msg, index) => {
        let template = isHumanText(index) ? questionTemplate : answerTemplate;
        result += template.render(msg.text);
    });

    return result;
}


function ConversationTree(props) {
    let messages = getConversationThread(props.tree, props.treePath);

    const items = messages.map(msg => {
        if (isHumanText(msg.key)) {
            return <HumanMessage key={msg.key} text={msg.text} pathItem={msg.pathItem} 
                    onBranchSwitch={props.onBranchSwitch} />
        } else {
            return <AIMessage key={msg.key} text={msg.text} pathItem={msg.pathItem}
                    onBranchSwitch={props.onBranchSwitch}
                    onRegenerate={props.onRegenerate} />
        }
    });

    return (
        <div className="mt-3">{items}</div>
    )
}


function getAppendedTree(tree, path, text, messageId) {
    let treeCopy = JSON.parse(JSON.stringify(tree));
    let pathCopy = copyTreePath(treeCopy, path);
    console.log("getappendedtree:"); console.log(path); console.log(pathCopy);

    let node = traverseTree(treeCopy, pathCopy);

    let newNode = {
        id: messageId,
        text,
        replies: []
    };
    node.replies.push(newNode);

    pathCopy.push(new PathItem(node.replies.length - 1, pathCopy.length, newNode, node));

    return {
        tree: treeCopy,
        leafIndex: node.replies.length - 1,
        node: newNode,
        parent: node,
        path: pathCopy
    };
}

function copyTreePath(tree, path) {
    let node = tree;

    let pathCopy = [];

    for (let i = 0; i < path.length; i++) {
        let item = path[i];
        let parent = node;
        node = node.replies[item.branchId];

        pathCopy.push(new PathItem(item.branchId, item.prefixLength, node, parent));
    }

    return pathCopy;
}


function traverseTree(tree, path) {
    //check if path is empty, then return tree root
    if (path.length === 0) {
        return tree;
    }
    let item = path[path.length - 1];
    return item.node;
}


function Message(props) {
    let pathItem = props.pathItem
    let numChildren = pathItem.parent.replies.length
    let active = pathItem.branchId + 1;
    let items = [];
    
    let onRegenerate = props.onRegenerate;

    function getHandler(key) {
        return e => {
            if (key !== active) {
                let newBranchId = key - 1
                props.onBranchSwitch(pathItem, newBranchId);
            }
        }
    }
    
    for (let i = 1; i <= numChildren; i++) {
        const handler = getHandler(i);
        items.push(
            <Pagination.Item key={i} active={i === active} onClick={handler}>
            {i}
            </Pagination.Item>
        );
    }
    return (
        <Card bg={props.bg} text={props.color} className="mb-3">
            <Card.Header>{props.header}</Card.Header>
            <Card.Body>
                <Card.Text>{props.text}</Card.Text>
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
            onBranchSwitch={props.onBranchSwitch} />;
}

function AIMessage(props) {
    return <Message bg="secondary" color="light" header="AI" text={props.text} pathItem={props.pathItem}
            onBranchSwitch={props.onBranchSwitch} onRegenerate={props.onRegenerate} />;
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
        let id = this.props.router.params.id;
        fetch(`/chats/treebanks/${id}/`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        }).then(response => response.json()).then(obj => {
            let tree;
            if (Object.keys(obj).length) {
                tree = {
                    replies: [obj]
                };

            } else {
                tree = {
                    replies: []
                }
            }

            let node = tree;
            let path = [];
            while (true) {
                if (node.replies.length === 0) {
                    break;
                }

                let parent = node;
                node = node.replies[0];
                path.push(new PathItem(0, path.length, node, parent));
            }

            this.setState({
                chatTree: tree,
                treePath: path
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
                let res = getAppendedTree(
                    prevState.chatTree, prevState.treePath, message.text, message.id
                );

                return {
                    inProgress: true,
                    completion: "",
                    chatTree: res.tree,
                    treePath: res.path
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
            let prefix = prevState.treePath.slice(0, pathItem.prefixLength);
            return {
                inProgress: true,
                completion: "",
                treePath: [...prefix],
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

            let promise = this.postText(generatedText, leaf.id);

            promise.then(message => {
                this.setState(prevState => {
                    let res = getAppendedTree(
                        prevState.chatTree, prevState.treePath, message.text, message.id
                    );

                    return {
                        prompt: "",
                        completion: "",
                        inProgress: false,
                        chatTree: res.tree,
                        contextLoaded: true,
                        treePath: res.path
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

    handleBranchSwitch(pathItem, newBranchId) {
        console.log("handle branch switch", pathItem, newBranchId);

        if (newBranchId < 0 || newBranchId >= pathItem.parent.replies.length) {
            throw Exception(`Out of bounds: ${newBranchId}`);
        }

        let treeCopy = JSON.parse(JSON.stringify(this.state.chatTree));
        let pathCopy = copyTreePath(treeCopy, this.state.treePath);
    
        let path = pathCopy.slice(0, pathItem.prefixLength);

        let lastItem = path[path.length - 1];
        let node = lastItem.node.replies[newBranchId];

        path.push(new PathItem(newBranchId, path.length, node, lastItem.node));

        while (true) {
            if (node.replies.length === 0) {
                break;
            }
            let parent = node;
            node = node.replies[0];
            path.push(new PathItem(0, path.length, node, parent));
        }

        this.setState({
            chatTree: treeCopy,
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