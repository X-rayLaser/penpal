import React from 'react';
import { useState } from 'react';
import { Outlet, Link } from "react-router-dom";
import Card from 'react-bootstrap/Card';
import Accordion from 'react-bootstrap/Accordion';
import Badge from 'react-bootstrap/Badge';
import Spinner from 'react-bootstrap/Spinner';
import Collapse from 'react-bootstrap/Collapse';
import Button from 'react-bootstrap/Button';
import Tab from 'react-bootstrap/Tab';
import Tabs from 'react-bootstrap/Tabs';

let myBuilds = [
    {
        url: "http://localhost:45344",
        status: "success",
        stdout: "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. ",
        stderr: "warning: Reassignment to the variable",
        files: [{
            name: 'index.html', content: "<html>\n<body>\nhello</body></html"
        }, {
            name: 'index.js', content: "var x = 43;\nvar y = 25"
        }]
    },
    {
        status: "error",
        stdout: "Build was unsuccessful",
        stderr: "warning: Reassignment to the variable",
        files: [{
            name: 'index.html', content: "<html>\n<body>\nhello</body></html"
        }, {
            name: 'index.js', content: "var x = 43;\nvar y = 25"
        }]
    },
    {
        status: "pending",
        stdout: "In progress",
        stderr: "warning: Reassignment to the variable",
        files: [{
            name: 'index.html', content: "<html>\n<body>\nhello</body></html"
        }, {
            name: 'index.js', content: "var x = 43;\nvar y = 25"
        }]
    }
]

export function WebpackBuildsContainer({ builds }) {
    console.log("builds", builds)
    return (
        <Card bg="info" text="light">
            <Card.Header>Builds</Card.Header>
            <Card.Body>
                <WebpackBuilds builds={builds} />
            </Card.Body>
        </Card>
    )
}

export function WebpackBuilds({ builds }) {
    return (
        <Accordion style={{ maxWidth: '45em' }}>
            {builds.map((buildObj, idx) =>
                <AccordionBuild buildObj={buildObj} id={idx} key={idx} />
            )}
        </Accordion>
    )
}


function AccordionBuild({ buildObj, id }) {
    return (
        <Accordion.Item eventKey={`${id}`}>
            <Accordion.Header>
                <AccordionHeader name="Webpack" status={buildObj.status} />
            </Accordion.Header>
            <Accordion.Body>
                <BuildBody {...buildObj} />
            </Accordion.Body>
        </Accordion.Item>
    );
}


export function ToolCallSection({ toolCalls }) {
    return (
        <Accordion style={{ maxWidth: '45em' }}>
            {toolCalls.map((toolObject, idx) =>
                <ToolCall toolObject={toolObject} id={idx} key={idx} />
            )}
        </Accordion>
    );
}

function ToolCall({ toolObject, id }) {
    let status;
    if (toolObject.result) {
        status = 'success';
    } else if (toolObject.error) {
        status = 'error';
    } else {
        status = 'pending';
    }

    let name = toolObject.name;
    let argsArray = [];

    for (const [key, value] of Object.entries(toolObject.arguments)) {
        argsArray.push({
            name: key,
            value: value
        });
    }

    return (
        <Accordion.Item eventKey={`${id}`}>
            <Accordion.Header>
                <AccordionHeader name={name} status={status} />
            </Accordion.Header>
            <Accordion.Body>
                <div className="mb-3">Arguments:</div>
                <ul>
                    {argsArray.map(({ name, value }, idx) => <li key={idx}>{name}: {value}</li>)}
                </ul>

                {toolObject.result && (
                    <div>
                        <span>Result: </span>
                        <span>{toolObject.result}</span>
                    </div>
                )}

                {toolObject.error && (
                    <div>
                        <span>Error: </span>
                        <span>{toolObject.error}</span>
                    </div>
                )}
            </Accordion.Body>
        </Accordion.Item>
    );
}


function AccordionHeader({ name, status }) {
    let statusElement;
    let textColor;
    if (status === 'success') {
        statusElement = <Badge size="sm" pill bg="success">{status}</Badge>
        textColor = 'text-success'
    } else if (status === 'error') {
        statusElement = <Badge size="sm" pill bg="danger">{status}</Badge>
        textColor = 'text-danger'
    } else {
        statusElement = (
            <span>
                <Badge size="sm" pill bg="info" className="me-2">In progress </Badge>

                <Spinner animation="grow" size="sm" />
            </span>
        );
        textColor = 'text-info'
    }
    return (
        <div className={textColor}>
            <span className="me-2">{name}</span>
            <span>{statusElement}</span>
        </div>
    );
}


function BuildBody({ status, stdout, stderr, files, url="" }) {
    let tree = files.map(({ name }) => name);

    let stdoutHtml = {
        __html: stdout || ""
    }

    let stderrHtml = {
        __html: stderr || ""
    }
    let prerenderedStdout = <pre dangerouslySetInnerHTML={stdoutHtml} style={{whiteSpace: 'break-spaces'}} />;
    let prerenderedStderr = <pre dangerouslySetInnerHTML={stderrHtml} style={{whiteSpace: 'break-spaces'}} />;

    return (
        <div>
            <Tabs
                defaultActiveKey="stdout"
                id="build-tabs"
                className="mb-3"
                >

                {url && (
                    <Tab eventKey="link" title="App URL">
                        <div className="mb-3">
                            <Link to={url}>{url}</Link>
                        </div>
                    </Tab>
                )}

                {stdout && (
                    <Tab eventKey="stdout" title="STDOUT">
                        <div className="mb-3">
                            <div>{prerenderedStdout}</div>
                        </div>
                    </Tab>
                )}
                
                {stderr && (
                    <Tab eventKey="stderr" title="STDERR">
                        <div className="mb-3">
                            <div>{prerenderedStderr}</div>
                        </div>
                    </Tab>
                )}

                {files.length > 0 && (
                    <Tab eventKey="files"  title="files">
                        <div>Source Tree:</div>
                        <SourceTree fileTree={tree} />
                        <Accordion>
                            {files.map(({ name, content }, idx) =>
                                <Accordion.Item key={idx} eventKey={`${idx}`}>
                                    <Accordion.Header>{name}</Accordion.Header>
                                    <Accordion.Body>
                                        <pre dangerouslySetInnerHTML={{__html: content}} style={{whiteSpace: 'break-spaces'}} />
                                    </Accordion.Body>
                                </Accordion.Item>
                            )}

                        </Accordion>
                    </Tab>
                )}
            </Tabs>
        </div>
    );
}


function SourceTree({ fileTree }) {
    if (isString(fileTree)) {
        return <li>{fileTree}</li>
    }

    return (
        <ul>{fileTree.map((obj, idx) => <SourceTree key={idx} fileTree={obj} />)}</ul>
    );
}


function isString(obj) {
    return (typeof obj === 'string' || obj instanceof String) ? true : false
}