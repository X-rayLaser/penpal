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


class RepositorySelectionWidget extends BaseSelectionWidget {
    constructor(props) {
        super(props);
        this.selectionLabel = "Model repository id";
        this.selectionId = "model_repository_select"
        this.ariaLabel = this.selectionLabel + " selection";
    }

    renderDetail(item) {
        return (
            <Card bg="light" text="dark" className="mt-3 mb-3">
                <Card.Body>
                    <Card.Title>{this.selectionLabel}</Card.Title>
                    <Card.Text>{item}</Card.Text>
                </Card.Body>
            </Card>
        );
    }

    getName(item) {
        return item;
    }
}

class ModelSelectionWidget extends BaseSelectionWidget {
    constructor(props) {
        super(props);
        this.selectionLabel = "Model file";
        this.selectionId = "model_file_select"
        this.ariaLabel = this.selectionLabel + " selection";
    }

    renderDetail(item) {
        let licensesText = "";
        if (item.repo.licenses) {
            licensesText = item.repo.licenses.join(", ");
        }

        let papersText = "";
        if (item.repo.papers) {
            papersText = item.repo.papers.join(", ");
        }

        let datasetsText = "";
        if (item.repo.datasets) {
            datasetsText = item.repo.datasets.join(", ");
        }

        return (
            <Card bg="light" text="dark" className="mt-3 mb-3">
                <Card.Body>
                    <Card.Title>{this.selectionLabel}</Card.Title>
                    <Card.Text>File: {item.file_name}</Card.Text>
                    <Card.Text>Size: {renderSize(item.size)}</Card.Text>
                    {licensesText && <Card.Text>Licenses: {licensesText}</Card.Text>}
                    {papersText && <Card.Text>Papers: {papersText}</Card.Text>}
                    {datasetsText && <Card.Text>Datasets: {datasetsText}</Card.Text>}
                </Card.Body>
            </Card>
        );
    }

