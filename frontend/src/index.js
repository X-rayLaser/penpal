import React from 'react';
import ReactDOM from 'react-dom';

import Container from 'react-bootstrap/Container';
import { createRoot } from 'react-dom/client';
import {
    createHashRouter,
    RouterProvider,
} from "react-router-dom";
import { Outlet, Link } from "react-router-dom";
import { ChatsList } from "./chats";
import { ActiveChat } from './active_chat';
import { ErrorPage } from './errors';
import { TextCompletionPage } from './text_completion';
import { SystemMessageList } from './system_messages';


class App extends React.Component {
    render() {
        return (
            <Container>
                <div>
                    <Link to={"my-chats"}>My chats</Link>
                    <Link to={"my-system-messages"}>My system messages</Link>
                    <Link to={"completion"}>Text completion</Link>
                </div>
                <div id="detail">
                    <Outlet />
                </div>
            </Container>
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
                path: "/my-system-messages/",
                element: <SystemMessageList />
            },
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