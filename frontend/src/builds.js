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


export function WebpackBuildsContainer({ builds }) {

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
    let status = mapToStatus(buildObj);
    return (
        <Accordion.Item eventKey={`${id}`}>
            <Accordion.Header>
                <AccordionHeader name="Webpack" status={status} />
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
    let status = mapToStatus(toolObject);
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


function mapToStatus(obj) {
    let status;
    if (obj.success || obj.result || obj.return_code === 0) {
        status = 'success';
    } else if (obj.error) {
        status = 'error';
    } else {
        status = 'pending';
    }
    return status;
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


function BuildBody({ status, stdout, stderr, src_tree, url="", error="" }) {
    let files = src_tree;
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

                {error.length === 0 && url && (
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

                {error && (
                    <Tab eventKey="error" title="Errors">
                        <div className="mb-3">
                            <div>{error}</div>
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