    getName(item) {
        return item.file_name;
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


class ModelLaunchConfig extends React.Component {
    constructor(props) {
        super(props);

        this.state = this.defaultLaunchParams;

        this.handleContextSizeChange = this.handleContextSizeChange.bind(this);
        this.handleNglChange = this.handleNglChange.bind(this);
        this.handleNumThreadsChange = this.handleNumThreadsChange.bind(this);
        this.handleNumBatchThreadsChange = this.handleNumBatchThreadsChange.bind(this);
        this.handleBatchSizeChange = this.handleBatchSizeChange.bind(this);
        this.handleMaxTokensChange = this.handleMaxTokensChange.bind(this);
    }

    get defaultLaunchParams() {
        return {...this.constructor.defaultLaunchParams};
    }

    handleContextSizeChange(e) {
        this.updateStateField("contextSize", e);
    }

    handleNglChange(e) {
        this.updateStateField("ngl", e);
    }

    handleNumThreadsChange(e) {
        this.updateStateField("numThreads", e);
    }

    handleNumBatchThreadsChange(e) {
        this.updateStateField("numBatchThreads", e);
    }

    handleBatchSizeChange(e) {
        this.updateStateField("batchSize", e);
    }

    handleMaxTokensChange(e) {
        this.updateStateField("nPredict", e);
    }

    updateStateField(field, event) {
        let update = {};
        let value = event.target.value;
        let intValue;

        if (!value) {
            intValue = 0;
        } else {
            try {
                intValue = parseInt(value);
            } catch (e) {
                console.error("Parsing error, value:", value);
                intValue = 0;
            }
        }

        if (isNaN(intValue)) {
            intValue = 0;
        }

        update[field] = intValue;
        this.setState(update, () => this.notify());
    }

    notify() {
        this.props.onChange(this.state);
    }

    render() {
        return (
            <div>
                <Row className="mb-3">
                    <Form.Label htmlFor="config_context_size" column="lg" sm={6} lg={4}>Context size</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="config_context_size" name="context-size" type="number"
                                            placeholder="Context size of your LLM" 
                                            value={this.state.contextSize}
                                            onChange={this.handleContextSizeChange} />
                    </Col>
                </Row>
                <Row className="mb-3">
                    <Form.Label htmlFor="config_gpu_layers" column="lg" sm={6} lg={4}># GPU layers</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="config_gpu_layers" name="context-size" type="number"
                                            placeholder="Number of loaded GPU layers"
                                            value={this.state.ngl}
                                            onChange={this.handleNglChange} />
                    </Col>
                </Row>
                <Row className="mb-3">
                    <Form.Label htmlFor="config_num_gen_threads" column="lg" sm={6} lg={4}># threads for generation</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="config_num_gen_threads" name="num_generation_threads" type="number"
                                            placeholder="Number of threads to use during generation"
                                            value={this.state.numThreads}
                                            onChange={this.handleNumThreadsChange} />
                    </Col>
                </Row>

                <Row className="mb-3">
                    <Form.Label htmlFor="config_num_batch_threads" column="lg" sm={6} lg={4}># batch threads</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="config_num_batch_threads" name="num_batch_threads" type="number"
                                            placeholder="Number of threads used during batch processing"
                                            value={this.state.numBatchThreads}
                                            onChange={this.handleNumBatchThreadsChange} />
                    </Col>
                </Row>

                <Row className="mb-3">
                    <Form.Label htmlFor="config_batch_size" column="lg" sm={6} lg={4}>Batch size</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="config_batch_size" name="batch_size" type="number"
                                            placeholder="Size of batch for prompt processing"
                                            value={this.state.batchSize}
                                            onChange={this.handleBatchSizeChange} />
                    </Col>
                </Row>

                <Row className="mb-3">
                    <Form.Label htmlFor="config_n_predict" column="lg" sm={6} lg={4}># tokens to predict</Form.Label>
                    <Col>
                        <Form.Control size="lg" id="config_n_predict" name="n_predict" type="number"
                                            placeholder="Maximum number of tokens to predict"
                                            value={this.state.nPredict}
                                            onChange={this.handleMaxTokensChange} />
                    </Col>
                </Row>
            </div>
        );
    }
}


ModelLaunchConfig.defaultLaunchParams = {
    contextSize: 512,
    ngl: 0,
    numThreads: 2,
    numBatchThreads: 2,
    batchSize: 512,
    nPredict: 512
};

class NewConfigurationForm extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            name: "",
            selectedRepo: "",
            selectedModelFile: "",
            selectedMMprojectorRepo: "",
            selectedMMprojectorModelFile: "",
            selectedVoiceId: "",
            launchConfig: ModelLaunchConfig.defaultLaunchParams,
            repos: [],
            modelFiles: [],
            projectorFiles: [],
            voices: [],
            installedModels: {}, // repository -> model_file mapping
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
            chatTemplate: ""
        };

        this.handleNameChange = this.handleNameChange.bind(this);
        this.handleSystemMessageChange = this.handleSystemMessageChange.bind(this);
        this.handlePresetChange = this.handlePresetChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleModelRepoChange = this.handleModelRepoChange.bind(this);
        this.handleModelFileChange = this.handleModelFileChange.bind(this);
        this.handleLaunchConfChanged = this.handleLaunchConfChanged.bind(this);
        this.handleCheck = this.handleCheck.bind(this);
        this.handleTemplateInput = this.handleTemplateInput.bind(this);

        this.handleProjectorRepoChange = this.handleProjectorRepoChange.bind(this);
        this.handleProjectorModelChange = this.handleProjectorModelChange.bind(this);

        this.handleVoiceChange = this.handleVoiceChange.bind(this);
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

