import { GenericFetchJson } from "./generic_components";


class Node {
    constructor(id, data, parent, replies, branchIndex) {
        this.id = id;
        this.data = data;
        this.parent = parent || null;
        this.replies = replies || [];
        this.branchIndex = branchIndex || null;
    }

    addChild(node) {
        node.parent = this;
        node.branchIndex = this.replies.length;
        this.replies.push(node);
    }
}


class Root extends Node {
    constructor(replies) {
        super(null, null, null, replies, null);
    }
}


class PathItem {
    constructor(nodeId, branchIndex) {
        this.nodeId = nodeId;
        this.branchIndex = branchIndex;
    }
};


export function buildTree(root) {
    let tree = new Root([]);
    if (Object.keys(root).length) {
        let fixedRoot = fixBranch(root);
        tree.addChild(fixedRoot);
    } else {
        tree = new Root([]);
    }

    let path = selectThread(tree);

    return {
        tree,
        path
    };
}

function fixBranch(node) {
    let fixedNode = new Node(node.id, { 
        text: node.text, clean_text: node.clean_text, html: node.html, audio: node.audio,
        image: node.image, image_b64: node.image_b64
    });
    for (let i = 0; i < node.replies.length; i++) {
        let fixedChild = fixBranch(node.replies[i]);
        fixedNode.addChild(fixedChild);
    }

    return fixedNode;
}

export function fetchTree(url) {
    let fetcher = new GenericFetchJson();

    return fetcher.performFetch(url).then(obj => {
        console.log("fetch tree:", obj)
        return buildTree(obj);
    });
}

export function addNode(tree, nodeId, message) {
    //create new node and append it to the list of children of a node with nodeId
    let treeCopy = copyTree(tree);

    let parentNode = getNodeById(treeCopy, nodeId);
    //todo: consider to just pass message itself as data
    let data = {
        text: message.text,
        clean_text: message.clean_text,
        html: message.html,
        audio: message.audio,
        image: message.image,
        image_b64: message.image_b64
    };

    let childNode = new Node(message.id, data);
    parentNode.addChild(childNode);
    return {
        tree: treeCopy,
        node: childNode
    }
}

function addNodeUnderRoot(tree, message) {
    let treeCopy = copyTree(tree);

    let data = {
        text: message.text,
        clean_text: message.clean_text,
        html: message.html,
        audio: message.audio,
        image: message.image,
        image_b64: message.image_b64
    };
    let childNode = new Node(message.id, data);
    treeCopy.addChild(childNode);
    return {
        tree: treeCopy,
        node: childNode
    }
}

export function addMessage(tree, thread, attachToId, message) {
    let res;
    if (attachToId) {
        res = addNode(tree, attachToId, message);
    } else {
        res = addNodeUnderRoot(tree, message);
    }

    let updatedTree = res.tree;
    let newNode = res.node;

    let updatedThread = appendThread(thread, newNode.id, newNode.branchIndex);

    return {
        tree: updatedTree,
        thread: updatedThread
    }
}

export function removeSubtree(tree, nodeId) {
    //delete a whole subtree of conversation rooted at nodeId
}

export function selectThread(tree, nodeId, strategy) {
    strategy = strategy || new SimpleSelectionStrategy();
    let node;
    let path;
    if (nodeId) {
        node = getNodeById(tree, nodeId);
        path = getPathToNode(node);
    } else {
        node = tree;
        path = [];
    }

    while (strategy.shouldContinue(node)) {
        let childIndex = strategy.selectBranch(node);
        node = node.replies[childIndex];
        path.push(new PathItem(node.id, node.branchIndex));
    }

    return path;
}

class SimpleSelectionStrategy {
    shouldContinue(node) {
        return node.replies.length > 0;
    }

    selectBranch(node) {
        return 0;
    }
}

function getPathToNode(node) {
    //returns path from root of the tree to the given node including that node
    let path = [];
    while (node.parent !== null) {
        path.push(new PathItem(node.id, node.branchIndex));
        node = node.parent;
    }
    
    let result = [];
    while (path.length > 0) {
        result.push(path.pop());
    }
    return result;
}

export function getNodeById(tree, nodeId) {
    let foundNode = null;

    function visit(node) {
        if (node.id === nodeId) {
            foundNode = node;
            return;
        }

        for (let child of node.replies) {
            visit(child);
        };
    }

    visit(tree);

    if (foundNode) {
        return foundNode;
    }

    console.log(tree);

    throw "Not found!!!";
}

export function appendThread(thread, nodeId, branchIndex) {
    let threadCopy = copyObject(thread);
    threadCopy.push(new PathItem(nodeId, branchIndex));
    return threadCopy;
}

export function popThread(thread) {
    let threadCopy = copyObject(thread);
    threadCopy.pop();
    return threadCopy;
}

export function collapseThread(thread, nodeId) {
    //remove all items past nodeId
    let threadCopy = copyObject(thread);

    while (threadCopy.length > 0) {
        let lastItem = threadCopy[threadCopy.length - 1];
        if (lastItem.nodeId === nodeId) {
            break;
        }

        threadCopy.pop();
    }

    return threadCopy;
}

export function getThreadMessages(tree, thread) {
    let node = tree;
    let res = [];
    for (let i = 0; i < thread.length; i++) {
        let item = thread[i];
        node = node.replies[item.branchIndex];

        let message = {
            id: node.id,
            data: node.data,
            numSiblings: node.parent.replies.length,
            pathItem: copyObject(item),
            key: i
        };
        res.push(message);
    }

    return res;
}


export function getConversationText(messages, questionTemplate, answerTemplate, systemMessage, systemTemplate) {
    let result = "";

    messages.forEach((msg, index) => {
        let template = isHumanText(index) ? questionTemplate : answerTemplate;
        result += template.render(msg.data.text);
    });

    if (systemMessage) {
        let prefix = systemMessage + "\n\n";
        if (systemTemplate) {
            prefix = systemTemplate.render(systemMessage);
        }
        result = prefix + result;
    }

    return result;
}

export function includeSystemMessage(messages, systemMessage, separator) {
    //prepends text of the first message in messages array with systemMessage
    let res = copyObject(messages);

    separator = separator || "\n\n";

    if (systemMessage && res.length > 0) {
        res[0].data.text = systemMessage + separator + res[0].data.text;
    }

    return res;
}

export function isHumanText(index) {
    return index % 2 === 0;
}

function copyTree(tree) {

    function copyBranch(node) {
        let nodeCopy = new Node(node.id, node.data);
        for (let child of node.replies) {
            let branchCopy = copyBranch(child);
            nodeCopy.addChild(branchCopy);
        }
        return nodeCopy;
    }
    
    return copyBranch(tree);
}

function copyObject(obj) {
    return JSON.parse(JSON.stringify(obj));
}