import React from 'react';
import Accordion from 'react-bootstrap/Accordion';


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

export {
    CollapsibleSystemMessage
}