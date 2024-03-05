import React from 'react';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { Link } from "react-router-dom";
import Pagination from 'react-bootstrap/Pagination';

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


function PaginationWidget(props) {
    let items = [];
    for (let number = 1; number <= props.numPages; number++) {
        items.push(
            <Pagination.Item key={number} active={number === props.activePage} 
                onClick={e => props.onPageClick(number)}>
            {number}
            </Pagination.Item>,
        );
    }

    if (props.numPages < 2) {
        return (<div></div>);
    }

    return (
        <div>
            <Pagination>{items}</Pagination>
        </div>
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
            showDeletedToast: false,
            numPages: 1,
            activePage: 1
        };

        this.handleHideDeletedToast = this.handleHideDeletedToast.bind(this);
        this.handleCreateChat = this.handleCreateChat.bind(this);
        this.handleDeleteChat = this.handleDeleteChat.bind(this);
        this.handleChangeConfiguration = this.handleChangeConfiguration.bind(this);
        this.handlePageClick = this.handlePageClick.bind(this);
    }

    componentDidMount() {
        this.loadPage();

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

    loadPage(pageNo) {
        pageNo = pageNo || 1;
        let url;
        if (pageNo) {
            url = `/chats/chats/?page=${pageNo}`;
        } else {
            url = `/chats/chats/`;
        }

        this.setState({
            loading_chats: true
        });

        fetch(url, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        }).then(response => {
            return response.json();
        }).then(data => {
            let results = data.results;
            this.setState({
                chats: results,
                loading_chats: false,
                activePage: pageNo
            });

            if (pageNo === 1) {
                let pageSize = results.length;
                let numPages = Math.ceil(data.count / pageSize);
                this.setState({ numPages });                
            }
        });
    }

    handlePageClick(pageNo) {
        console.log(`pageno ${pageNo}`)
        this.loadPage(pageNo);
    }

    handleHideDeletedToast() {
        this.setState({ showDeletedToast: false });
    }

    handleCreateChat(e) {
        let self = this;

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

    handleDeleteChat(id) {
        const url = `/chats/chats/${id}/`;
        let fetcher = new GenericFetchJson();
        fetcher.method = 'delete';
        fetcher.okRespondWithJson = false;

        this.setState({ deletionId: id });
        fetcher.performFetch(url).then(response => {
            let chats = this.state.chats.filter(chat => chat.id !== id);
            this.setState({ chats, showDeletedToast: true });
        }).catch(reason => {
            console.error(`Deletion failure: ${reason}`);
        }).finally(() => {
            this.setState({ deletionId: null });
        });
    }

    handleChangeConfiguration(e) {
        let name = e.target.value;

        this.setState({
            selected_name: name
        });
    }

    render() {
        const chatItems = this.state.chats.map((chat, index) =>
            <ChatItem key={index} text={chat.prompt_text} itemId={chat.id} 
                      onDelete={this.handleDeleteChat} deletion={chat.id === this.state.deletionId} />
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
                                                 onChange={this.handleChangeConfiguration}>
                                        {configs}
                                    </Form.Select>
                                </Col>
                                <Col>
                                    <Button variant="light" onClick={this.handleCreateChat} 
                                            disabled={this.state.buttonDisabled || this.state.loading_configs}>
                                        Create
                                    </Button>
                                </Col>
                            </Row>
                        </Form>
                    </Card.Body>
                </Card>
                {
                    this.state.loading_chats && (
                        <Spinner animation="border" role="status">
                            <span className="visually-hidden">Loading...</span>
                        </Spinner>
                    )
                }
                {
                    !this.state.loading_chats && chatItems.length > 0 && (
                        <div>
                            <h4>My chats</h4>
                            <PaginationWidget 
                                numPages={this.state.numPages}
                                activePage={this.state.activePage}
                                onPageClick={this.handlePageClick} />
                                
                            <div>{chatItems}</div>
                            <PaginationWidget 
                                numPages={this.state.numPages}
                                activePage={this.state.activePage}
                                onPageClick={this.handlePageClick} />
                        </div>
                    )
                }
            </div>
        );
    }
}


ChatsList = withRouter(ChatsList);

export {
    ChatsList
}
