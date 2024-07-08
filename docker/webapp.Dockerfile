FROM python:3.10

RUN groupadd -r user && useradd -m -r -g user user

ENV PATH="$PATH:/home/user/.local/bin" SECRET_KEY_PATH="/secrets/secret_key.txt"

COPY ./requirements.txt /requirements.txt

USER user
RUN pip install -r /requirements.txt

USER root

COPY ./ /app

RUN mkdir /data && chown -R user: /data \
    && mkdir /secrets && touch /secrets/secret_key.txt && chown -R user: /secrets \
    && chown -R user: /app

USER user

WORKDIR /app

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash && . ~/.profile && nvm install 20

RUN . ~/.profile && npm install && npx webpack

# creating directories in advance will allow to create volumes with mount points at their place
# with correct ownership (will by ownbed by user)
RUN mkdir -p /app/frontend/public

SHELL ["/bin/bash", "-l", "-c"]

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]