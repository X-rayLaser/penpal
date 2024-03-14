import React from 'react';
import ListGroup from 'react-bootstrap/ListGroup';
import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Accordion from 'react-bootstrap/Accordion';
import Dropdown from 'react-bootstrap/Dropdown';
import DropdownButton from 'react-bootstrap/DropdownButton';
import Alert from 'react-bootstrap/Alert';
import Badge from 'react-bootstrap/Badge';
import Stack from 'react-bootstrap/Stack';
import Spinner from 'react-bootstrap/Spinner';
import { GenericFetchJson } from './generic_components';
import { withRouter } from "./utils";


class ModelControlPanel extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            downloads: [],
            installedModels: []
        };

        this.intervalMilliSecs = 5000;
        this.intervalId = null;
        this.handleStartDownload = this.handleStartDownload.bind(this);
    }

    componentDidMount() {
        this.intervalId = setInterval(() => {
            this.syncDownloadsInProgress();
            this.syncInstalledModels();
        }, this.intervalMilliSecs);
    }

    componentWillUnmount() {
        clearInterval(this.intervalId);
    }

    syncDownloadsInProgress() {
        this.syncStateLists('/modelhub/downloads-in-progress/', "downloads");
    }

    syncInstalledModels() {
        this.syncStateLists('/modelhub/installed-models/', "installedModels");
    }

    syncStateLists(url, listKey) {
        fetch(url).then(response => response.json()).then(data => {
            let patch = {};
            patch[listKey] = data
            this.setState(patch);
        });

    }

    handleStartDownload(repoId, fileName) {
        console.log("starting download:", repoId, fileName);
        const url = '/modelhub/start-download/'
        let fetcher = new GenericFetchJson();
        fetcher.method = "POST";
        fetcher.body = {
            repo_id: repoId,
            file_name: fileName
        };

        fetcher.performFetch(url);
    }
    render() {
        let downloads = this.state.downloads;
        let downloadsInProgress = downloads.map((modelInfo, index) => 
            <ListGroup.Item variant="secondary">
                {`Installing a model: ${modelInfo.repo_id}/${modelInfo.file_name}... `}
                <Spinner animation="border" role="status">
                </Spinner>
            </ListGroup.Item>
        );
        return (
            <div>
                {downloadsInProgress.length > 0 && (
                    <ListGroup>{downloadsInProgress}</ListGroup>
                )}
                <HuggingfaceHubRepositoryViewer onStartDownload={this.handleStartDownload} />
            </div>
        );
    }
};


