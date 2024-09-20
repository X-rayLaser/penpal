import React from 'react';
import Button from 'react-bootstrap/Button';
import Alert from 'react-bootstrap/Alert';
import Form from 'react-bootstrap/Form';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Card from 'react-bootstrap/Card';
import Accordion from 'react-bootstrap/Accordion';
import Collapse from 'react-bootstrap/Collapse';
import ListGroup from 'react-bootstrap/ListGroup';
import Tab from 'react-bootstrap/Tab';
import Tabs from 'react-bootstrap/Tabs';

import { ItemListWithForm, GenericFetchJson } from "./generic_components";
import { renderSize } from './utils';
import { Preset } from "./presets";
import { withRouter } from "./utils";


class BaseSelectionWidget extends React.Component {
    constructor(props) {
        super(props);
        this.selectionLabel = "Item";
        this.selectionId = "item_select"
        this.ariaLabel = this.selectionLabel + " selection";
        this.blankOptionText = "";
    }
    renderDetail(item) {
        return (
            <div>Item detail</div>
        );
    }

    renderDetailIfExists(item) {
        if (item) {
            return this.renderDetail(item);
        }

        return <div></div>
    }

    getName(item) {
        return item.name;
    }

    render() {
        let items = [];

        let selectedItem = null;
        
        let props = this.props;

        if (props.items.length > 0) {
            items = props.items.map((item, index) => {
                let name = this.getName(item);
                return <option key={index} value={name}>{name}</option>;
            });

            selectedItem = props.items.filter(item => this.getName(item) === props.selectedName)[0];
        }

        let detailWidget = this.renderDetailIfExists(selectedItem);

        const changeHandler = e => {
            props.onChange(e.target.value);
        }

        return (
            <div>
                <Row>
                    <Form.Label htmlFor={this.selectionId} column="lg" sm={4} lg={2}>
                        {this.selectionLabel}
                    </Form.Label>
                    <Col>
                        <Form.Select size="lg" id={this.selectionId}
                                    aria-label={this.ariaLabel}
                                    value={props.selectedName}
                                    onChange={changeHandler}>
                        {this.blankOptionText && (<option value="">{this.blankOptionText}</option>)}
                        {items}
                        </Form.Select>
                    </Col>
                </Row>
                {selectedItem && <div>{detailWidget}</div>}
            </div>
        );
    }
}

class SystemMessageSelectionWidget extends BaseSelectionWidget {
    constructor(props) {
        super(props);
        this.selectionLabel = "System message";
        this.selectionId = "system_message_select"
        this.ariaLabel = this.selectionLabel + " selection";
        this.blankOptionText = "--No system message--";
    }
    renderDetail(item) {
        console.log("selectedMessage: ", this.props.selectedName)
        return (
            <Card bg="light" text="dark" className="mt-3 mb-3">
                <Card.Body>
                    <Card.Title>{this.selectionLabel}</Card.Title>
                    <Card.Text>{item.text}</Card.Text>
                </Card.Body>
            </Card>
        );
    }
}

class VoiceSelectionWidget extends BaseSelectionWidget {
    constructor(props) {
        super(props);
        this.selectionLabel = "Voice sample id";
        this.selectionId = "voice_id_select"
        this.ariaLabel = this.selectionLabel + " selection";
        this.blankOptionText = "--No voice ids--";
    }
    renderDetail(item) {
        return (
            <div>
                <div className="mt-2 mb-2">
                    Listen to the chosen voice sample for {item.voice_id}:
                </div>
                <audio controls>
                    <source src={item.url} type="audio/wav" />
                    Your browser does not support the audio element.
                </audio>
            </div>
        );
    }

    getName(item) {
        return item.voice_id;
    }
}


class PresetSelectionWidget extends BaseSelectionWidget {
    constructor(props) {
        super(props);
        this.selectionLabel = "Preset";
        this.selectionId = "preset_select"
        this.ariaLabel = this.selectionLabel + " selection";
        this.blankOptionText = "--No system message--";
        this.state = {
            open: false,
            buttonText: "Show preset settings"
        };
        console.log("fa PresetSelectionWidget")
        this.handleClick = this.handleClick.bind(this);
    }

    handleClick() {
        this.setState(prevState => {
            let buttonText;
            let open = !prevState.open;


            if (open) {
                buttonText = "Hide preset settings";
            } else {
                buttonText = "Show preset settings"   
            }
            
            return {
                open,
                buttonText
            };
        })
    }
    renderDetail(item) {
        let preset = {
            name: item.name,
            eventKey: "0",
            settings: {
                temperature: item.temperature,
                topK: item.top_k,
                topP: item.top_p,
                minP: item.min_p,
                repeatPenalty: item.repeat_penalty,
                nPredict: item.n_predict
            }
        };

        return (
            <div className="mb-3">
                <Button variant="secondary" className="mt-3 mb-3" onClick={this.handleClick}
                        aria-controls="collapse-preset"
                        aria-expanded={open}>
                    {this.state.buttonText}
                </Button>
                <Collapse in={this.state.open}>
                    <div id="collapse-preset" className="mt-3">
                        <Preset preset={preset} />
                    </div>
                </Collapse>
            </div>
        );
    }

}


