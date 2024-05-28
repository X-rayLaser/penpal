import React from 'react';
import Button from 'react-bootstrap/Button';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Accordion from 'react-bootstrap/Accordion';
import Toast from 'react-bootstrap/Toast';
import ToastContainer from 'react-bootstrap/ToastContainer';
import { withRouter } from "./utils";


function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');


class ItemListWithForm extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            items: [],
            fetchingItems: true,
            itemsFetchError: "",

            submissionInProgress: false,
            deletionInProgress: false,

            errors: [],
            submissionError: "",
            deletionError: "",

            showCreatedToast: false,
            showDeletedToast: false
        };

        this.listUrl = '';
        this.itemsHeader = "Items";
        this.formHeader = "Create new item";
        this.itemCreatedText = "You've successfully added a new item";
        this.itemDeletedText = "You've successfully deleted an item";

        this.invalidFieldsText = "Some fields are not filled correctly";
        
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleDeleteItem = this.handleDeleteItem.bind(this);
        this.handleHideCreatedToast = this.handleHideCreatedToast.bind(this);
        this.handleHideDeletedToast = this.handleHideDeletedToast.bind(this);
    }

    componentDidMount() {
        let fetcher = new GenericFetchJson();
        fetcher.messages["404"] = "Failed to fetch items: resource not found (404)";
        fetcher.messages["5xx"] = "Failed to fetch items because of server error";
        fetcher.invalidFieldsError = this.invalidFieldsText;
        fetcher.unknownError = "Failed to fetch items because of unknown error";

        fetcher.performFetch(this.listUrl).then(data => {
            let items = data.map((it, index) => {
                let item = this.createItem(it);
                item.index = index;
                return item;
            });

            this.setState({ items });
        }).catch(errorObject => {
            this.setState({ itemsFetchError: errorObject.error });
        }).finally(() => {
            this.setState({ fetchingItems: false });
        });
    }

    createItem(item) {
        throw "Not implmented";
    }

    renderItem(item, index, handleDeleteItem) {
        return (
            <div key={index}>List item</div>
        );
    }

    containerizeItems(items) {
        return (
            <Accordion>{items}</Accordion>
        );
    }

    renderForm(handleSubmit) {
        throw "Not implmented";
    }

    handleSubmit(fieldsObject) {
        this.setState({ submissionInProgress: true });

        let fetcher = new GenericFetchJson();
        fetcher.messages["404"] = "Submission failed because resource not found (404)";
        fetcher.messages["5xx"] = "Submission failed because of server error";
        fetcher.invalidFieldsError = this.invalidFieldsText;
        fetcher.unknownError = "Submission failed due to an unknown error";

        fetcher.method = "POST";
        fetcher.body = fieldsObject;

        return fetcher.performFetch(this.listUrl).then(data => {
            this.setState(prevState => {
                let newItem = this.createItem(data);
                newItem.index = `${prevState.items.length}`;

                return {
                    items: [...prevState.items, newItem],
                    errors: [],
                    submissionError: "",
                    showCreatedToast: true
                }
            });
        }).catch(reason => {
            console.error(reason);

            let updatedFields = { submissionError: reason.error };

            if (reason.hasOwnProperty("fieldErrors")) {
                updatedFields.errors = reason.fieldErrors;
            }

            this.setState(updatedFields);
        }).finally(() => {
            this.setState({ submissionInProgress: false });
        });
    }

    handleDeleteItem(item) {
        let detailUrl = `${this.listUrl}${item.id}/`;

        this.setState({ deletionInProgress: true });

        let fetcher = new GenericFetchJson();
        fetcher.messages["404"] = "Failed to delete item: resource not found (404)";
        fetcher.messages["5xx"] = "Failed to delete item: server error";
        fetcher.invalidFieldsError = this.invalidFieldsText;
        fetcher.unknownError = "Failed to delete item: unknown error";
        fetcher.method = "DELETE";
        fetcher.okRespondWithJson = false;

        fetcher.performFetch(detailUrl).then(data => {
            this.setState(prevState => {
                let newItems = prevState.items.filter(it => it.id !== item.id);
                return {
                    items: newItems,
                    showDeletedToast: true,
                    deletionError: ""
                };
            });
        }).catch(reason => {
            this.setState({ deletionError: reason.error });
        }).finally(() => {
            this.setState({  deletionInProgress: false });
        });
    }

    handleHideCreatedToast() {
        this.setState({ showCreatedToast: false });
    }

    handleHideDeletedToast() {
        this.setState({ showDeletedToast: false });
    }

    render() {
        let listItems = this.state.items.map((item, index) => this.renderItem(item, index, this.handleDeleteItem));
        let itemsInContainer = this.containerizeItems(listItems);
        let form = this.renderForm(this.handleSubmit);

        return (
            <div>
                <StickyToastContainer>
                    <AutoclosableToast show={this.state.showCreatedToast}
                                            text={this.itemCreatedText}
                                            onClose={this.handleHideCreatedToast} />

                    <AutoclosableToast show={this.state.showDeletedToast}
                                            text={this.itemDeletedText}
                                            onClose={this.handleHideDeletedToast} />
                </StickyToastContainer>

                <Card className="mt-2">
                    <Card.Body>
                        <Card.Title>{this.formHeader}</Card.Title>
                        {this.state.submissionError && 
                            <Alert className="mt-3 mb-3" variant="danger">{this.state.submissionError}</Alert>
                        }
                        {form}
                    </Card.Body>
                </Card>
                <h2 className="mt-2 mb-2">{this.itemsHeader}</h2>
                {this.state.deletionError && <Alert variant="danger">{this.state.deletionError}</Alert>}
                {this.state.fetchingItems && <Spinner />}
                {this.state.itemsFetchError && <Alert variant="danger">{this.state.itemsFetchError}</Alert>}
                {!this.state.fetchingItems && <div>{itemsInContainer}</div>}
            </div>
        );
    }
}


