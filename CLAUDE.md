# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

مستشار العقود (Contract Consultant) — an Arabic-language agent that connects to Google Drive, reads construction contracts (PDF/DOCX/Google Docs), and answers questions strictly from document evidence with citation-lock (page + clause citations, confidence-gated answers). Planned features beyond Q&A: risk scanning, contract comparison, cross-document smart search, and a claims-entitlement assistant. Contracts are in English (FIDIC/construction style); the UI/chat/answers are Arabic + RTL, but evidence quotes stay in the original English.

Current status: Phase 0 (infra) and Phase 1 (Drive ingestion pipeline) are built. RAG/citation-lock QA, the chat frontend, and risk/compare/search/claims features are not yet implemented (see README.md "حالة المشروع" for the phase breakdown).

## Critical environment constraint

**This project only runs inside GitHub Codespaces.** The developer's local Windows machine cannot run Docker Desktop (admin-restricted), so there is no local dev path — everything (Next.js, FastAPI, Postgres, ChromaDB, Redis) runs via `.devcontainer/devcontainer.json` + `docker-compose.yml` inside the cloud container. Do not suggest `docker compose up` from a local host shell as a primary workflow; assume the work happens inside an already-running Codespace terminal at `/workspace`.

Within the Codespace, the editor/terminal attaches to the `backend` service container (python:3.11-slim based), not the outer VM. That container has Python/pip but **no `git` and no `docker` CLI** by default — `git pull` and any `docker compose ...` command that needs to rebuild/recreate containers must run from a context that has those tools (e.g. install `git` via apt ad hoc, or trigger a rebuild through the Codespaces UI/CLI rather than from inside this container).

## Commands

All commands below run inside the Codespace, from `/workspace`.

```bash
# Apply DB schema (Postgres, via Alembic)
cd backend && alembic upgrade head

# Run the Drive ingestion pipeline manually (list -> parse -> chunk -> embed -> store)
cd backend && python -m app.ingestion.cli

# Or trigger ingestion via the API instead of the CLI
curl -X POST localhost:8000/api/ingest/run
curl localhost:8000/api/ingest/status

# Backend health check
curl localhost:8000/api/health

# Frontend dev server
cd frontend && npm run dev      # next dev -p 3000
cd frontend && npm run build
cd frontend && npm run lint
```

No backend test suite or linter is configured yet. There is no Alembic autogenerate workflow established beyond the single `0001_initial_schema` migration — write new migrations by hand following that file's style.

## Architecture

```
Next.js (App Router, TS, Tailwind, RTL)
        |  REST/JSON
        v
FastAPI (Python) backend
   |-- Drive ingestion (Drive API v3 + Sheets API, service-account auth)
   |-- Parsing: PyMuPDF/pdfplumber/Tesseract OCR (PDF), python-docx (DOCX), Drive export (GDocs)
   |-- Clause-aware chunker
   |-- Embeddings (local sentence-transformers, multilingual) -> ChromaDB
   |-- Postgres (SQLAlchemy + Alembic) -- registry, clauses, chat history, risk/compare cache
   |-- Redis -- reserved for rate limiting (not yet wired up)
   |-- (planned) RAG retrieval + OpenRouter LLM calls, citation-lock confidence scorer
   |-- (planned) Risk scanner / Compare / Smart search / Claims assistant
```

5 docker-compose services: `frontend` (:3000), `backend` (:8000), `postgres` (:5432), `chromadb` (:8001 externally, :8000 internally), `redis` (:6379).

### Google Drive access — service account, not OAuth

