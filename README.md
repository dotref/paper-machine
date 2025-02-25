# Paper Machine

## Setup

Clone the repo, then follow the steps below.

### To bring up the services (Database and Backend) in the docker compose file.
Naviagate to the `backend` directory and run the command below. Reload is on, so saved changes to the backend will automatically be applied (no need to rebuild)
```
docker-compose up --build
```

### To access MinIO console

Visit `localhost:9000` in your web browser and login using the credentials `minio_user` and `minio_password`.

### To access FastAPI console

Visit `localhost:5000/docs` in your web browser. You may interact with the API endpoints in the console.

### To bring up the frontend
NOTE: frontend is not integrated with the backend at this time.

Open another terminal, navigate to the `frontend` directory, and run the commands below.

```
npm i
```
npm run dev
```
