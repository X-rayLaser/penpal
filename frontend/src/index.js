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

import { ChatsList } from "./chats";
import { ActiveChat } from './active_chat';
import { ErrorPage } from './errors';
import { TextCompletionPage } from './text_completion';
import { SystemMessageList } from './system_messages';
import { PresetsPage } from './presets';
import { ConfigurationsPage } from './configurations';
import { ModelControlPanel } from './llm_models';


class App extends React.Component {
    render() {
        return (
            <div>
                <Navbar bg="dark" data-bs-theme="dark">
                    <Container>
                    <Navbar.Brand href="#home">Penpal</Navbar.Brand>
                    <Nav className="me-auto">
                        <Nav.Link href="#my-chats">My chats</Nav.Link>
                        <Nav.Link href="#configurations">Configurations</Nav.Link>

                        <Nav.Link href="#my-system-messages">System messages</Nav.Link>
                        <Nav.Link href="#presets">Presets</Nav.Link>
                        <Nav.Link href="#models">Models</Nav.Link>
                    </Nav>
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
                element: <ActiveChat />
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