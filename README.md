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

انسخ `.env.example` إلى `.env` وعبّئ:

| المتغير | المصدر |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_FILE` | مسار مفتاح Service Account (انظر أدناه) — لا حاجة لـ OAuth أو متصفح |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | معرّف مجلد Drive الجذري (مثلاً مجلد 01-Contracts) |
| `GOOGLE_ARCHIVING_MATRIX_FILE_ID` | معرّف ملف/شيت Archiving Matrix |
| `OPENROUTER_API_KEY` | openrouter.ai |

`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `NEXTAUTH_*` غير مطلوبة حالياً — كانت لتسجيل دخول تفاعلي للواجهة، وتم تأجيلها لأن المستخدم وحيد ولا حاجة فعلية لها في هذه المرحلة.

**أفضل ممارسة**: أضف هذه القيم كـ **Codespaces Secrets** بدلاً من كتابتها في `.env` محلياً — تُحقن تلقائياً عند إنشاء أي Codespace جديد.

لا حاجة لمفتاح embeddings — تعمل محلياً عبر `sentence-transformers` (نموذج متعدد اللغات) داخل حاوية الـ backend.

### الوصول إلى Google Drive (Service Account — بدون متصفح أو OAuth)

الـ backend يتصل بـ Drive باسم حساب خدمة (Service Account) مستقل تماماً عن أي تسجيل دخول بشري. المفتاح محفوظ محلياً في `backend/secrets/service-account.json` (مُستثنى من git تماماً، لن يُرفع أبداً).

**الخطوة المطلوبة منك**: شارك مجلدات Drive (01-Contracts، 02-Specifications، وملف/شيت Archiving Matrix) مع بريد حساب الخدمة كـ **Viewer**:

```
contract-consultant-agent@contract-consultant.iam.gserviceaccount.com
```

(افتح كل مجلد في Drive → Share → ألصق هذا البريد → Viewer → Send)

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
