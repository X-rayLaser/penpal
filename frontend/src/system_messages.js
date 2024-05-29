import React from 'react';
import Button from 'react-bootstrap/Button';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { Link } from "react-router-dom";
import { withRouter } from "./utils";
import { GenericFetchJson, csrftoken } from './generic_components';


function SystemMessage(props) {
    return (
        <Card bg="light">
            <Card.Header>{props.message.name}</Card.Header>
            <Card.Body bg="light">
                <Card.Text>{props.message.text}</Card.Text>
            </Card.Body>
        </Card>
    );
}


class SystemMessageList extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            messages: [],
            name: "",
            text: "",
            buttonDisabled: false,
            nameErrors: [],
            textErrors: [],
            otherErrors: []
        };

        this.handleNameChange = this.handleNameChange.bind(this);
        this.handleTextChange = this.handleTextChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
    }

    componentDidMount() {
        let fetcher = new GenericFetchJson();

        fetcher.performFetch('/chats/system_messages/').then(data => {
            console.log(data);
            this.setState({ messages: data});
        });
    }

    handleNameChange(event) {
        this.setState({ name: event.target.value });
    }

    handleTextChange(event) {
        this.setState({ text: event.target.value });
    }

    handleSubmit(event) {
        event.preventDefault();
        this.setState({
            buttonDisabled: true,
            nameErrors: [],
            textErrors: []
        });

        let body = {
            name: this.state.name,
            text: this.state.text
        };

        fetch('/chats/system_messages/', {
            method: 'POST',
            body: JSON.stringify(body),
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken
            }
        }).then(response => {
            if (response.ok) {
                return response.json();
            } else {
                return response.json().then(obj => { console.log(obj); throw obj; });
            }
        }).then(data => {
            this.setState(prevState => ({
                messages: [...prevState.messages, { name: data.name, text: data.text }],
                name: "",
                text: "",
                buttonDisabled: false
            }));
        }).catch(error => {
            let errorsObj = {};
            if (error.name) {
                errorsObj.nameErrors = error.name;
            }

            if (error.text) {
                errorsObj.textErrors = error.text;
            }
            this.setState(errorsObj);
        }).finally(data => {
            this.setState({ buttonDisabled: false });
        });
    }
    render() {
        const messages = this.state.messages.map((message, index) =>
            <div key={index} className="mt-3 mb-3">
                <SystemMessage key={index} message={message} />
            </div>
        );

        const nameErrors = this.state.nameErrors.map((error, index) => 
            <Alert key={index} className="mt-2 mb-2" variant="danger">{error}</Alert>
        );

        const textErrors = this.state.textErrors.map((error, index) => 
            <Alert key={index} className="mt-2 mb-2" variant="danger">{error}</Alert>
        );

        return (
            <div>
                <Card className="mt-3 mb-3" bg="secondary" text="light">
                    <Card.Body>
                        <Card.Title>Create a new system message</Card.Title>
                        <Form onSubmit={this.handleSubmit}>
                            <Form.Group className="mb-3" controlId="formSystemMessageName">
                                <Form.Label>Name</Form.Label>
                                <Form.Control type="text" placeholder="Enter identifier for your message" 
                                              value={this.state.name}
                                              onChange={this.handleNameChange} />
                                <Form.Text className="text-muted">
                                    You will be able to refer to your system message by that name
                                </Form.Text>
                                {nameErrors.length > 0 && 
                                    <div>{nameErrors}</div>
                                }
                                <Form.Control.Feedback>Looks good!</Form.Control.Feedback>
                            </Form.Group>
                            <Form.Group className="mb-3" controlId="formSystemMessageText">
                                <Form.Label>System message</Form.Label>
                                <Form.Control as="textarea" rows={5} 
                                              placeholder="Enter text for your new system message here"
                                              value={this.state.text}
                                              onChange={this.handleTextChange} />
                                {textErrors.length > 0 && 
                                    <div>{textErrors}</div>
                                }
                            </Form.Group>
                            <Button type="submit" variant="light" disabled={this.state.buttonDisabled}>
                                Submit
                            </Button>
                        </Form>
                    </Card.Body>
                </Card>
                <h2>System messages</h2>
                {messages.length > 0 && <div>{messages}</div>}
                {messages.length === 0 && <h4>It appears you have not created any system messages yet</h4>}
            </div>
        );
    }
}

SystemMessageList = withRouter(SystemMessageList);

export {
    SystemMessageList
}
