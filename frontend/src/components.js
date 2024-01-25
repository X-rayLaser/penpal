import React from 'react';
import Accordion from 'react-bootstrap/Accordion';
import Form from 'react-bootstrap/Form';


function CollapsibleSystemMessage(props) {
    let sysMessage = (props.systemMessage && props.systemMessage.text) || "";
    return (
        <div>
            <Accordion>
                <Accordion.Item eventKey="0">
                    <Accordion.Header>System Message</Accordion.Header>
                    <Accordion.Body>{sysMessage}</Accordion.Body>
                </Accordion.Item>
            </Accordion>
        </div>
    );
}


function CollapsibleEditableSystemMessage(props) {
    let sysMessage = (props.systemMessage && props.systemMessage.text) || "";
    return (
        <div>
            <Accordion>
                <Accordion.Item eventKey="0">
                    <Accordion.Header>System Message</Accordion.Header>
                    <Accordion.Body>
                        <Form.Control as="textarea" rows={10} 
                            placeholder="Enter a system message (it will override the one defined in configuration)"
                            onChange={props.onChange}
                            value={sysMessage}
                            disabled={props.inProgress} />
                    </Accordion.Body>
                </Accordion.Item>
            </Accordion>
        </div>
    );
}

export {
    CollapsibleSystemMessage,
    CollapsibleEditableSystemMessage
}