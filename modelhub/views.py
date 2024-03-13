from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


from huggingface_hub import HfApi, list_repo_tree


hf_api = HfApi()


def is_gguf(repo):
    return 'gguf' in map(str.lower, repo.tags)


def get_tag_values(tags, key):
    return [tag.split(':')[1]
            for tag in tags if tag.startswith(key)]


def get_repo_info(repo):
    licenses = get_tag_values(repo.tags, 'license')
    datasets = get_tag_values(repo.tags, 'dataset')
    arxiv_papers = get_tag_values(repo.tags, 'arxiv')

    prefixes = ['license', 'dataset', 'arxiv']
    other_tags = filter(lambda tag: not any(tag.startswith(p) for p in prefixes), repo.tags)

    return dict(id=repo.id, downloads=repo.downloads, likes=repo.likes, 
                licenses=licenses, datasets=datasets, papers=arxiv_papers, 
                tags=other_tags)


def get_file_info(repo_file):
    print('repo file', repo_file)
    return dict(path=repo_file.path, size=repo_file.size)


@api_view(['GET'])
def list_repositories(request):
    author = request.query_params.get('author')
    search = request.query_params.get('search')

    params = dict(limit=20, sort="downloads", direction=-1)

    if author:
        params["author"] = author
    
    if search:
        params["search"] = search
    
    it = hf_api.list_models(**params)

    repos = [get_repo_info(repo) for repo in it if is_gguf(repo)]
    return Response(repos)


@api_view(['GET'])
def list_gguf_files(request):
    repo_id = request.query_params.get('repo_id')

    if not repo_id:
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    files = list_repo_tree(repo_id)
    gguf_files = [get_file_info(repo_file) for repo_file in files 
                  if repo_file.path.lower().endswith('.gguf')]
    print(repo_id, '\n', gguf_files)
    return Response(gguf_files)
