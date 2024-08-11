import argparse
import os
import json
import sys

sys.path.insert(0, ".")
from llm_services.common import models_root, models_registry


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Adds a local GGUF model to the list of installed models"
    )

    parser.add_argument("model_id", type=str)
    parser.add_argument("model_path", type=str)
    parser.add_argument("--yes", action='store_true')
    args = parser.parse_args()

    source = args.model_path
    file_size = os.path.getsize(source)
    file_name = os.path.split(source)[-1]

    destination = os.path.join(models_root, file_name)

    if os.path.exists(models_root) and not args.yes:
        yesno = input(f"Writing file(s) to existing folder '{models_root}'. Continue? (y/n)")
        if yesno != "y":
            sys.exit(0)
    else:
        os.makedirs(models_root, exist_ok=True)

    if not os.path.exists(models_registry):
        registry = []
    else:
        with open(models_registry) as f:
            registry = json.loads(f.read())

    registry.append({
        'repo_id': args.model_id,
        'repo': {},
        'file_name': file_name,
        'size': file_size
    })

    with open(models_registry, 'w') as f:
        f.write(json.dumps(registry))
    print("Updated registry")
