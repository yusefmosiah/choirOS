# ChoirOS API

FastAPI backend for parsing URLs and files.

## Setup

```bash
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

## Endpoints

- `POST /api/parse/url` - Parse URL (YouTube, web page)
- `POST /api/parse/upload` - Parse uploaded file
- `GET /api/artifacts` - List artifacts
- `GET /api/artifacts/{id}` - Get artifact
