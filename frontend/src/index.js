import React from 'react';
import ReactDOM from 'react-dom';

import Container from 'react-bootstrap/Container';
import { createRoot } from 'react-dom/client';
import {
    createHashRouter,
    RouterProvider,
} from "react-router-dom";
import { Outlet, Link } from "react-router-dom";
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import Spinner from 'react-bootstrap/Spinner';
import Button from 'react-bootstrap/Button';

import { ChatsList } from "./chats";
import { ActiveChat } from './active_chat';
import { ErrorPage } from './errors';
import { TextCompletionPage } from './text_completion';
import { SystemMessageList } from './system_messages';
import { PresetsPage } from './presets';
import { ConfigurationsPage } from './configurations';
import { ModelControlPanel } from './llm_models';
import { GenericFetchJson } from './generic_components';

class App extends React.Component {
    constructor() {
        super();
        this.state = {
            user: null,
            loading: true
        };
    }

    fetchUserName() {
        let fetcher = new GenericFetchJson();
        
        return fetcher.performFetch('/whoami/').then(data => {
            this.setState({ user: data.user, loading: false });
        });
    }
    componentDidMount() {
        this.fetchUserName();
    }
    render() {
        const handleLogout = (e) => {
            this.setState({ loading: true });
            let fetcher = new GenericFetchJson();
            fetcher.method = "POST";
            fetcher.withCsrfToken = true;
            fetcher.performFetch("/accounts/logout/").then(data => {
                return this.fetchUserName();
            }).catch(reason => {
                console.error(reason);
            }).finally(() => {
                this.setState({ loading: false });
            });
        };

        return (
            <div>
                <Navbar bg="dark" data-bs-theme="dark">
                    <Container>
                        <Navbar.Brand href="#home">Penpal</Navbar.Brand>
                        <Navbar.Toggle aria-controls="basic-navbar-nav" />
                        <Navbar.Collapse id="basic-navbar-nav">
                            <Nav className="me-auto">
                                <Nav.Link href="#my-chats">My chats</Nav.Link>
                                <Nav.Link href="#configurations">Configurations</Nav.Link>

                                <Nav.Link href="#my-system-messages">System messages</Nav.Link>
                                <Nav.Link href="#presets">Presets</Nav.Link>
                                <Nav.Link href="#models">Models</Nav.Link>
                            </Nav>
                        </Navbar.Collapse>
                        <Navbar.Collapse className="justify-content-end">
                            {this.state.loading && (
                                <Spinner animation="border" role="status" variant="light">
                                    <span className="visually-hidden">Loading...</span>
                                </Spinner>
                            )}
                            {!this.state.loading && (
                                <div>
                                    {this.state.user && (
                                        <div>
                                            <Navbar.Text>
                                                <span className="me-3">Hello, {this.state.user}!</span>
                                                <Button variant="link" onClick={handleLogout} style={{ verticalAlign: 'baseline' }}>
                                                    Log out
                                                </Button>
                                            </Navbar.Text>
                                        </div>
                                    )}
                                    {!this.state.user && (
                                        <div>
                                            <Navbar.Text className="me-3">
                                                <a href="/accounts/login/">Log in</a>
                                            </Navbar.Text>
                                            <Navbar.Text>
                                                <a href="/accounts/signup/">Sign up</a>
                                            </Navbar.Text>
                                        </div>
                                    )}
                                </div>
                            )}
                        </Navbar.Collapse>
                    </Container>
                </Navbar>
                <Container>
                    <div id="detail">
                        <Outlet />
                    </div>
                </Container>
            </div>
        )
    }
}


const socket = new WebSocket("ws://localhost:9000");

function getRandomInt(max) {
    return Math.floor(Math.random() * max);
}

let n = getRandomInt(Math.pow(2, 31));
let socketSessionId = `${n}`;


socket.addEventListener("open", (event) => {
    socket.send(socketSessionId);
});


const router = createHashRouter([
    {
        path: "/",
        element: <App />,
        errorElement: <ErrorPage />,
        children: [
            {
                path: "/completion/",
                element: <TextCompletionPage />
            },
            {
                path: "/my-chats/",
                element: <ChatsList />
            },
            {
                path: "/chats/:id/",
                element: <ActiveChat websocket={socket} socketSessionId={socketSessionId} />
            },
            {
                path: "/configurations/",
                element: <ConfigurationsPage />
            },
            {
                path: "/presets/",
                element: <PresetsPage />
            },
            {
                path: "/my-system-messages/",
                element: <SystemMessageList />
            },
            {
                path: "/models",
                element: <ModelControlPanel />
            }
        ]
    }
]);


// Render your React component instead
const root = createRoot(document.getElementById('react_app'));
root.render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);