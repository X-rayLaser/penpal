import React from 'react';
import Button from 'react-bootstrap/Button';
import Alert from 'react-bootstrap/Alert';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Accordion from 'react-bootstrap/Accordion';
import { ItemListWithForm } from "./generic_components";
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
                    <Accordion.Header>Generation settings</Accordion.Header>
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


function PresetAccordionItem(props) {
    return (
        <Accordion.Item eventKey={props.eventKey}>
            <Accordion.Header>{props.preset.name}</Accordion.Header>
            <Accordion.Body>
                <Preset {...props} />
            </Accordion.Body>
      </Accordion.Item>
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
        <div>
            <GenerationSettings settings={props.preset.settings} eventHandlers={eventHandlers} 
                                errors={props.errors} disabled={true} />
            {props.onDeletePreset &&
            <Button variant="danger" onClick={handleClick} disabled={props.disableDelete}>Delete preset</Button>
            }
        </div>
    );
}



function copyObject(obj) {
    return JSON.parse(JSON.stringify(obj));
}

class NewPresetForm extends React.Component {
    constructor(props) {
        super(props);
        
        this.defaultSettings = {
            temperature: 0.3,
            topK: 40,
            topP: 0.95,
            minP: 0.05,
            repeatPenalty: 1.1,
            nPredict: 512
        };

        this.state = {
            name: "",
            settings: this.defaultSettings,
            submissionInProgress: false
        };

        this.handleNameChange = this.handleNameChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);

    }

    handleNameChange(e) {
        this.setState({ name: e.target.value });
    }

    unpdateSettingsField(settings, field, value) {
        settings = copyObject(settings);
        settings[field] = value;
        this.setState({ settings });
    }

    handleSubmit(event) {
        event.preventDefault();

        this.setState({ submissionInProgress: true });

        let body = {
            name: this.state.name,
            temperature: this.state.settings.temperature,
            top_k: this.state.settings.topK,
            top_p: this.state.settings.topP,
            min_p: this.state.settings.minP,
            repeat_penalty: this.state.settings.repeatPenalty,
            n_predict: this.state.settings.nPredict
        };

        this.props.onSubmit(body).finally(() => {
            this.setState({ submissionInProgress: false });
        });
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

        let nameErrors = [];

        if (this.props.errors.hasOwnProperty("name")) {
            nameErrors = this.props.errors.name.map((error, index) => 
                <Alert key={index} className="mt-2 mb-2" variant="danger">{error}</Alert>
            );
        }
        return (
            <Form onSubmit={this.handleSubmit}>
                <Form.Group className="mb-3">
                    <Form.Label htmlFor="new_preset_name">Name</Form.Label>
                    <Form.Control id="new_preset_name" name="name" type="text"
                                    placeholder="Name of your new preset" 
                                    value={this.state.name}
                                    onChange={this.handleNameChange} />

                    {nameErrors.length > 0 && 
                        <div>{nameErrors}</div>
                    }
                </Form.Group>
                <Form.Group className="mb-3">
                    <GenerationSettings settings={this.state.settings} eventHandlers={handlers}
                                        errors={this.props.errors} />
                </Form.Group>
                <Button type="submit" disabled={this.props.submissionInProgress}>Submit</Button>
            </Form>
        );
    }
}

class PresetsPage extends ItemListWithForm {
    constructor(props) {
        super(props);

        this.listUrl = "/chats/presets/";
        this.itemsHeader = "Presets";
    }

    createItem(item) {
        return {
            id: item.id,
            name: item.name,
            settings: {
                temperature: item.temperature,
                topK: item.top_k,
                topP: item.top_p,
                minP: item.min_p,
                repeatPenalty: item.repeat_penalty,
                nPredict: item.n_predict
            }
        };
    }

    renderItem(item, index, handleDeleteItem) {
        return (
                <PresetAccordionItem key={index} eventKey={index} name={item.name} preset={item}
                    onDeletePreset={handleDeleteItem}
                    disableDelete={this.state.deletionInProgress || this.state.submissionInProgress} />
        );
    }

    renderForm(handleSubmit) {
        return (
            <NewPresetForm onSubmit={handleSubmit}
                           errors={this.state.errors}
                           submissionInProgress={this.state.submissionInProgress} />
        );
    }
}

PresetsPage = withRouter(PresetsPage);

export {
    PresetsPage,
    CollapsibleLLMSettings,
    Preset,
    getRandomInt
}
