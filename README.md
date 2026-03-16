# eMasterHub Server

FastAPI backend for eMasterHub.

## Prerequisites

- **Python** ≥ 3.12
- **uv** (recommended) — [install](https://docs.astral.sh/uv/getting-started/installation/):

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

## Setup & run

1. **Install dependencies** (from project root):

   ```bash
   uv sync
   ```

2. **Run the dev server**:

   ```bash
   uv run uvicorn main:app --reload
   ```

   Server: `http://127.0.0.1:8000`  
   Docs: `http://127.0.0.1:8000/docs`