class NewConfigurationForm extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            name: "",
            selectedVoiceId: "",
            voices: [],
            systemMessages: [],
            selectedMessageName: "",
            presets: [],
            selectedPresetName: "",
            presetNames: [],
            nameToMessage: {},
            nameToPreset: {},
            loadingSystemMessages: true,
            loadingPresets: true,
            tools: [],
            supportedTools: [],
            chatTemplate: "",
            pythonServerUrl: "",
            reactComponentServerUrl: ""
        };

        this.handleNameChange = this.handleNameChange.bind(this);
        this.handleSystemMessageChange = this.handleSystemMessageChange.bind(this);
        this.handlePresetChange = this.handlePresetChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleCheck = this.handleCheck.bind(this);
        this.handleTemplateInput = this.handleTemplateInput.bind(this);
        this.handleVoiceChange = this.handleVoiceChange.bind(this);

        this.handlePythonServerUrlChange = this.handlePythonServerUrlChange.bind(this);
        this.handleReactComponentServerUrlChange = this.handleReactComponentServerUrlChange.bind(this);
    }

    componentDidMount() {
        //fetch system messages and presets and create lookup tables by name
        let fetcher = new GenericFetchJson();
        
        fetcher.performFetch('/chats/system_messages/').then(data => {
            let nameToMessage = {};
            data.forEach(msg => {
                nameToMessage[msg.name] = msg;
            });

            this.setState({
                systemMessages: data,
                selectedMessageName: "",
                nameToMessage,
                loadingSystemMessages: false
            })
        });

        fetcher.performFetch('/chats/presets/').then(data => {
            let nameToPreset = {};
            data.forEach(preset => {
                nameToPreset[preset.name] = preset;
            });

            this.setState({
                presets: data,
                selectedPresetName: "",
                nameToPreset,
                loadingPresets: false
            })
        });

        fetcher.performFetch('/chats/list-voices/').then(voices => {
            this.setState({ voices });
        });

        fetcher.performFetch('/chats/supported-tools/').then(data => {
            this.setState({ supportedTools: data });
        });
    }

    groupByRepoId(entries) {
        let result = {};

        entries.forEach(modelInfo => {
            if (!result.hasOwnProperty(modelInfo.repo_id)) {
                result[modelInfo.repo_id] = [];
            }
            result[modelInfo.repo_id].push(modelInfo);
        });

        return result;
    }

    handleNameChange(e) {
        this.setState({ name: e.target.value });
    }

    handleSystemMessageChange(selectedMessageName) {
        this.setState({ selectedMessageName });
    }

    handlePresetChange(selectedPresetName) {
        this.setState({ selectedPresetName });
    }

    handleVoiceChange(selectedVoiceId) {
        this.setState({ selectedVoiceId });
    }

    handleCheck(checked, name) {
        
        this.setState(prevState => {
            let tools = [...prevState.tools];
            let index = tools.indexOf(name);

            if (index >= 0) {
                tools.splice(index, 1);
            } else {
                tools.push(name);
            }
            return {
                tools
            };
        })

    }

    handlePythonServerUrlChange(e) {
        this.setState({ pythonServerUrl: e.target.value });
    }

    handleReactComponentServerUrlChange(e) {
        this.setState({ reactComponentServerUrl: e.target.value });
    }

    handleSubmit(e) {
        e.preventDefault();
        let preset = this.state.nameToPreset[this.state.selectedPresetName];

        let sandboxes = {};

        if (this.state.pythonServerUrl) {
            sandboxes["PYTHON_PROJECT"] = this.state.pythonServerUrl;
        }

        if (this.state.reactComponentServerUrl) {
            sandboxes["STYLED_REACT_COMPONENT_PROJECT"] = this.state.reactComponentServerUrl;
        }

        let data = {
            name: this.state.name,
            tools: this.state.tools,
            sandboxes,
            template_spec: this.state.chatTemplate,
            voice_id: this.state.selectedVoiceId
        };

        if (preset) {
            data.preset = preset.id;
        }

        if (this.state.selectedMessageName) {
            let message = this.state.nameToMessage[this.state.selectedMessageName];
            data.system_message = message.id;
        }

        console.log(data);
        this.props.onSubmit(data);
    }

    handleTemplateInput(e) {
        this.setState({ chatTemplate: e.target.value });
    }

    render() {
        let nameErrors = [];

        if (this.props.errors.hasOwnProperty("name")) {
            nameErrors = this.props.errors.name.map((error, index) => 
                <Alert key={index} className="mt-2 mb-2" variant="danger">{error}</Alert>
            );
        }

        let checkboxes = this.state.supportedTools.map((name, index) => {
            let checked = false;

            this.state.tools.forEach(tool => {
                if (tool === name) {
                    checked = true;
                }
            });
            return (
                <Form.Check
                    key={index}
                    label={name}
                    name="tools"
                    type="checkbox"
                    checked={checked}
                    onChange={e => this.handleCheck(e.target.checked, name)}
                    id={`inline-checkbox-${index}`}
                    style={{ textTransform: 'capitalize' }}
                />
            );
        });

        // todo: display errors for other fields

        console.log('selected message name', this.state.selectedMessageName);

        return (
            <Form onSubmit={this.handleSubmit}>
                <Row className="mb-3">
                    <Form.Label htmlFor="new_configuration_name" column="lg" sm={4} lg={2}>Name</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="new_configuration_name" name="name" type="text"
                                        placeholder="Name of your new configuration" 
                                        value={this.state.name}
                                        onChange={this.handleNameChange} />
                    </Col>
                </Row>
                {nameErrors.length > 0 && 
                    <div>{nameErrors}</div>
                }

                <div className="mb-3">
                    <SystemMessageSelectionWidget items={this.state.systemMessages}
                                                  selectedName={this.state.selectedMessageName}
                                                  onChange={this.handleSystemMessageChange} />
                </div>
                <div className="mb-3">
                    <PresetSelectionWidget items={this.state.presets}
                                           selectedName={this.state.selectedPresetName}
                                           onChange={this.handlePresetChange} />
                </div>

                <div className="mb-3">
                    <VoiceSelectionWidget items={this.state.voices}
                                          selectedName={this.state.selectedVoiceId}
                                          onChange={this.handleVoiceChange} />
                </div>

                <Form.Group className="mb-3">
                    <Form.Label>Chat template spec (JSON)</Form.Label>
                    <Form.Control as="textarea" rows={10} placeholder="Enter a template in json format"
                          onInput={this.handleTemplateInput}
                          value={this.state.chatTemplate} />
                </Form.Group>

                {checkboxes &&
                <Form.Group className="mb-3">
                    <Form.Label>Tools available to LLM</Form.Label>
                    <div>{checkboxes}</div>
                </Form.Group>
                }

                <Row className="mb-3">
                    <Form.Label htmlFor="python_sandbox_url" column="lg" sm={4} lg={2}>Python server</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="python_sandbox_url" name="name" type="text"
                                        placeholder="URL of the server with Python environment" 
                                        value={this.state.pythonServerUrl}
                                        onChange={this.handlePythonServerUrlChange} />
                    </Col>
                </Row>

                <Row className="mb-3">
                    <Form.Label htmlFor="react_component_sandbox_url" column="lg" sm={4} lg={2}>React Component server</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="react_component_sandbox_url" name="name" type="text"
                                        placeholder="URL of the server with React+webpack environment" 
                                        value={this.state.reactComponentServerUrl}
                                        onChange={this.handleReactComponentServerUrlChange} />
                    </Col>
                </Row>

                <Button type="submit">Create configuration</Button>
            </Form>
        );
    }
}


