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


function getRandomInt() {
    let max = Math.pow(2, 64);
    return Math.floor(Math.random() * max);
}


function SliderWithInput(props) {
    let errorList = props.errors || [];
    let errorMessages = errorList.map((error, index) => 
        <Alert className="mt-3 mb-3" key={index} variant="danger">{error}</Alert>
    );

    //trick to automatically generate unique ids for fields in GenerationSettings
    let id =`${props.name}_${getRandomInt()}`;

    return (
        <div>
            <Form.Label htmlFor={id}>{props.label}</Form.Label>
            <Row>
                <Col xs={8} sm={10}>
                    <Form.Range min={props.min} max={props.max} step={props.step}
                                value={props.value} onChange={props.onChange} disabled={props.disabled} />
                </Col>
                <Col>
                    <Form.Control id={id} name={props.name} type="number" min={props.min} max={props.max} step={props.step}
                                  value={props.value} onChange={props.onChange} disabled={props.disabled} />
                </Col>
            </Row>
            {errorMessages.length > 0 && 
                <div>{errorMessages}</div>
            }
        </div>
    );
}


function CollapsibleLLMSettings(props) {
    return (
        <div className="mt-2">
            <Accordion>
                <Accordion.Item eventKey="0">
                    <Accordion.Header>LLM settings</Accordion.Header>
                    <Accordion.Body>
                        <GenerationSettings {...props} />
                    </Accordion.Body>
                </Accordion.Item>
            </Accordion>
        </div>
    );
}


function GenerationSettings(props) {
    let errors = props.errors || {};

    let disabled;
    if (props.disabled === undefined) {
        disabled = false;
    } else {
        disabled = props.disabled;
    }

    return (
        <div>
            <SliderWithInput name="temperature" label="Temperature" min="0" max="100" step="0.01" 
                             value={props.settings.temperature} onChange={props.eventHandlers.onTemperatureChange}
                             errors={errors.temperature || []} disabled={disabled} />

            <SliderWithInput name="top_k" label="Top K" min="1" max="1000" step="1" 
                             value={props.settings.topK} onChange={props.eventHandlers.onTopKChange}
                             errors={errors.top_k || []} disabled={disabled} />

            <SliderWithInput name="top_p" label="Top P" min="0" max="1" step="0.01" 
                             value={props.settings.topP} onChange={props.eventHandlers.onTopPChange}
                             errors={errors.top_p || []} disabled={disabled} />

            <SliderWithInput name="min_p" label="Min P" min="0" max="1" step="0.01" 
                             value={props.settings.minP} onChange={props.eventHandlers.onMinPChange}
                             errors={errors.min_p || []} disabled={disabled} />

            <SliderWithInput name="repeat_penalty" label="Repeatition penalty" min="0" max="100" step="0.01" 
                             value={props.settings.repeatPenalty} onChange={props.eventHandlers.onRepeatPenaltyChange}
                             errors={errors.repeat_penalty || []} disabled={disabled} />

            <SliderWithInput name="n_predict" label="Maximum # of tokens" min="1" max="4096" step="1" 
                             value={props.settings.nPredict} onChange={props.eventHandlers.onMaxTokensChange}
                             errors={errors.n_predict || []} disabled={disabled} />
        </div>
    );
}


function Preset(props) {
    function handleClick(e) {
        props.onDeletePreset(props.preset);
    }

    let eventHandlers;
    if (props.eventHandlers === undefined) {
        eventHandlers = {
            onTemperatureChange: e => {},
            onTopKChange: e => {},
            onTopPChange: e => {},
            onMinPChange: e => {},
            onRepeatPenaltyChange: e => {},
            onMaxTokensChange: e => {}
        };
    } else {
        eventHandlers = props.eventHandlers;
    }

    return (
        <Accordion.Item eventKey={props.eventKey}>
            <Accordion.Header>{props.preset.name}</Accordion.Header>
            <Accordion.Body>
                <GenerationSettings settings={props.preset.settings} eventHandlers={eventHandlers} 
                                    errors={props.errors} disabled={true} />
                <Button variant="danger" onClick={handleClick} disabled={props.disableDelete}>Delete preset</Button>
            </Accordion.Body>
      </Accordion.Item>
    );
}


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


