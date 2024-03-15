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
            installedModels: [],
            failedDownloads: []
        };

        this.intervalMilliSecs = 5000;
        this.intervalId = null;
        this.handleStartDownload = this.handleStartDownload.bind(this);
    }

    componentDidMount() {
        this.runInitialSync();

        this.intervalId = setInterval(() => {
            this.refreshDownloads();
        }, this.intervalMilliSecs);
    }

    componentWillUnmount() {
        clearInterval(this.intervalId);
    }

    runInitialSync() {
        const urlInProgress = '/modelhub/downloads-in-progress/';
        const urlListModels = '/modelhub/installed-models/';

        let fetcher = new GenericFetchJson();
        
        fetcher.performFetch(urlInProgress).then(downloads => {
            this.setState({ downloads }, () => {
                fetcher.performFetch(urlListModels).then(installedModels => {
                    
                    let cleanedDownloads = downloads.filter(download => {
                        let duplicates = installedModels.filter(model => 
                            download.repo_id === model.repo_id && 
                            download.file_name === model.file_name
                        );
                        return duplicates.length === 0;
                    });

                    this.setState({ downloads: cleanedDownloads, installedModels});
                });
            });
        });

        this.syncFailedDownloads();
    }

    syncFailedDownloads() {
        //this.syncStateLists('/modelhub/failed-downloads/', "failedDownloads");
    }

    syncStateLists(url, listKey) {
        fetch(url).then(response => response.json()).then(data => {
            let patch = {};
            patch[listKey] = data
            this.setState(patch);
        });

    }

    refreshDownloads() {
        let fetcher = new GenericFetchJson();

        let statusPromises = this.state.downloads.map(download => {
            let repo_id = encodeURIComponent(download.repo_id);
            let file_name = encodeURIComponent(download.file_name);
            let url = `/modelhub/get-download-status/?repo_id=${repo_id}&file_name=${file_name}`;
            return fetcher.performFetch(url);
        });
        
        Promise.all(statusPromises).then(downloadStatuses => {
            let successfulDownloads = [];
            let failedDownloads = [];
            let inProgress = [];

            this.state.downloads.forEach((download, index) => {
                let status = downloadStatuses[index];
                if (status.finished && status.errors.length === 0) {
                    successfulDownloads.push({
                        repo_id: status.repo_id,
                        file_name: status.file_name
                    });
                } else if (status.finished) {
                    failedDownloads.push(status);
                } else {
                    inProgress.push(status);
                }
            });

            this.setState({
                downloads: inProgress,
                installedModels: [...this.state.installedModels, ...successfulDownloads],
                failedDownloads,
            })
        });
    }

    handleStartDownload(repoId, fileName) {
        console.log("starting download:", repoId, fileName);
        const url = '/modelhub/start-download/';

        let download = {
            repo_id: repoId,
            file_name: fileName
        };

        let fetcher = new GenericFetchJson();
        fetcher.method = "POST";
        fetcher.body = download;
    
        this.setState(prevState => ({
            downloads: [...prevState.downloads, download]
        }));
        fetcher.performFetch(url);
    }
    render() {
        let downloads = this.state.downloads;
        let downloadsInProgress = downloads.map((modelInfo, index) => 
            <ListGroup.Item key={index} variant="secondary">
                {`Installing a model: ${modelInfo.repo_id}--${modelInfo.file_name}... `}
                <Spinner animation="border" role="status">
                </Spinner>
            </ListGroup.Item>
        );

        let installedModels = this.state.installedModels.map((modelInfo, index) =>
            <ListGroup.Item key={index} variant="success">
                {`Repository: ${modelInfo.repo_id} Path: ${modelInfo.file_name}... `}
            </ListGroup.Item>
        );

        let reservedModels = [...this.state.downloads, ...this.state.installedModels];
        return (
            <div>
                {downloadsInProgress.length > 0 && (
                    <ListGroup className="mt-3">{downloadsInProgress}</ListGroup>
                )}

                {installedModels.length > 0 && (
                    <div className="mt-3">
                        <h4>Installed models</h4>
                        <ListGroup>{installedModels}</ListGroup>
                    </div>
                )}
                <HuggingfaceHubRepositoryViewer 
                    onStartDownload={this.handleStartDownload}
                    reservedModels={reservedModels} />
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

                if (this.state.selectedFileIndex !== null) {
                    filePath = this.state.ggufFiles[this.state.selectedFileIndex].path;
                    fileSize = renderSize(this.state.ggufFiles[this.state.selectedFileIndex].size);
                }

                const handleStartDownload = e => {
                    this.props.onStartDownload(item.id, filePath);
                }

                let disableDownload = false;

                this.props.reservedModels.forEach(d => {
                    if (d.repo_id === item.id && d.file_name === filePath) {
                        disableDownload = true;
                    }
                });

                itemBody = (
                    <div>
                        {licenses.length > 0 && <div>Licenses: {licenses}</div>}
                        {datasets.length > 0 && <div>Datasets: {datasets}</div>}
                        {papers.length > 0 && <div>Papers: {papers}</div>}
                        {tags.length > 0 && (
                            <Stack direction="horizontal" gap={2} style={{ 'overflowX': 'auto' }}>
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
                                <Button variant="secondary" onClick={handleStartDownload} disabled={disableDownload}>
                                    Start download    
                                </Button>
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
