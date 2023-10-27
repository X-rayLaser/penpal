import React from 'react';
import ReactDOM from 'react-dom';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Container from 'react-bootstrap/Container';

import { createRoot } from 'react-dom/client';


class TextCompletionWidget extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            prompt: "",
            completion: ""
        };

        this.handleGenerate = this.handleGenerate.bind(this);
        this.handleInput = this.handleInput.bind(this);
    }

    handleGenerate(e) {
        e.preventDefault();

        self = this;

        fetch('/chats/completion', {
            method: 'POST',
            body: "",
            headers: {
                "Content-Type": "application/json"
            }
        }).then(response => {
            let reader = response.body.getReader();
            reader.read().then(function pump({ done, value }) {
                if (done) {
                    return;
                }

                let s = new TextDecoder().decode(value);

                let response = JSON.parse(s);
                self.setState((prevState, props) => ({
                    completion: prevState.completion + response.data
                }));
                console.log(done, s);
                return reader.read().then(pump);
            });
        });
    }

    handleInput(event) {
        this.setState({ prompt: event.target.value, completion: "" });
    }
    render() {
        return (
            <Form onSubmit={this.handleGenerate}>
                <Form.Group className="mb-3" controlId="exampleForm.ControlTextarea1">
                    <Form.Label>Example textarea</Form.Label>
                    <Form.Control as="textarea" rows={10} placeholder="Enter a prompt here"
                        onInput={this.handleInput}
                        value={this.state.prompt + this.state.completion} />
                </Form.Group>
                <Button variant="primary" type="submit">
                    Generate completion
                </Button>
            </Form>
        );
    }
}


class App extends React.Component {
    render() {
        return (
            <Container>
                <TextCompletionWidget />
            </Container>
        )
    }
}

// Render your React component instead
const root = createRoot(document.getElementById('react_app'));
root.render(<App />);