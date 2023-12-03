import React from 'react';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { Link } from "react-router-dom";
import { withRouter } from "./utils";


class ChatsList extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            buttonDisabled: false,
            chats: [],
            loading_chats: true
        };
    }

    componentDidMount() {
        fetch('/chats/chats/', {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        }).then(response => {
            return response.json();
        }).then(data => {
            this.setState({
                chats: data,
                loading_chats: false
            })
        });
    }

    render() {
        let self = this;
        function clickHandler(e) {
            self.setState({
                buttonDisabled: true
            });

            fetch('/chats/chats/', {
                method: 'POST',
                body: JSON.stringify({}),
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

        const chatItems = this.state.chats.map((chat, index) =>
            <li key={index}><Link to={`/chats/${chat.id}/`}>{chat.prompt_text}</Link></li>
        );
        return (
            <div>
                <Button variant="primary" onClick={clickHandler} disabled={this.state.buttonDisabled}>
                    Start a new chat
                </Button>
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
