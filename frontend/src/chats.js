import React from 'react';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { Link } from "react-router-dom";
import { withRouter } from "./utils";


class ChatsList extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            buttonDisabled: false,
            chats: [],
            loading_chats: true,
            loading_system_messages: true,
            system_messages: [],
            selected_name: "",
            name_to_message: {}
        };
    }

    componentDidMount() {
        fetch('/chats/chats/', {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        }).then(response => {
            return response.json();
        }).then(data => {
            this.setState({
                chats: data,
                loading_chats: false
            })
        });

        fetch('/chats/system_messages/', {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        }).then(response => {
            return response.json();
        }).then(data => {
            let name_to_message = {};
            data.forEach(msg => {
                name_to_message[msg.name] = msg;
            });

            this.setState({
                system_messages: data,
                selected_name: data[0].name,
                name_to_message,
                loading_system_messages: false
            })
        });
    }

    render() {
        let self = this;
        function clickHandler(e) {
            self.setState({
                buttonDisabled: true
            });

            let body = {};

            if (self.state.selected_name) {
                let systemMessage = self.state.name_to_message[self.state.selected_name];
                if (!systemMessage) {
                    console.error(`Message lookup failed on key ${self.state.selected_name}`);
                } else {
                    body.system_message = systemMessage.id;
                }
            }

            fetch('/chats/chats/', {
                method: 'POST',
                body: JSON.stringify(body),
                headers: {
                    "Content-Type": "application/json"
                }
            }).then(response => {
                return response.json();
            }).then(data => {
                console.log(data);
                self.props.router.navigate(`/chats/${data.id}/`);
            });
        }

        function changeMessageHandler(e) {
            let name = e.target.value;

            self.setState({
                selected_name: name
            });
        }

        const chatItems = this.state.chats.map((chat, index) =>
            <li key={index}><Link to={`/chats/${chat.id}/`}>{chat.prompt_text}</Link></li>
        );

        let messages;

        if (this.state.system_messages.length > 0) {
            messages = this.state.system_messages.map((message, index) =>
                <option key={index} value={message.name}>{message.name}</option>
            );
        } else {
            messages = [];
        }

        let systemMessage = this.state.name_to_message[this.state.selected_name];

        return (
            <div>
                <Card className="mt-2 mb-2" bg="secondary" text="light">
                    <Card.Body>
                        <Card.Title>Create a new chat</Card.Title>
                        <Form>
                            <Row>
                                <Col xs={10}>
                                    <Form.Select aria-label="System message selection" value={this.state.selected_name}
                                                 onChange={changeMessageHandler}>
                                        {messages}
                                    </Form.Select>
                                </Col>
                                <Col>
                                    <Button variant="light" onClick={clickHandler} 
                                            disabled={this.state.buttonDisabled || this.state.loading_system_messages}>
                                        Create
                                    </Button>
                                </Col>
                            </Row>
                            {systemMessage &&
                            <Card bg="light" text="dark" className="mt-2 mb-2">
                                <Card.Body>
                                    <Card.Title>System message</Card.Title>
                                    <Card.Text>{systemMessage.text}</Card.Text>
                                </Card.Body>
                            </Card>
                            }
                        </Form>
                    </Card.Body>
                </Card>
                <h4>My chats</h4>
                {
                    this.state.loading_chats && (<Spinner animation="border" role="status">
                        <span className="visually-hidden">Loading...</span>
                    </Spinner>)
                }
                {!this.state.loading_chats && <ul>{chatItems}</ul>}
            </div>
        );
    }
}


ChatsList = withRouter(ChatsList);

export {
    ChatsList
}