class HuggingfaceHubRepositoryViewer extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            searchTerm: "",
            foundItems: [],
            ggufFiles: [],
            selectedFileIndex: null, 
            detailLoading: false,
            searching: false,
            expandedIdx: ""
        };

        this.handleTermChange = this.handleTermChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleAccordionSelect = this.handleAccordionSelect.bind(this);
        this.handleFileItemClick = this.handleFileItemClick.bind(this);
    }

    handleTermChange(e) {
        this.setState({ searchTerm: e.target.value });
    }

    handleSubmit(e) {
        e.preventDefault();
        const url = `/modelhub/repos/?search=${this.state.searchTerm}`;

        this.setState({ searching: true });

        //todo: handle errors gracefully
        fetch(url).then(response => response.json()).then(foundItems => {
            this.setState({ foundItems });
        }).finally(() => {
            this.setState({ searching: false });
        });
    }

    handleAccordionSelect(eventKey) {
        console.log('event key:', eventKey);
        if (eventKey === null || eventKey === undefined) {
            return;
        }

        this.setState({ detailLoading: true, expandedIdx: eventKey, selectedFileIndex: null });

        let id = parseInt(eventKey);
        let repoId = this.state.foundItems[id].id;

        repoId = encodeURIComponent(repoId);
        const url = `/modelhub/repo-detail/?repo_id=${repoId}`;

        //todo: handle errors gracefully
        fetch(url).then(response => response.json()).then(ggufFiles => {
            this.setState({ ggufFiles });
        }).finally(() => {
            this.setState({ detailLoading: false });
        });
    }

    handleFileItemClick(fileIndex) {
        this.setState({ selectedFileIndex: fileIndex });
    }

    render() {
        function renderSize(size) {
            const KB = 1000
            const MB = KB * 1000;
            const GB = MB * 1000;

            let newSize;
            let units;
            if (size > GB) {
                newSize = size / GB;
                units = 'GB';
            } else if (size > MB) {
                newSize = size / MB;
                units = 'MB';
            } else if (size > KB) {
                newSize = size / KB;
                units = 'KB';
                
            } else {
                newSize = size;
                units = 'B';
            }

            return `${Math.round(newSize * 10) / 10} ${units}`;
        }


        let items = this.state.foundItems.map((item, index) => {
            let itemBody;
            if (this.state.detailLoading) {
                itemBody = <div>Please, wait...</div>;
            } else {
                let ggufItems = this.state.ggufFiles.map((fileInfo, fileIndex) => 
                    <Dropdown.Item key={fileIndex} eventKey={fileIndex} onClick={e => this.handleFileItemClick(fileIndex)}>
                        {`${fileInfo.path} (${renderSize(fileInfo.size)})`}
                    </Dropdown.Item>
                );

                let licenses = item.licenses.join(", ");
                let datasets = item.datasets.join(", ");
                let papers = item.papers.join(", ");
                let tags = item.tags.map((tag, tagIndex) => 
                    <Badge key={tagIndex} bg="success">{tag}</Badge>
                );

                let filePath = null;
                let fileSize = null;

                if (this.state.selectedFileIndex) {
                    filePath = this.state.ggufFiles[this.state.selectedFileIndex].path;
                    fileSize = this.state.ggufFiles[this.state.selectedFileIndex].size;
                }

                const handleStartDownload = e => {
                    this.props.onStartDownload(item.id, filePath);
                }

                itemBody = (
                    <div>
                        {licenses.length > 0 && <div>Licenses: {licenses}</div>}
                        {datasets.length > 0 && <div>Datasets: {datasets}</div>}
                        {papers.length > 0 && <div>Papers: {papers}</div>}
                        {tags.length > 0 && (
                            <Stack direction="horizontal" gap={2} style={{ 'overflow-x': 'auto' }}>
                                Tags: {tags}
                            </Stack>
                        )}
                        
                        <DropdownButton title="Select a file" variant="primary" className="mb-3 mt-3">
                            {ggufItems}
                        </DropdownButton>
                        {this.state.selectedFileIndex !== null && (
                            <div>
                                <div className="mb-3">
                                    <span>A model to be downloaded: </span>
                                    <span>{filePath} </span>
                                    <span>{`(${fileSize})`}</span>
                                </div>

                                <Alert variant="warning" className="mb-3">
                                    Be careful when downloading third-party models. Avoid downloads 
                                    from authors who you do not trust.
                                </Alert>
                                <Alert variant="warning" className="mb-3">
                                    Make sure you have enough disk space on LLM server to download a chosen model.
                                </Alert>
                                <Button variant="secondary" onClick={handleStartDownload}>Start download</Button>
                            </div>
                        )}
                    </div>
                );
            }
            return (
                <Accordion.Item key={index} eventKey={`${index}`}>
                    <Accordion.Header>
                        {item.id}        Likes: {item.likes} Downloads: {item.downloads}
                    </Accordion.Header>
                    <Accordion.Body>{itemBody}</Accordion.Body>
                </Accordion.Item>
            );
        });

        return (
            <div className="mt-3">
                <h4>Download open models from Hugging Face (HF)</h4>
                <Form onSubmit={this.handleSubmit}>
                <Row>
                    <Col xs={8} sm={4}>
                        <Form.Control 
                            placeholder="HF repository name"
                            name="search-term"
                            value={this.state.searchTerm}
                            onChange={this.handleTermChange} />
                    </Col>
                    <Col>
                        <Button variant="primary" type="submit">Search</Button>
                    </Col>
                </Row>
                </Form>
                {this.state.searching && <div>Searching repositories on Hugging Face Hub...</div>}
                {!this.state.searching && 
                    <Accordion
                        onSelect={this.handleAccordionSelect}
                        className="mt-3"
                    >{items}
                    </Accordion>}
            </div>
        );
    }
}


ModelControlPanel = withRouter(ModelControlPanel);

export {
    ModelControlPanel
}
