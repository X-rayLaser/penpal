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
import Card from 'react-bootstrap/Card';
import { renderSize } from './utils';
import { GenericFetchJson } from './generic_components';
import { withRouter } from "./utils";


class ModelControlPanel extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            downloads: [],
            installedModels: [],
            failedDownloads: [],
            initialSyncDone: false
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
            let downloadsWithStatus = downloads.map(download => ({
                ...download,
                elapsed: calculateElapsedSeconds(download.started_at)
            }));

            this.setState({ downloadsWithStatus }, () => {
                fetcher.performFetch(urlListModels).then(installedModels => {
                    
                    let cleanedDownloads = downloadsWithStatus.filter(download => {
                        let duplicates = installedModels.filter(model => 
                            download.repo_id === model.repo_id && 
                            download.file_name === model.file_name
                        );
                        return duplicates.length === 0;
                    });

                    this.setState({ 
                        downloads: cleanedDownloads,
                        installedModels,
                        initialSyncDone: true 
                    });
                });
            });
        });

        this.syncFailedDownloads();
    }

    syncFailedDownloads() {
        this.syncStateLists('/modelhub/failed-downloads/', "failedDownloads");
    }

    syncStateLists(url, listKey) {
        let fetcher = new GenericFetchJson();

        fetcher.performFetch(url).then(data => {
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
                let elapsed = calculateElapsedSeconds(status.started_at);
                let statusWithTiming = {...status, elapsed};

                if (status.finished && status.errors.length === 0) {
                    successfulDownloads.push({
                        repo_id: status.repo_id,
                        repo: status.repo,
                        file_name: status.file_name,
                        size: status.size
                    });
                } else if (status.finished) {
                    failedDownloads.push(status);
                } else {
                    inProgress.push(statusWithTiming);
                }
            });

            this.setState({
                downloads: inProgress,
                installedModels: [...this.state.installedModels, ...successfulDownloads],
                failedDownloads: [...this.state.failedDownloads, ...failedDownloads],
            })
        });
    }

    handleStartDownload(repo, fileName, fileSize) {    
        this.setState(prevState => ({
            downloads: [...prevState.downloads, {
                repo,
                repo_id: repo.id,
                file_name: fileName,
                size: fileSize,
                started_at: (new Date()) / 1000
            }]
        }));
    }
    render() {
        let downloads = this.state.downloads;
        let downloadsInProgress = downloads.map((modelInfo, index) => 
            <Card key={index} bg="secondary" text="light">
                <Card.Body>
                    <Card.Title>
                        {`Installing a model: ${modelInfo.repo_id}--${modelInfo.file_name}... `}
                        <Spinner animation="border" role="status">
                        </Spinner>
                    </Card.Title>
                    {modelInfo.elapsed && (
                        <Card.Subtitle>Elapsed time: {formatTimeElapsed(modelInfo.elapsed)}</Card.Subtitle>
                    )}
                </Card.Body>
            </Card>
        );

        let failedDownloads = this.state.failedDownloads.map((modelInfo, index) => 
            <Card key={index} variant="secondary" bg="danger" text="white" className="mb-3">
                <Card.Body>
                    <Card.Title>Download failed for {modelInfo.repo_id}--{modelInfo.file_name}</Card.Title>
                    {modelInfo.errors.map((error, errorId) => 
                        <Card.Text key={errorId}>{error}</Card.Text>
                    )}
                </Card.Body>
            </Card>
        );

        let installedModels = this.state.installedModels.map((modelInfo, index) =>
            <Col key={index}>
            <Card className="mb-3 me-3"
                bg='light' text='dark'>
                <Card.Body>
                    <div style={{ minHeight: '95px'}}>
                        <Card.Title>{modelInfo.repo_id}</Card.Title>
                        <Card.Subtitle className="mb-2 text-muted">{modelInfo.file_name}</Card.Subtitle>
                    </div>

                    <Card.Text>
                        <JoinedItemText name="Licenses" items={modelInfo.repo.licenses} separator=", " />
                    </Card.Text>

                    <Card.Text>
                        <PapersUrlsInline papers={modelInfo.repo.papers} />
                    </Card.Text>

                    <Card.Text>
                        <span>Size on disk: {renderSize(modelInfo.size)}</span>
                    </Card.Text>

                    <Button as='a' href={`https://huggingface.co/${modelInfo.repo_id}`} target='_blank'>
                        View on Hugging Face
                    </Button>
                </Card.Body>
            </Card>
            </Col>
        );

        if (!this.state.initialSyncDone) {
            return (
                <div>Loading page... 
                    <Spinner animation="border" role="status">
                        <span className="visually-hidden">Loading...</span>
                    </Spinner>
              </div>
            );
        }

        return (
            <div>
                <div>
                    {failedDownloads.length > 0 && (
                        <div className="mt-3">{failedDownloads}</div>
                    )}
                    {downloadsInProgress.length > 0 && (
                        <div className="mt-3">{downloadsInProgress}</div>
                    )}
                </div>

                {installedModels.length > 0 && (
                    <div className="mt-3">
                        <h4>Installed models</h4>
                        <Row xs={1} md={3} className="g-2">{installedModels}</Row>
                    </div>
                )}
                <HuggingfaceHubRepositoryViewer 
                    onStartDownload={this.handleStartDownload}
                    downloads={this.state.downloads}
                    installedModels={this.state.installedModels}
                    />
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
            pendingDownloads: [],
            launchFailures: [],
            selectedFileIndex: null, 
            detailLoading: false,
            searching: false,
            expandedIdx: ""
        };

        this.handleTermChange = this.handleTermChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleAccordionSelect = this.handleAccordionSelect.bind(this);
        this.handleFileItemClick = this.handleFileItemClick.bind(this);
        this.handleStartDownload = this.handleStartDownload.bind(this);
    }

    handleTermChange(e) {
        this.setState({ searchTerm: e.target.value });
    }

    handleSubmit(e) {
        e.preventDefault();
        const url = `/modelhub/repos/?search=${this.state.searchTerm}`;

        this.setState({ searching: true });

        //todo: handle errors gracefully
        let fetcher = new GenericFetchJson();

        fetcher.performFetch(url).then(foundItems => {
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
        let fetcher = new GenericFetchJson();
        
        fetcher.performFetch(url).then(ggufFiles => {
            this.setState({ ggufFiles });
        }).finally(() => {
            this.setState({ detailLoading: false });
        });
    }

    handleFileItemClick(fileIndex) {
        this.setState({ selectedFileIndex: fileIndex });
    }

    handleStartDownload(repo, fileName, fileSize) {
        console.log("starting download:", repo, fileName, fileSize);
        const url = '/modelhub/start-download/';

        let download = {
            repo,
            repo_id: repo.id,
            file_name: fileName,
            size: fileSize
        };

        let fetcher = new GenericFetchJson();
        fetcher.method = "POST";
        fetcher.body = download;
        fetcher.messages["5xx"] = "Failed to start download. Check that LLM server is available."
    
        function removeDownload(arr) {
            return arr.filter(d => 
                !(d.repo_id === repo.id && d.file_name === fileName)
            );
        }

        this.setState(prevState => {
            let pendingDownloads = removeDownload(prevState.pendingDownloads);
            let launchFailures = removeDownload(prevState.launchFailures);
            pendingDownloads.push(download);
            
            return {
                pendingDownloads,
                launchFailures
            };
        });

        fetcher.performFetch(url).then(obj => {
            this.props.onStartDownload(repo, fileName, fileSize);

            this.setState(prevState => {
                let pendingDownloads = removeDownload(prevState.pendingDownloads);
                let launchFailures = removeDownload(prevState.launchFailures);

                return {
                    pendingDownloads,
                    launchFailures
                };

            });
        }).catch(errorObject => {
            this.setState(prevState => {
                let failure = {
                    ...download,
                    error: errorObject.error
                };

                let pendingDownloads = removeDownload(prevState.pendingDownloads);
                let launchFailures = removeDownload(prevState.launchFailures);
                launchFailures.push(failure);

                console.log("state:", pendingDownloads, launchFailures);

                return {
                    pendingDownloads,
                    launchFailures
                };
            });
            
            console.error(errorObject);
        });
    }

    render() {
        let items = this.state.foundItems.map((item, index) => {
            let itemBody;
            if (this.state.detailLoading) {
                itemBody = <div>Please, wait...</div>;
            } else {
                itemBody = <RepositoryDetail 
                                ggufFiles={this.state.ggufFiles}
                                installedModels={this.props.installedModels}
                                downloads={this.props.downloads}
                                pendingDownloads={this.state.pendingDownloads}
                                launchFailures={this.state.launchFailures}
                                onFileItemClick={this.handleFileItemClick}
                                selectedFileIndex={this.state.selectedFileIndex}
                                onStartDownload={this.handleStartDownload}
                                repo={item} />;
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
};


function RepositoryDetail(props) {
    let repo = props.repo;

    let ggufItems = props.ggufFiles.map((fileInfo, fileIndex) => {
        let isInstalled = containsModel(props.installedModels, repo.id, fileInfo.path);
        let isInProgress = containsModel(props.downloads, repo.id, fileInfo.path);

        return (
            <Dropdown.Item key={fileIndex} eventKey={fileIndex} onClick={e => props.onFileItemClick(fileIndex)}>
                {`${fileInfo.path} (${renderSize(fileInfo.size)})`}
                {isInstalled && <Badge bg="success">Installed</Badge>}
                {isInProgress && <Badge>Installing...</Badge>}
            </Dropdown.Item>
        );
    });

    let filePath = null;
    let fileSize = null;

    if (props.selectedFileIndex !== null) {
        filePath = props.ggufFiles[props.selectedFileIndex].path;
        fileSize = props.ggufFiles[props.selectedFileIndex].size;
    }

    const handleStartDownload = e => {
        props.onStartDownload(repo, filePath, fileSize);
    }

    let isInstalled = containsModel(props.installedModels, repo.id, filePath);
    let isInProgress = containsModel(props.downloads, repo.id, filePath);
    let isPending = containsModel(props.pendingDownloads, repo.id, filePath);

    let failures = props.launchFailures.filter(item => item.repo_id === repo.id && item.file_name === filePath);
    let launchError = (failures.length > 0 && failures[0].error) || null;

    return (
        <div>
            <RepositoryMetadata repo={repo} />
            
            <DropdownButton title="Select a file" variant="primary" className="mb-3 mt-3">
                {ggufItems}
            </DropdownButton>

            <ModelDownload filePath={filePath} fileSize={fileSize} installed={isInstalled}
                inProgress={isInProgress} pending={isPending} launchError={launchError}
                onStartDownload={e => handleStartDownload(e)} />
        </div>
    );
}


function RepositoryMetadata(props) {
    let licenses = props.repo.licenses.join(", ");
    let datasets = props.repo.datasets.join(", ");
    let papers = props.repo.papers.map((paperId, index) => 
        <div key={index}>
            <ArxivLink paperId={paperId} />
        </div>
    );
    let tags = props.repo.tags.map((tag, tagIndex) => 
        <Badge key={tagIndex} bg="success">{tag}</Badge>
    );
    return (
        <div>
            {licenses.length > 0 && <div>Licenses: {licenses}</div>}
            {datasets.length > 0 && <div>Datasets: {datasets}</div>}
            {papers.length > 0 && <div>Papers: {papers}</div>}
            {tags.length > 0 && (
                <Stack direction="horizontal" gap={2} style={{ 'overflowX': 'auto' }}>
                    Tags: {tags}
                </Stack>
            )}
        </div>
    );
}


function JoinedItemText(props) {
    let items = props.items.join(props.separator);

    return (
        <span>
            {`${props.name}: ${items}`}
        </span>
    );
}


function PapersUrlsInline(props) {
    let urls = props.papers.map((paperId, index) => 
        <ArxivLink key={index} paperId={paperId} />
    );
    return (
        <span>Papers: {urls}</span>
    );
}


function ArxivLink(props) {
    let url = `https://arxiv.org/abs/${props.paperId}`;
        
    return (
        <Card.Link href={url} target='_blank'>{url}</Card.Link>
    );
}


function ModelDownload(props) {
    let fileSize = props.fileSize && renderSize(props.fileSize);
    return (
        <div>
            {props.filePath !== null && props.installed && (
                <Alert variant="success" className="mb-3">
                    {`Model ${props.filePath} is installed`}
                </Alert>
            )}
            {props.filePath !== null && props.inProgress && (
                <Alert variant="primary" className="mb-3">
                    {`Model ${props.filePath} is installing`}
                    <Spinner animation="border" role="status" size="sm"></Spinner>
                </Alert>
            )}

            {props.filePath !== null && props.launchError && (
                <Alert variant="danger" className="mb-3">{props.launchError}</Alert>
            )}

            {props.filePath !== null && !props.installed && !props.inProgress && (
                <div>
                    <div className="mb-3">
                        <span>A model to be downloaded: </span>
                        <span>{props.filePath} </span>
                        <span>{`(${fileSize})`}</span>
                    </div>

                    <Alert variant="warning" className="mb-3">
                        Be careful when downloading third-party models. Avoid downloads 
                        from authors who you do not trust.
                    </Alert>
                    <Alert variant="warning" className="mb-3">
                        Make sure you have enough disk space on LLM server to download a chosen model.
                    </Alert>
                    <Button variant="secondary" onClick={props.onStartDownload} disabled={props.pending}>
                        Start download
                    </Button>
                </div>
            )}
        </div>
    );
}


function containsModel(models, repo_id, file_name) {
    let matches = models.filter(model => 
        model.repo_id === repo_id && model.file_name === file_name
    );

    return matches.length > 0;
}


function calculateElapsedSeconds(t0) {
    let now = (new Date()) / 1000;
    return Math.round(now - t0);
}


function formatTimeElapsed(numSeconds) {
    let date = new Date(0);
    date.setSeconds(numSeconds);
    let indexStart = 11;
    let indexEnd = 19;
    return date.toISOString().substring(indexStart, indexEnd);
}


ModelControlPanel = withRouter(ModelControlPanel);

export {
    ModelControlPanel
}
