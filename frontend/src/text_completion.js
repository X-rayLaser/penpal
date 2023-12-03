import React from 'react';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { streamJsonResponse } from './utils';


class TextCompletionWidget extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            prompt: "",
            completion: "",
            inProgress: false
        };

        this.handleGenerate = this.handleGenerate.bind(this);
        this.handleInput = this.handleInput.bind(this);
    }

    handleGenerate(e) {
        e.preventDefault();

        self = this;

        this.setState({ inProgress: true });

        const handleChunk = chunk => {
            self.setState((prevState, props) => ({
                completion: prevState.completion + chunk.data
            }));
        };

        const handleDone = () => {
            self.setState({ inProgress: false });
        }

        let body = {
            prompt: this.state.prompt
        }
        streamJsonResponse('/chats/completion/', 'POST', body, handleChunk, handleDone);
    }

    handleInput(event) {
        this.setState({ prompt: event.target.value, completion: "" });
    }
    render() {
        let textarea;
        let button;

        if (this.state.inProgress) {
            textarea = (<Form.Control as="textarea" rows={10} placeholder="Enter a prompt here"
                onInput={this.handleInput}
                value={this.state.prompt + this.state.completion}
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
                value={this.state.prompt + this.state.completion} />);
            
            button = <Button variant="primary" type="submit">Generate completion</Button>;
        }
        return (
            <Form onSubmit={this.handleGenerate}>
                <Form.Group className="mb-3" controlId="exampleForm.ControlTextarea1">
                    <Form.Label>Use LLM to complete your prompt</Form.Label>
                    {textarea}
                </Form.Group>
                {button}
            </Form>
        );
    }
}


class TextCompletionPage extends React.Component {
    render() {
        return (
                <TextCompletionWidget />
        );
    }
}

export {
    TextCompletionPage
}