class ConfigurationsPage extends ItemListWithForm {
    constructor(props) {
        super(props);
        console.log("Confi page1")
        this.listUrl = "/chats/configurations/";
        this.formHeader = "Create new LLM configuration";
    }

    createItem(item) {
        return item;
    }

    containerizeItems(items) {
        return (
            <div>{items}</div>
        );
    }

    renderItem(item, index, handleDeleteItem) {
        let preset = null;
        if (item.preset_ro) {
            preset = {
                name: item.preset_ro.name,
                settings: {
                    temperature: item.preset_ro.temperature,
                    topK: item.preset_ro.top_k,
                    topP: item.preset_ro.top_p,
                    minP: item.preset_ro.min_p,
                    repeatPenalty: item.preset_ro.repeat_penalty,
                    nPredict: item.preset_ro.n_predict
                }
            };
        }

        let tools = item.tools.map((name, index) => {
            return (
                <ListGroup.Item key={index} style={{ width: "20em", textTransform: 'capitalize' }} variant="success">
                    {name}
                </ListGroup.Item>
            );
        });

        return (
            <Card key={index} className="mb-3">
                <Card.Header>{item.name}</Card.Header>
                <Card.Body>
                    <Accordion className="mb-3">
                        {item.system_message_ro && (
                            <Accordion.Item eventKey="0">
                                <Accordion.Header>System message: {item.system_message_ro.name}</Accordion.Header>
                                <Accordion.Body>{item.system_message_ro.text}</Accordion.Body>
                            </Accordion.Item>
                        )}
                        {preset && (
                            <Accordion.Item eventKey="1">
                                <Accordion.Header>Generation preset: {preset.name}</Accordion.Header>
                                <Accordion.Body>
                                    <Preset preset={preset} />
                                </Accordion.Body>
                            </Accordion.Item>
                        )}
                    </Accordion>

                    {tools.length > 0 && 
                    <div className="mb-3">
                        <div>Tools:</div>
                        <ListGroup className="mt-2">{tools}</ListGroup>
                    </div>
                    }

                    <Button variant="danger" size="lg" onClick={e => handleDeleteItem(item)}>
                        Delete configuration
                    </Button>
                </Card.Body>
            </Card>
        );
    }

    renderForm(handleSubmit) {
        return (
            <NewConfigurationForm onSubmit={handleSubmit} errors={this.state.errors} />
        );
    }
}

ConfigurationsPage = withRouter(ConfigurationsPage);

export {
    ConfigurationsPage
}
