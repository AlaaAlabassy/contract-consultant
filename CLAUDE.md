# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- ════════════════════════════════════════════════════════════════════════
     SESSION RESUME — استئناف الجلسة (آخر تحديث: 2026-06-23 ليلاً)
     احذف هذا القسم بعد اكتمال التحقق الحي وعودة المشروع لوضعه الطبيعي.
     ════════════════════════════════════════════════════════════════════════ -->
## ⏸️ نقطة الاستئناف (اقرأ هذا أولاً)

**أين توقّفنا:** كل كود الواجهة الخلفية والأمامية (QA + فحص المخاطر + واجهة المحادثة RTL) مبنيٌّ ومُختبَر (54/54 اختبار وحدة ناجح) ومحفوظٌ ومدفوعٌ بالكامل إلى `origin/main` (شجرة العمل نظيفة، `0 0` ahead/behind). كنا في منتصف **أول تحقّق حيّ من طرف إلى طرف** داخل Codespace.

**ما تم التحقق منه حيّاً بنجاح هذه الجلسة:**
- `numpy 1.26.4` (إصلاح تعارض chromadb 0.4.24 مع NumPy 2.0 — commit `f0bbdf2`)، `alembic upgrade head` نجح، و`/api/health` يُرجع `{'status': 'ok'}`.
- الأسرار موجودة (Drive folder + service-account JSON)، و`POST /api/ingest/run` بدأ الاستيعاب فعلياً على مجلد Drive حقيقي (folder_id `1X5FW44bFPs-tzrOzToCAYwKZ_xipxLW_`، ~30 عقداً أغلبها ممسوح ضوئياً).

**الحالة وقت التوقّف:** الاستيعاب كان لا يزال `running` (عملية python بـ~90% CPU، طبيعي بسبب OCR على 30 عقداً ممسوحاً — متوقّع أن يطول ساعة+). العدّاد في DB يبقى 0 حتى النهاية لأن `run_ingestion` يلتزم (commit) مرّة واحدة فقط بعد كل الملفات.

**الـ Codespace النشط:** `fantastic-parakeet-5gqq9664vx7627w6g` (machine: standardLinux32gb). تُرك يعمل ليلاً لإكمال الاستيعاب.

**⚠️ قيد بيئي مهم اكتُشف:** SSH عبر `gh codespace ssh` و port-forward **غير موثوقَين** من شبكة المستخدم (تعليق/Connection refused متقطّع — حجب نفق dev tunnels). القناة الموثوقة الوحيدة هي **طرفية المتصفح** (VS Code Web). التقسيم: المستخدم ينفّذ الأوامر في طرفية المتصفح ويلصق الناتج؛ المساعد يحلّل ويوجّه. طرفية المتصفح الافتراضية تكون **داخل حاوية backend** (فيها python/pip/alembic/uvicorn/httpx، وبلا git/docker/curl).

**الخطوات التالية عند الاستئناف (بالترتيب):**
1. في طرفية المتصفح للـ Codespace، افحص حالة الاستيعاب:
   `python -c "import httpx, json; print(json.dumps(httpx.get('http://localhost:8000/api/ingest/status', timeout=30).json(), ensure_ascii=False, indent=2))"`
2. إن لم تكتمل بعد، انتظر دون إزعاج الخادم (كل استعلام يزاحم OCR على المعالج). إن `error`، اعرض الرسالة.
3. عند `done`: راجع ملخّص `ingested/skipped/failed`، ثم نفّذ **التحقق النهائي**:
   - سؤال QA حقيقي: `POST /api/qa/ask` بسؤال عربي عن بند فعلي (مثلاً عن الدفعة المقدمة أو غرامات التأخير) — تأكّد من `answer_ar` + اقتباس إنجليزي حرفي + `confidence_label`.
   - فحص مخاطر: `POST /api/risk/scan` بـ `{"contract_id": <id>}`، ثم `GET /api/risk/scan/status?contract_id=<id>` حتى `done`، ثم `GET /api/risk/<id>` لعرض النتائج.
4. (تحسين معماري مؤجَّل، ليس عائقاً): الاستيعاب يعمل كـ `BackgroundTask` داخل عملية الخادم ويُشبع المعالج فيبطّئ بقية الطلبات؛ والالتزام مرّة واحدة في النهاية يفقد التقدّم الجزئي عند أي انهيار. يُفضَّل لاحقاً نقله لعامل منفصل والالتزام بعد كل عقد.

<!-- ════════════════ نهاية قسم الاستئناف ════════════════ -->

## Project

