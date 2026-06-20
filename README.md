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
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | معرّف مجلد Drive الجذري |
| `GOOGLE_ARCHIVING_MATRIX_FILE_ID` | معرّف ملف/شيت Archiving Matrix |
| `OPENROUTER_API_KEY` | openrouter.ai |

**أفضل ممارسة**: أضف هذه القيم كـ **Codespaces Secrets** (Settings → Codespaces → Secrets) بدلاً من كتابتها في `.env` محلياً — تُحقن تلقائياً عند إنشاء أي Codespace جديد.

لا حاجة لمفتاح embeddings — تعمل محلياً عبر `sentence-transformers` (نموذج متعدد اللغات) داخل حاوية الـ backend.

### التحقق من عمل النظام

- Backend: افتح المنفذ المُوجَّه 8000 → `/api/health` يجب أن يرجع `{"status": "ok"}`.
- Frontend: افتح المنفذ المُوجَّه 3000 → يجب أن تظهر صفحة "مستشار العقود" بواجهة عربية RTL.

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

هذا هو الإعداد الأساسي (Phase 0): البنية التحتية والحاويات والمسارات الفارغة جاهزة. الميزات الفعلية (الفهرسة، RAG، Citation Lock، تحليل المخاطر، المقارنة، البحث الذكي، مساعد المطالبات) تُبنى في المراحل التالية — راجع خطة التنفيذ الكاملة للتفاصيل.
