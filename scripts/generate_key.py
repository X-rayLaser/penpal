import os
from django.core.management.utils import get_random_secret_key

def generate_key():
    secret_path = os.environ.get('SECRET_KEY_PATH')
    if not secret_path:
        print(f"Environment variable 'SECRET_KEY_PATH' is not set. Quitting.")
        return
    
    with open(secret_path) as f:
        content = f.read()
    
    if content:
        yes_no = input(f'This will overwrite non-empty file "{secret_path}". Continue (y/n)?')
    else:
        yes_no = 'y'
    
    if yes_no != 'y':
        print("Operation cancelled by user")
        return

    key = get_random_secret_key()
    with open(secret_path, 'w') as f:
        f.write(key)


if __name__ == '__main__':
    generate_key()
