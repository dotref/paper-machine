# Paper Machine

## Setup

Clone the repo, then follow the steps below.

### Set environment 

Rename `.env.template` to `.env`.

#### OpenAI config

In the `.env` file, fill in `OPENAI_API_KEY` and desired `OPENAI_API_MODEL`.

#### Embedding config

In the `.env` file, fill in desired Hugging Face embedding model in `EMBEDDING_MODEL` and `EMBEDDING_MODEL_REVISION`.

To toggle embedding creation on (off by default), change the `EMBED_ON` constant to `true` for "on" and `false` for "off".

#### Auth config

Generate a secret key, one way is to use the command below:

```
openssl rand -hex 32
```

Copy the output and fill in `AUTH_SECRET` in the `.env` file.

### To bring up the application (frontend, backend, and DB) in the docker compose file:
Install Docker (and/or Docker Desktop).

In the root directory, run the command below. Reload is on, so saved changes to the backend will automatically be applied (no need to rebuild)
```
docker-compose up --build
```

### To use the app

Visit `localhost:3000` in your web browser.

### To access MinIO console

Visit `localhost:9000` in your web browser and login using the credentials `minio_user` and `minio_password`.

### To access FastAPI console

Visit `localhost:5000/docs` in your web browser. You may interact with the API endpoints in the console.

### To access pgAdmin 4 console

Visit `localhost:8888` in your web browser and login using the credentials `user-name@domain-name.com` and `strong-password`.

Add a new server with name `pgvector` and address `pgvector:5432` and use the credentials `testuser` and `testpwd`.