function NewPresetForm(props) {
    let nameErrors = [];

    if (props.errors.hasOwnProperty("name")) {
        nameErrors = props.errors.name.map((error, index) => 
            <Alert key={index} className="mt-2 mb-2" variant="danger">{error}</Alert>
        );
    }

    // todo: turn this into a component, move related event handlers and fetch calls here

    return (
        <Card className="mt-2">
            <Card.Body>
                <Card.Title>Create a new preset</Card.Title>
                {props.submissionError && 
                    <Alert className="mt-3 mb-3" variant="danger">{props.submissionError}</Alert>
                }
                <Form onSubmit={props.onSubmitForm}>
                    <Form.Group className="mb-3">
                        <Form.Label htmlFor="new_preset_name">Name</Form.Label>
                        <Form.Control id="new_preset_name" name="name" type="text"
                                        placeholder="Name of your new preset" 
                                        value={props.presetName}
                                        onChange={props.onNameChange} />

                        {nameErrors.length > 0 && 
                            <div>{nameErrors}</div>
                        }
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <GenerationSettings settings={props.settings} eventHandlers={props.eventHandlers}
                                            errors={props.errors} />
                    </Form.Group>
                    <Button type="submit" disabled={props.submissionInProgress}>
                        Create preset
                    </Button>
                </Form>
            </Card.Body>
        </Card>
    );
}


class PresetsPage extends React.Component {
    constructor(props) {
        super(props);

        this.url = "/chats/presets/";
        this.defaultSettings = {
            temperature: 0.3,
            topK: 40,
            topP: 0.95,
            minP: 0.05,
            repeatPenalty: 1.1,
            nPredict: 512
        };

        this.state = {
            presets: [],
            name: "",
            settings: this.defaultSettings,

            submissionError: "",
            errors: {},
            fetchPresetsError: "",
            deletionError: "",

            submissionInProgress: false,
            deletionInProgress: false,
            fetchPresetsInProgress: true,

            showCreatedPresetToast: false,
            showDeletedPresetToast: false
        };

        this.handleNameChange = this.handleNameChange.bind(this);
        this.handleSubmitForm = this.handleSubmitForm.bind(this);
        this.handleDeletePreset = this.handleDeletePreset.bind(this);

        this.handleHideCreatedToast = this.handleHideCreatedToast.bind(this);
        this.handleHideDeletedToast = this.handleHideDeletedToast.bind(this);
    }

    componentDidMount() {
        fetch(this.url, {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        }).then(response => {
            if (response.ok) {
                return response.json();
            } else if (response.status === 404) {
                throw { message: "Failed to fetch presets: resource not found (404)" };
            } else if (response.status >= 500) {
                throw { message: "Failed to fetch presets because of server error" };
            } else {
                throw { message: "Failed to fetch presets because of unknown error" };
            }
        }).then(data => {
            let presets = data.map((fieldObject, index) => {
                return {
                    id: fieldObject.id,
                    name: fieldObject.name,
                    eventKey: `${index}`,
                    settings: {
                        temperature: fieldObject.temperature,
                        topK: fieldObject.top_k,
                        topP: fieldObject.top_p,
                        minP: fieldObject.min_p,
                        repeatPenalty: fieldObject.repeat_penalty,
                        nPredict: fieldObject.n_predict
                    }
                }
            })
            this.setState({ presets });
        }).catch(reason => {
            if (reason.hasOwnProperty("message")) {
                this.setState({ fetchPresetsError: reason.message });
            } else {
                this.setState({ fetchPresetsError: "Failed to fetch presets due to an unknown error" });
            }
        }).finally(() => {
            this.setState({ fetchPresetsInProgress: false });
        })
    }

    copyObject(obj) {
        return JSON.parse(JSON.stringify(obj));
    }

    unpdateSettingsField(settings, field, value) {
        settings = this.copyObject(settings);
        settings[field] = value;
        this.setState({ settings });
    }

    handleNameChange(e) {
        this.setState({ name: e.target.value });
    }

    handleSubmitForm(e) {
        e.preventDefault();
        let body = {
            name: this.state.name,
            temperature: this.state.settings.temperature,
            top_k: this.state.settings.topK,
            top_p: this.state.settings.topP,
            min_p: this.state.settings.minP,
            repeat_penalty: this.state.settings.repeatPenalty,
            n_predict: this.state.settings.nPredict
        };

        this.setState({ submissionInProgress: true });

        fetch(this.url, {
            method: 'POST',
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(body)
        }).then(response => {
            if (response.ok) {
                return response.json();
            } else if (response.status === 404) {
                throw { message: "Submission failed because resource not found (404)" };
            } else if (response.status >= 500) {
                throw { message: "Submission failed because of server error" };
            } else if (response.status >= 400) {
                return response.json().then(errorsObject => {
                    console.log("HERE")
                    throw { errorsObject };
                });
            }
        }).then(data => {
            this.setState(prevState => {
                let newPreset = {
                    id: data.id,
                    name: data.name,
                    eventKey: `${prevState.presets.length}`,
                    settings: {
                        temperature: data.temperature,
                        topK: data.top_k,
                        topP: data.top_p,
                        minP: data.min_p,
                        repeatPenalty: data.repeat_penalty,
                        nPredict: data.n_predict
                    }
                };
                return {
                    presets: [...prevState.presets, newPreset],
                    errors: [],
                    submissionError: "",
                    name: "",
                    settings: this.copyObject(this.defaultSettings),
                    showCreatedPresetToast: true
                }
            });
        }).catch(reason => {
            console.error(reason);

            if (reason.hasOwnProperty("errorsObject")) {
                this.setState({
                    errors: reason.errorsObject,
                    submissionError: "Some fields are not filled correctly"
                });
            } else if (reason.hasOwnProperty("message")) {
                this.setState({ submissionError: reason.message });
            } else {
                this.setState({ submissionError: "Submission failed due to an unknown error" });
            }
        }).finally(() => {
            this.setState({ submissionInProgress: false });
        });
    }

