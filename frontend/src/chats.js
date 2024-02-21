import React from 'react';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { Link } from "react-router-dom";
import { GenericFetchJson } from "./generic_components";
import { StickyToastContainer, AutoclosableToast } from './generic_components';
import { withRouter } from "./utils";


function ChatItem(props) {
    return (
        <Card className="mb-3">
            <Card.Body>
                <Card.Text>{props.text}</Card.Text>
                <Button variant="primary" href={`/#chats/${props.itemId}/`} 
                        className="me-2" disabled={props.deletion}>
                    View chat
                </Button>
                <Button variant="danger" onClick={e => props.onDelete(props.itemId)} 
                        disabled={props.deletion}>
                    Delete
                </Button>
                {props.deletion && <div className="mt-2">Deleting an item</div>}
            </Card.Body>
        </Card>
    );
}


class ChatsList extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            buttonDisabled: false,
            chats: [],
            loading_chats: true,
            loading_configs: true,
            deletionId: null,
            configs: [],
            selected_name: "",
            name_to_config: {},
            showDeletedToast: false
        };

        this.handleHideDeletedToast = this.handleHideDeletedToast.bind(this);
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

        fetch('/chats/configurations/', {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        }).then(response => {
            return response.json();
        }).then(data => {
            let name_to_config = {};
            data.forEach(conf => {
                name_to_config[conf.name] = conf;
            });

            this.setState({
                configs: data,
                selected_name: data[0].name,
                name_to_config,
                loading_configs: false
            })
        });
    }

    handleHideDeletedToast() {
        this.setState({ showDeletedToast: false });
    }

    render() {
        let self = this;
        function clickHandler(e) {
            self.setState({
                buttonDisabled: true
            });

            let body = {};

            if (self.state.selected_name) {
                let config = self.state.name_to_config[self.state.selected_name];
                if (!config) {
                    console.error(`Configuration lookup failed on key ${self.state.selected_name}`);
                } else {
                    body.configuration = config.id;
                }
            }

            fetch('/chats/chats/', {
                method: 'POST',
                body: JSON.stringify(body),
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            }).then(response => {
                return response.json();
            }).then(data => {
                console.log(data);
                self.props.router.navigate(`/chats/${data.id}/`);
            });
        }

        function changeConfigurationHandler(e) {
            let name = e.target.value;

            self.setState({
                selected_name: name
            });
        }


        function handleDelete(id) {
            const url = `/chats/chats/${id}/`;
            let fetcher = new GenericFetchJson();
            fetcher.method = 'delete';
            fetcher.okRespondWithJson = false;

            self.setState({ deletionId: id });
            fetcher.performFetch(url).then(response => {
                let chats = self.state.chats.filter(chat => chat.id !== id);
                self.setState({ chats, showDeletedToast: true });
            }).catch(reason => {
                console.error(`Deletion failure: ${reason}`);
            }).finally(() => {
                self.setState({ deletionId: null });
            });
        }

        const chatItems = this.state.chats.map((chat, index) =>
            <ChatItem key={index} text={chat.prompt_text} itemId={chat.id} 
                      onDelete={handleDelete} deletion={chat.id === this.state.deletionId} />
        );

        let configs;

        if (this.state.configs.length > 0) {
            configs = this.state.configs.map((conf, index) =>
                <option key={index} value={conf.name}>{conf.name}</option>
            );
        } else {
            configs = [];
        }

        return (
            <div>
                <StickyToastContainer>
                    <AutoclosableToast show={this.state.showDeletedToast}
                                            text="Item has been deleted"
                                            onClose={this.handleHideDeletedToast} />
                </StickyToastContainer>
                <Card className="mt-2 mb-2" bg="secondary" text="light">
                    <Card.Body>
                        <Card.Title>Create a new chat</Card.Title>
                        <Form>
                            <Row>
                                <Col xs={10}>
                                    <Form.Select aria-label="Configuration selection" value={this.state.selected_name}
                                                 onChange={changeConfigurationHandler}>
                                        {configs}
                                    </Form.Select>
                                </Col>
                                <Col>
                                    <Button variant="light" onClick={clickHandler} 
                                            disabled={this.state.buttonDisabled || this.state.loading_configs}>
                                        Create
                                    </Button>
                                </Col>
                            </Row>
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
