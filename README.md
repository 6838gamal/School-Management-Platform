# 🏫 School Management Platform

نظام متكامل لإدارة المدارس مبني على **FastAPI** — يشمل إدارة الطلاب والمعلمين والجداول الدراسية والحضور والدرجات والسلوك والأنشطة والواجبات والتقارير، مع نظام صلاحيات (RBAC) متعدد الأدوار وواجهة ويب عربية.

> An integrated school management platform built with FastAPI, featuring students, teachers, schedules, attendance, grades, behavior, activities, homework, reports, and a full RBAC permission system with an Arabic web UI.

---

## ✨ المزايا الرئيسية

| الوحدة | الوصف |
|---|---|
| 🏫 إدارة المدرسة | هيكل أكاديمي: سنوات، فصول، مراحل، مواد، قاعات، شعب (sections) |
| 👨‍🏫 الطلاب والمعلمون | ملفات كاملة، تعيين شعب وفصول، بحث وتصفية |
| 📅 الجداول الدراسية | إنشاء وعرض جداول مرتبطة بالسنة الأكاديمية |
| ✅ الحضور والغياب | تسجيل يومي للطلاب والمعلمين + تقارير |
| 📊 الدرجات | إدخال وعرض وتقارير الدرجات |
| 🎯 الأنشطة | وحدات نشاط وأدوار لمسؤول الأنشطة |
| 🧠 السلوك | متابعة السلوكيات والملاحظات |
| 📝 الواجبات | إدارة الواجبات المنزلية |
| 🔔 الإشعارات | نظام إشعارات داخلي |
| 📄 التقارير | تقارير PDF تُولَّد عبر WeasyPrint بروابط تنتهي صلاحيتها |
| 🔐 الصلاحيات | RBAC كامل: مدير، وكيل، مسؤول أنشطة، معلم |

## 🛠️ البنية التقنية

- **Backend:** FastAPI 0.115 + Pydantic v2 + SQLAlchemy 2 (async) + Alembic
- **قاعدة البيانات:** PostgreSQL 16 (asyncpg)
- **الواجهة:** قوالب Jinja2 + React/Vite (دليل `src/`)
- **الأمان:** bcrypt + جلسات موقّعة (itsdangerous) + صلاحيات لكل دور
- **البنية التحتية:** Docker Compose + Nginx

## 📁 هيكل المشروع

```
├── app/
│   ├── core/          # الإعدادات، قاعدة البيانات، الأمان، الصلاحيات، الاستثناءات
│   ├── models/        # نماذج ORM (users, students, teachers, schedules, ...)
│   ├── schemas/       # مخططات Pydantic
│   ├── repositories/  # طبقة الوصول للبيانات
│   ├── services/      # منطق الأعمال (auth_service, ...)
│   ├── routes/
│   │   ├── web/       # مسارات الواجهة (HTML)
│   │   └── api/v1/    # واجهة REST API
│   ├── templates/     # قوالب Jinja2 (عربية RTL)
│   └── static/        # ملفات ثابتة
├── migrations/        # هجرات Alembic
├── src/               # واجهة React (اختيارية)
├── nginx/             # إعدادات Nginx
├── tests/             # اختبارات الوحدات
└── .github/workflows/ # CI
```

## 🚀 البدء السريع (Docker)

```bash
# 1. انسخ ملف البيئة واضبط القيم
cp .env.example .env

# 2. شغّل المنظومة كاملة (PostgreSQL + التطبيق + Nginx)
docker compose up -d --build
```

ثم افتح المتصفح على: **http://localhost** — سيتم تلقائيًا تطبيق الهجرات وتهيئة قاعدة البيانات وإنشاء المستخدمين التجريبيين.

## 👨‍💻 التشغيل اليدوي (تطوير)

```bash
# 1. متطلبات النظام: Python 3.12 + PostgreSQL قيد التشغيل
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 2. أنشئ قاعدة البيانات وعدّل .env
cp .env.example .env

# 3. طبّق الهجرات وشغّل الخادم
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## 🔑 بيانات الدخول الافتراضية

| الدور | البريد | كلمة المرور |
|---|---|---|
| 👨‍💼 مدير | `admin@school.edu` | `admin123` |
| 👨‍🏫 وكيل | `deputy@school.edu` | `deputy123` |
| 🎯 مسؤول أنشطة | `activities@school.edu` | `activities123` |
| 📚 معلم | `teacher@school.edu` | `teacher123` |

> ⚠️ **غيّر هذه البيانات فورًا في بيئة الإنتاج.**

## ⚙️ متغيرات البيئة الرئيسية

| المتغير | الافتراضي | الوصف |
|---|---|---|
| `APP_ENV` | `development` | بيئة التشغيل (`production` في الإنتاج) |
| `SECRET_KEY` | `change-me-...` | **مفتاح توقيع الجلسات — غيّره في الإنتاج** |
| `DATABASE_URL` | `postgresql+asyncpg://...` | اتصال قاعدة البيانات |
| `SESSION_MAX_AGE` | `604800` | مدة صلاحية الجلسة (7 أيام) |
| `SESSION_SECURE` | `false` | اجعلها `true` في الإنتاج (HTTPS) |
| `SMTP_*` | — | إعدادات البريد للإشعارات (اختياري) |

## 🔌 واجهة برمجة التطبيقات (API)

المسارات متاحة تحت `/api/v1` (مصادقة عبر كوكي الجلسة):

- `POST /api/v1/auth/login` — تسجيل الدخول
- `POST /api/v1/auth/logout` — تسجيل الخروج
- `POST /api/v1/auth/register` — تسجيل مدرسة
- الموارد: `students`, `teachers`, `academics`, `attendance`, `grades`, `schedules`, `homework`, `activities`, `behavior`, `notifications`, `reports`

وثائق Swagger التفاعلية: `http://localhost:8000/docs`

## 🧪 الاختبارات

```bash
# تشغيل اختبارات الوحدات (لا تتطلب قاعدة بيانات)
python -m pytest tests -v

# فحص الجودة بأداة Ruff
ruff check app tests
```

## 🤖 CI/CD

يوجد workflow جاهز في `.github/workflows/ci.yml` يعمل على كل push/PR:
فحص الجودة (Ruff) + تشغيل الاختبارات ضد قاعدة PostgreSQL حقيقية داخل GitHub Actions.

## 🤝 المساهمة

1. Fork المشروع وأنشئ فرعًا: `git checkout -b feature/your-feature`
2. نفّذ تغييراتك وأضف اختبارات
3. تأكد من نجاح `ruff check` و `pytest`
4. افتح Pull Request

## 📄 الترخيص

راجع ملف الترخيص الخاص بالمشروع.