    handleDeletePreset(preset) {
        let detailUrl = `/chats/presets/${preset.id}/`;

        this.setState({ deletionInProgress: true });
        fetch(detailUrl, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        }).then(response => {
            if (response.ok) {
                return {};
            } else if (response.status === 404) {
                throw { message: "Failed to delete preset: resource not found (404)" };
            } else if (response.status >= 500) {
                throw { message: "Failed to delete preset: server error" };
            } else {
                throw { message: "Failed to delete preset: unknown error" };
            }
        }).then(data => {
            this.setState(prevState => {
                let newPresets = prevState.presets.filter(p => p.id !== preset.id);
                return {
                    presets: newPresets,
                    showDeletedPresetToast: true,
                    deletionError: ""
                };
            });
        }).catch(reason => {
            if (reason.hasOwnProperty("message")) {
                this.setState({ deletionError: reason.message });
            } else {
                this.setState({ deletionError: "Failed to delete preset due to an unknown error" });
            }
        }).finally(() => {
            this.setState({  deletionInProgress: false });
        });
    }

    handleHideCreatedToast() {
        this.setState({ showCreatedPresetToast: false });
    }

    handleHideDeletedToast() {
        this.setState({ showDeletedPresetToast: false });
    }

    render() {
        const onTemperatureChange = event => {
            this.unpdateSettingsField(this.state.settings, "temperature", event.target.value);
        };

        const onTopKChange = event => {
            this.unpdateSettingsField(this.state.settings, "topK", event.target.value);
        };

        const onTopPChange = event => {
            this.unpdateSettingsField(this.state.settings, "topP", event.target.value);
        };

        const onMinPChange = event => {
            this.unpdateSettingsField(this.state.settings, "minP", event.target.value);
        };

        const onRepeatPenaltyChange = event => {
            this.unpdateSettingsField(this.state.settings, "repeatPenalty", event.target.value);
        };

        const onMaxTokensChange = event => {
            this.unpdateSettingsField(this.state.settings, "nPredict", event.target.value);
        };

        let handlers = {
            onTemperatureChange,
            onTopKChange,
            onTopPChange,
            onMinPChange,
            onRepeatPenaltyChange,
            onMaxTokensChange
        };

        let accordionItems = this.state.presets.map((p, index) => 
            <Preset key={index} eventKey={p.eventKey} name={p.name} preset={p} 
                    onDeletePreset={this.handleDeletePreset}
                    disableDelete={this.state.deletionInProgress || this.state.submissionInProgress} />
        );

        return (
            <div>
                <StickyToastContainer>
                    <AutoclosableToast show={this.state.showCreatedPresetToast}
                                            text="You've successfully added a new preset"
                                            onClose={this.handleHideCreatedToast} />

                    <AutoclosableToast show={this.state.showDeletedPresetToast}
                                            text="You've successfully deleted a preset"
                                            onClose={this.handleHideDeletedToast} />
                </StickyToastContainer>

                <NewPresetForm submissionError={this.state.submissionError}
                               onSubmitForm={this.handleSubmitForm}
                               presetName={this.state.name}
                               onNameChange={this.handleNameChange}
                               settings={this.state.settings}
                               eventHandlers={handlers}
                               errors={this.state.errors}
                               submissionInProgress={this.state.submissionInProgress} />

                <h2 className="mt-2 mb-2">Presets</h2>
                {this.state.deletionError && <Alert variant="danger">{this.state.deletionError}</Alert>}
                {this.state.fetchPresetsInProgress && <Spinner />}
                {this.state.fetchPresetsError && <Alert variant="danger">{this.state.fetchPresetsError}</Alert>}
                {!this.state.fetchPresetsInProgress && <Accordion>{accordionItems}</Accordion>}
            </div>
        );
    }
};

PresetsPage = withRouter(PresetsPage);

export {
    PresetsPage,
    CollapsibleLLMSettings
}