# مستشار العقود — Contract Consultant

وكيل عقود ومطالبات ذكي يتصل مباشرة بـ Google Drive، يقرأ العقود ويجيب على الأسئلة بالاستناد إلى نص المستند فقط (Citation Lock)، مع تحليل المخاطر، مقارنة العقود، البحث الذكي عبر جميع العقود، ومساعد المطالبات.

## البيئة: GitHub Codespaces فقط

هذا المشروع مُصمم للعمل بالكامل داخل **GitHub Codespaces** — لا حاجة لتثبيت Docker أو Node أو Python على جهازك. كل الخدمات (Next.js, FastAPI, Postgres, ChromaDB, Redis) تُشغَّل تلقائياً داخل الحاوية السحابية عبر `.devcontainer/devcontainer.json` و `docker-compose.yml`.

### تشغيل المشروع

1. ادفع هذا المستودع إلى GitHub (إذا لم يكن مدفوعاً بعد):
   ```bash
   git remote add origin <repo-url>
   git push -u origin main
   ```
2. على صفحة المستودع في GitHub: **Code → Codespaces → Create codespace on main**.
3. Codespaces سيبني ويشغّل تلقائياً 5 خدمات: `frontend` (3000), `backend` (8000), `postgres` (5432), `chromadb` (8001), `redis` (6379).
4. بعد الإنشاء، تحقق من الخدمات:
   ```bash
   docker compose ps
   ```

### المفاتيح والإعدادات المطلوبة (قبل الاستخدام الفعلي)

انسخ `.env.example` إلى `.env` (وكذلك `frontend/.env.local.example` إلى `frontend/.env.local`) وعبّئ:

| المتغير | المصدر |
|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 Client (فعّل Drive API + Sheets API). Redirect URI = رابط Codespaces المُوجَّه للمنفذ 3000 |
| `NEXTAUTH_SECRET` | أي قيمة عشوائية قوية، مثلاً `openssl rand -base64 32` |
| `NEXTAUTH_URL` | رابط Codespaces المُوجَّه للمنفذ 3000 |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | معرّف مجلد Drive الجذري (مثلاً مجلد 01-Contracts) |
| `GOOGLE_ARCHIVING_MATRIX_FILE_ID` | معرّف ملف/شيت Archiving Matrix |
| `GOOGLE_REFRESH_TOKEN` | ناتج تشغيل `scripts/get_refresh_token.py` مرة واحدة (انظر أدناه) |
| `OPENROUTER_API_KEY` | openrouter.ai |

**أفضل ممارسة**: أضف هذه القيم كـ **Codespaces Secrets** (Settings → Codespaces → Secrets) بدلاً من كتابتها في `.env` محلياً — تُحقن تلقائياً عند إنشاء أي Codespace جديد.

لا حاجة لمفتاح embeddings — تعمل محلياً عبر `sentence-transformers` (نموذج متعدد اللغات) داخل حاوية الـ backend.

### الحصول على GOOGLE_REFRESH_TOKEN (مرة واحدة فقط)

تسجيل الدخول التفاعلي عبر NextAuth في الواجهة يُستخدم لجلسة المستخدم فقط. عمليات الفهرسة (Ingestion) في الـ backend تحتاج Refresh Token مستقل يعمل بدون متصفح مفتوح. لأن هذا يتطلب فتح متصفح أثناء التفويض، **شغّل هذا السكربت من جهازك المحلي** (لا داخل Codespace، حيث لا يوجد متصفح):

```bash
pip install google-auth-oauthlib
GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... python scripts/get_refresh_token.py
```

سيفتح متصفحك لتسجيل الدخول وتفويض صلاحية القراءة على Drive، وفي النهاية يطبع Refresh Token — أضفه كـ `GOOGLE_REFRESH_TOKEN` في `.env` أو كـ Codespaces Secret.

### تجهيز قاعدة البيانات وتشغيل الفهرسة (داخل Codespace)

```bash
cd backend
alembic upgrade head          # ينشئ جداول contracts/clauses/... في Postgres
python -m app.ingestion.cli   # يقرأ Google Drive، يستخرج البنود، يخزّنها في Chroma + Postgres
```

أو عبر الـ API مباشرة: `POST /api/ingest/run` ثم `GET /api/ingest/status` لمتابعة التقدّم.

### التحقق من عمل النظام

- Backend: افتح المنفذ المُوجَّه 8000 → `/api/health` يجب أن يرجع `{"status": "ok"}`.
- Frontend: افتح المنفذ المُوجَّه 3000 → يجب أن تظهر صفحة "مستشار العقود" بواجهة عربية RTL.
- الفهرسة: بعد تشغيل `app.ingestion.cli`، يجب أن يظهر ملخص JSON يحتوي على أسماء الملفات المُفهرسة، وعدد صفوف `clauses` في Postgres يساوي عدد القطع (chunks) في مجموعة Chroma `contract_clauses`.

## البنية التقنية

| الطبقة | التقنية |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS، RTL كامل |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Vector DB | ChromaDB |
| LLM | OpenRouter (Economy/Balanced/Premium model routing) |
| Embeddings | sentence-transformers (محلي، مجاني، متعدد اللغات) |
| Rate Limiting | Redis |
| Auth | Google OAuth2 (NextAuth.js) |

## حالة المشروع

- **Phase 0 (مكتمل)**: البنية التحتية والحاويات وهيكل المشروع.
- **Phase 1 (مكتمل)**: خط أنابيب القراءة من Google Drive (PDF/DOCX/Google Docs)، قارئ Archiving Matrix، تقطيع البنود الذكي (Clause-Aware Chunking)، embeddings محلية متعددة اللغات، التخزين في ChromaDB + Postgres.
- **المراحل القادمة**: RAG + Citation Lock (المرحلة 2)، واجهة المحادثة وعارض المستندات (المرحلة 3)، تحليل المخاطر/المقارنة/البحث الذكي/مساعد المطالبات (المرحلة 4)، التحسينات الأمنية النهائية (المرحلة 5).