مستشار العقود (Contract Consultant) — an Arabic-language agent that connects to Google Drive, reads construction contracts (PDF/DOCX/Google Docs), and answers questions strictly from document evidence with citation-lock (page + clause citations, confidence-gated answers). Planned features beyond Q&A: risk scanning, contract comparison, cross-document smart search, and a claims-entitlement assistant. Contracts are in English (FIDIC/construction style); the UI/chat/answers are Arabic + RTL, but evidence quotes stay in the original English.

Current status: Phase 0 (infra), Phase 1 (Drive ingestion pipeline), Phase 2 (RAG/citation-lock QA + chat frontend), and risk scanning are built. Contract comparison, cross-document smart search, and the claims-entitlement assistant are not yet implemented (see README.md "حالة المشروع" for the phase breakdown).

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

# Ask a citation-lock question (RAG QA)
curl -X POST localhost:8000/api/qa/ask -H "Content-Type: application/json" -d '{"question": "..."}'

# Run/poll the risk scanner for one ingested contract
curl -X POST localhost:8000/api/risk/scan -H "Content-Type: application/json" -d '{"contract_id": 1}'
curl "localhost:8000/api/risk/scan/status?contract_id=1"
curl localhost:8000/api/risk/1

# Backend unit tests (pytest; stubs out chromadb/sentence-transformers if absent, see tests/conftest.py)
cd backend && pip install -r requirements-dev.txt && pytest

# Frontend dev server
cd frontend && npm run dev      # next dev -p 3000
cd frontend && npm run build
cd frontend && npm run lint
```

No backend linter is configured yet (`next lint` also has no ESLint config committed - it prompts interactively). Backend unit tests so far cover `app/rag/qa.py`, `app/rag/citation_lock.py`, `app/rag/retrieval.py`, and `app/risk/scanner.py` — there is no test coverage for ingestion, parsing, or the DB layer. There is no Alembic autogenerate workflow established beyond the single `0001_initial_schema` migration — write new migrations by hand following that file's style.

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
   |-- RAG retrieval + OpenRouter LLM calls, citation-lock confidence scorer (app/rag/)
   |-- Risk scanner (app/risk/) -- built on the same citation-lock primitives as RAG QA
   |-- (planned) Compare / Smart search / Claims assistant
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

### Citation-lock (`backend/app/rag/citation_lock.py`, shared by QA and risk scanning)

The model is always shown a numbered list of retrieved clauses and may only cite by that number — it never supplies its own quote text, clause number, or page reference. `resolve_citations()` drops any index that's out of range, wrong-typed (including `bool`, since `isinstance(True, int)` is `True` in Python), or duplicated; `parse_json_object()` turns any non-JSON-object LLM response into `None` rather than raising. Both `app/rag/qa.py` (answers) and `app/risk/scanner.py` (risk findings) build on these two functions: a result is only produced if the LLM both confirms it *and* cites at least one verifiable chunk, and the resulting confidence is `min()` of the cited chunks' retrieval similarity — never the LLM's own self-reported confidence. Confidence bands (`app/config.py` `confidence_high`/`warn`/`refuse`): >0.90 high, 0.70-0.90 warn, 0.50-0.70 red, <0.50 refuse with "no supporting evidence".

### Risk scanning (`backend/app/risk/`)

`catalog.py` holds a fixed list of FIDIC/construction red-flag categories (`RiskRule`: `rule_key`, an Arabic `query_ar` used to retrieve candidate clauses, `description_ar` given to the LLM, and a static `severity`). `scanner.scan_contract(contract_id)` checks each rule independently — one rule's LLM failure is logged and skipped, never aborts the rest of the scan. `app/api/routes_risk.py` runs scans as a background task (same in-memory-status pattern as `routes_ingestion.py`) and persists one `RiskResult` row per (rule, cited clause) pair, deleting prior results for that contract first (rescans are idempotent, not additive).

### Database models (`backend/app/db/models.py`)

`Contract` (1) -> `Clause` (many), plus `ChatMessage`, `RiskResult` (now populated by `app/risk/scanner.py`), and `CompareResult` (still a schema-only placeholder for the not-yet-built contract-comparison feature).

## Secrets

Real secret values live in **Codespaces secrets** (`GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_ROOT_FOLDER_ID`, `GOOGLE_ARCHIVING_MATRIX_FILE_ID`, `OPENROUTER_API_KEY`), injected as env vars and substituted into `docker-compose.yml` via `${VAR:-}` — there is no committed `.env`, and Codespaces secrets only take effect on *newly created* codespaces, not existing ones (a secret added after a codespace exists requires deleting and recreating it, or manually exporting it into the running shell). `.env.example` documents the same variables for the local-file fallback path (`GOOGLE_SERVICE_ACCOUNT_FILE` + a real `.env`), which is only relevant outside Codespaces.
