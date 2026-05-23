# Dev

Start the full development stack: FastAPI backend and React frontend.

## Steps

1. Ensure dependencies are installed:
```bash
uv sync
cd frontend && npm install && cd ..
```

2. Start the stack with Docker Compose (preferred — runs backend + frontend together):
```bash
docker compose up --build
```

OR start services individually for faster iteration:

**Backend** (FastAPI on port 8000):
```bash
uv run uvicorn api.main:app --reload --port 8000
```

**Frontend** (Vite dev server on port 5173):
```bash
cd frontend && npm run dev
```

3. Open http://localhost:5173 for the React UI and http://localhost:8000/docs for the FastAPI Swagger UI.

Report: confirm both services started successfully and list any errors.