        fetcher.performFetch('/modelhub/installed-models/').then(entries => {
            let groupedEntries = this.groupByRepoId(entries);
            let repos = Object.keys(groupedEntries);
            let selectedRepo = "";
            let selectedModelFile = "";
            let modelFiles = [];

            if (repos.length > 0) {
                selectedRepo = repos[0];
                modelFiles = groupedEntries[selectedRepo];
                if (modelFiles.length > 0) {
                    selectedModelFile = modelFiles[0].file_name;
                }
            }

            this.setState({
                repos,
                installedModels: groupedEntries,
                selectedRepo,
                modelFiles,
                selectedModelFile
            });
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

    handleModelRepoChange(selectedRepo) {
        let selection = this.updateSelectionFields(selectedRepo);
        this.setState({
            selectedRepo,
            modelFiles: selection.modelFiles,
            selectedModelFile: selection.selectedModelFile
        });
    }

    handleProjectorRepoChange(selectedRepo) {
        let selection = this.updateSelectionFields(selectedRepo);
        this.setState({
            selectedMMprojectorRepo: selectedRepo,
            projectorFiles: selection.modelFiles,
            selectedMMprojectorModelFile: selection.selectedModelFile
        });
    }

    handleProjectorModelChange(selectedModelFile) {
        this.setState({ selectedMMprojectorModelFile: selectedModelFile });
    }

    updateSelectionFields(selectedRepo) {
        let modelFiles = [];
        let selectedModelFile = "";
        if (this.state.installedModels.hasOwnProperty(selectedRepo)) {
            modelFiles = this.state.installedModels[selectedRepo];
        }

        if (modelFiles.length > 0) {
            selectedModelFile = modelFiles[0].file_name;
        }

        return {
            modelFiles,
            selectedModelFile
        };
    }

    handleVoiceChange(selectedVoiceId) {
        this.setState({ selectedVoiceId });
    }

    handleModelFileChange(selectedModelFile) {
        this.setState({ selectedModelFile });
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

    handleLaunchConfChanged(launchConfig) {
        this.setState({ launchConfig });
    }

    handleSubmit(e) {
        e.preventDefault();
        let preset = this.state.nameToPreset[this.state.selectedPresetName];

        if (this.state.selectedMMprojectorModelFile) {
            this.state.launchConfig['mmprojector'] = this.state.selectedMMprojectorModelFile;
        }

        let data = {
            name: this.state.name,
            model_repo: this.state.selectedRepo,
            file_name: this.state.selectedModelFile,
            launch_params: this.state.launchConfig,
            tools: this.state.tools,
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
                    <RepositorySelectionWidget 
                        items={this.state.repos}
                        selectedName={this.state.selectedRepo}
                        onChange={this.handleModelRepoChange} 
                    />
                </div>

                <div className="mb-3">
                    <ModelSelectionWidget 
                        items={this.state.modelFiles}
                        selectedName={this.state.selectedModelFile}
                        onChange={this.handleModelFileChange} 
                    />
                </div>

                <div className="mb-3">
                    <RepositorySelectionWidget
                        items={["", ...this.state.repos]}
                        selectedName={this.state.selectedMMprojectorRepo}
                        onChange={this.handleProjectorRepoChange}
                    />
                </div>

                <div className="mb-3">
                    <ModelSelectionWidget
                        items={this.state.projectorFiles}
                        selectedName={this.state.selectedMMprojectorModelFile}
                        onChange={this.handleProjectorModelChange}
                    />
                </div>

                <Accordion className="mb-3">
                    <Accordion.Item eventKey="0">
                        <Accordion.Header>Model launch parameters</Accordion.Header>
                        <Accordion.Body>
                            <ModelLaunchConfig onChange={this.handleLaunchConfChanged} />
                        </Accordion.Body>
                    </Accordion.Item>
                </Accordion>

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
                    <div className="mb-3">Repository: {item.model_repo}</div>
                    <div className="mb-3">Model file: {item.file_name}</div>

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
                        <Accordion.Item eventKey="2">
                            <Accordion.Header>Model launch parameters</Accordion.Header>
                            <Accordion.Body>
                                <div>Context size: {item.launch_params.contextSize}</div>
                                <div># GPU layers: {item.launch_params.ngl}</div>
                                <div># threads for generation: {item.launch_params.numThreads}</div>
                                <div># batch threads: {item.launch_params.numBatchThreads}</div>
                                <div>Batch size: {item.launch_params.batchSize}</div>
                                <div># tokens to predict: {item.launch_params.nPredict}</div>
                            </Accordion.Body>
                        </Accordion.Item>
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