class GenericFetchJson {
    constructor() {
        this.method = 'GET';
        this.body = {};
        this.okRespondWithJson = true;
        this.withCsrfToken = false;

        this.messages = {
            "404": "Fetch failed: resource not found (404)",
            "5xx": "Fetch failed: server error"
        };

        this.invalidFieldsError = "Some fields are not filled correctly";
        this.unknownError = "Fetch failed due to an unknown error";
        this.unhandledStatusError = this.unknownError;
    }

    performFetch(url) {
        let requestParams = {
            method: this.method,
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        };

        if (this.method === 'POST') {
            let binary = this.body.constructor.name === 'Blob' ? true : false;
            if (binary) {
                requestParams.headers["Content-Type"] = "application/octet-stream";
                requestParams.body = this.body;
            } else {
                requestParams.body = JSON.stringify(this.body);
            }
        }

        if (this.method !== 'GET' && this.withCsrfToken) {
            requestParams.headers['X-CSRFToken'] = csrftoken;
        }

        let promise = fetch(url, requestParams).then(response => {
            if (response.ok) {
                if (this.okRespondWithJson) {
                    return response.json();
                } else {
                    return {};
                }
            } else if (response.status === 404) {
                throw { message: this.messages["404"] };
            } else if (response.status >= 500) {
                throw { message: this.messages["5xx"] };
            } else if (response.status >= 400) {
                return response.json().then(errorsObject => {
                    throw { errorsObject };
                });
            } else {
                throw { message: this.unhandledStatusError };
            }
        }).catch(reason => {
            let errorObject;
            if (reason.hasOwnProperty("errorsObject")) {
                errorObject = {
                    fieldErrors: reason.errorsObject,
                    error: this.invalidFieldsError
                };
            } else if (reason.hasOwnProperty("message")) {
                errorObject = { error: reason.message };
            } else {
                errorObject = { error: this.unknownError };
            }

            throw errorObject;
        });

        return promise;
    }
};

function AutoclosableToast(props) {
    return (
        <Toast className="mt-2" bg="success" show={props.show} 
            delay={3000} autohide onClose={props.onClose}
            style={{ fontSize: "1.25em" }}>
            <Toast.Header>
                <strong className="me-auto">Penpal</strong>
            </Toast.Header>
            <Toast.Body className="text-white">{props.text}</Toast.Body>
        </Toast>
    );
}


function StickyToastContainer(props) {
    return (
        <ToastContainer style={{ position: 'fixed', bottom: 0}}>
            {props.children}
        </ToastContainer>
    );
}

export {
    ItemListWithForm,
    AutoclosableToast,
    StickyToastContainer,
    GenericFetchJson
};