The backend authenticates to Drive/Sheets as a **Google Cloud service account** (`app/drive/client.py`), not via interactive OAuth — there's no browser flow, refresh token, or NextAuth Drive scope involved on the backend side. The key comes from either `GOOGLE_SERVICE_ACCOUNT_JSON` (raw JSON content, used in Codespaces via a Codespaces secret) or `GOOGLE_SERVICE_ACCOUNT_FILE` (a local file path, gitignored under `backend/secrets/`) — JSON content takes precedence if both are set. For the service account to see anything, the user must share the target Drive folders with the service account's `client_email` as Viewer. `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`NEXTAUTH_*` exist in config only for a possible future interactive frontend login and are currently unused.

### Ingestion pipeline (`backend/app/ingestion/pipeline.py`)

`run_ingestion(folder_id)` recursively lists Drive files, and per file: parses pages -> clause-splits -> embeds -> upserts into Chroma -> writes `Contract`/`Clause` rows in Postgres. It's incremental and idempotent: a file is skipped if its `drive_modified_time` hasn't advanced since `last_ingested_at`; re-ingesting a changed file deletes its old Chroma chunks (`chroma_store.delete_by_contract`) and `Clause` rows before re-inserting. Chunk IDs are `"{contract_id}:{chunk_index}"`, shared between Chroma and `Clause.chroma_chunk_id` — this is the join key between the vector store and the relational registry, and the invariant to preserve when touching either side. All contracts share a single Chroma collection (`contract_clauses`) rather than one per contract, since cross-document Smart Search (planned) needs to query the whole corpus without a contract filter.

### PDF parsing fallback cascade (`backend/app/parsing/pdf_parser.py`)

Three-tier fallback per page, each tier only invoked when the previous one returns under `MIN_CHARS_BEFORE_FALLBACK` (20 chars): PyMuPDF text extraction -> pdfplumber (better for table-heavy pages) -> Tesseract OCR via PyMuPDF's `get_textpage_ocr` (`eng+ara` languages, 300 DPI). The OCR tier exists because the user's real contracts are scanned PDF images with no text layer at all — expect OCR to be hit routinely, not as a rare edge case, and expect it to be slow (model/page dependent).

### Clause-aware chunking (`backend/app/chunking/clause_splitter.py`)

Chunks are split on clause-number boundaries (regex cascade: numbered headers like `14.2 Advance Payment` -> `Clause`/`Article` keyword form -> ALL-CAPS heading fallback for non-FIDIC docs), not fixed-token windows — every chunk is already a citable unit (clause number + page number) by construction, which is what the (planned) citation-lock QA depends on. Oversized chunks (>1800 chars) are split further on sub-clause boundaries (e.g. `14.2.1`, `14.2.2`) rather than mid-sentence, keeping the parent clause number attached.

### Embeddings (`backend/app/embeddings/embedder.py`)

Local, free, multilingual via `sentence-transformers` (`intfloat/multilingual-e5-small`) — required because Arabic questions must retrieve against English clause text. Follows the e5 model's documented `"query: "` / `"passage: "` prefix convention for asymmetric retrieval; don't drop these prefixes when adding new embedding call sites.

### ChromaDB version pinning

`chromadb` (backend) and the `chromadb/chroma` server image (docker-compose) are deliberately pinned to **0.4.24** (the older v1 HTTP API), not `latest`/0.5.x. Newer 0.5.x client/server combinations hit a known `KeyError: '_type'` bug in `CollectionConfigurationInternal.from_json` when creating a collection via the v2 API with simple `metadata={"hnsw:space": "cosine"}` (no explicit `configuration`). Keep client and server versions identical when touching either.

### Database models (`backend/app/db/models.py`)

`Contract` (1) -> `Clause` (many), plus `ChatMessage`, `RiskResult`, `CompareResult` — the latter three are schema-only placeholders for the not-yet-built RAG/risk/compare features; their `confidence`/`clause_number`/`page_number` fields anticipate the citation-lock pattern described in the README's planned Phase 2 (confidence bands: >0.90 high, 0.70-0.90 warn, 0.50-0.70 red warning, <0.50 refuse with "no supporting evidence").

## Secrets

Real secret values live in **Codespaces secrets** (`GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_ROOT_FOLDER_ID`, `GOOGLE_ARCHIVING_MATRIX_FILE_ID`, `OPENROUTER_API_KEY`), injected as env vars and substituted into `docker-compose.yml` via `${VAR:-}` — there is no committed `.env`, and Codespaces secrets only take effect on *newly created* codespaces, not existing ones (a secret added after a codespace exists requires deleting and recreating it, or manually exporting it into the running shell). `.env.example` documents the same variables for the local-file fallback path (`GOOGLE_SERVICE_ACCOUNT_FILE` + a real `.env`), which is only relevant outside Codespaces.
