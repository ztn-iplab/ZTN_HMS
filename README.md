# ZTN_HMS — Zero Trust Hospital Management Service

This repository contains the Hospital Management Service (HMS) that pairs with the `ZTN_SIM` project to showcase Zero Trust Identity and Access Management (IAM) as an API-first service. The HMS is a research-grade Flask web application that consumes the Zero Trust IAM gateway for authentication, MFA, and adaptive risk scoring while it manages electronic health records (EHR)-style data such as patients, appointments, diagnoses, and nursing interactions. The goal of this README is to make the experiment reproducible across research environments and to document the moving parts needed to validate the IAM flows end-to-end.

---

## Table of contents
1. [System overview](#system-overview)
2. [Repository layout](#repository-layout)
3. [Prerequisites](#prerequisites)
4. [Environment setup](#environment-setup)
5. [Application configuration](#application-configuration)
6. [Database preparation](#database-preparation)
7. [Running the HMS locally](#running-the-hms-locally)
8. [Working with the Zero Trust IAM API](#working-with-the-zero-trust-iam-api)
9. [Reproducing the experiment](#reproducing-the-experiment)
10. [Operational tips](#operational-tips)
11. [Troubleshooting](#troubleshooting)

---

## System overview

| Component | Purpose |
| --- | --- |
| `hospital_core` Flask application | Hosts dashboards for admins, doctors, and nurses. Routes under `hospital_core/routes/` enforce role-based access control that depends on the ZTN IAM-issued session data. |
| Zero Trust IAM API (`ZTN_SIM` backend) | Provides `/login`, `/verify-totp-login`, `/enroll-totp`, `/setup-totp/confirm`, and WebAuthn endpoints that deliver access tokens, trust scores, and MFA policy decisions consumed by `auth_routes.py`. |
| PostgreSQL (`hospital_db`) | Persists local hospital data models (`hospital_core/models.py`) for patients, staff, appointments, diagnoses, and treatments. |
| TLS certificates (`certs/`) | Local development certificates referenced by `main.py` and `run.sh` to serve HTTPS locally. |

Key security capabilities:
- Cookie-based JWT storage configured in `config.py` and `hospital_core/__init__.py` with Flask-JWT-Extended.
- Multi-factor decisioning using TOTP and WebAuthn flags returned from IAM (see `auth_routes.py`).
- Role-aware dashboards (`dashboard_routes.py`) and CRUD helpers (`patient_routes.py`, `appointments.py`).

---

## Repository layout

```
ZTN_HMS/
├── config.py                # Loads environment variables and base configuration
├── main.py                  # Flask entry point (wraps `hospital_core.create_app`)
├── hospital_core/
│   ├── __init__.py          # App factory, extension registration, blueprint wiring
│   ├── extensions.py        # SQLAlchemy, Flask-Login, and migration extensions
│   ├── models.py            # SQLAlchemy models for patients, staff, records
│   └── routes/              # Blueprints for auth, dashboards, patients, appointments
├── templates/               # Jinja2 templates for auth, dashboards, and CRUD UIs
├── static/                  # CSS/JS assets consumed by the templates
├── migrations/              # Alembic migration history for PostgreSQL schema
├── certs/                   # Dev TLS certificate and key pair
├── run.sh                   # Helper script for HTTPS Flask dev server
├── requirements.txt         # Reproducible dependency lock for Python 3.12 envs
└── README.md                # This document
```

---

## Prerequisites

| Tool | Recommended version |
| --- | --- |
| Python | 3.12.x |
| PostgreSQL | 15+ |
| OpenSSL | Latest stable (for generating TLS material if you replace `certs/`) |
| ZTN IAM service | The Zero Trust IAM API from `ZTN_SIM` running locally or remotely |

> **Note:** The included virtual environment (`venv/`) targets Python 3.10 packages. Create a fresh Python 3.12 virtual environment by following the next section for consistent results.

---

## Environment setup

1. **Clone and enter the repository**
   ```bash
   git clone <this repo>
   cd ZTN_HMS
   ```

2. **Create a clean virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Install a Postgres client (optional but handy)**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install postgresql-client
   ```

---

## Application configuration

1. Copy `.env.example` (create one if it does not exist) and populate it with the required secrets:

   ```ini
   SECRET_KEY=dev-secret
   JWT_SECRET_KEY=dev-jwt-secret
   ZTN_IAM_URL=https://localhost:8443/api/v1
   API_KEY=replace-with-ztn-sim-api-key
   SQLALCHEMY_DATABASE_URI=postgresql://ztn:ztn%40sim@localhost:5432/hospital_db
   FLASK_APP=main.py
   FLASK_ENV=development
   ```

   - `SQLALCHEMY_DATABASE_URI` defaults to `postgresql://ztn:ztn%40sim@localhost:5432/hospital_db` in `config.py`. Update that constant (or subclass `Config`) if your Postgres connection string differs.
   - `ZTN_IAM_URL` and `API_KEY` must match the running Zero Trust IAM service used in the `ZTN_SIM` experiments.

2. Source the environment file (or export the variables manually):
   ```bash
   set -a
   source .env
   set +a
   ```

---

## Database preparation

1. **Create the database and role**
   ```bash
   psql -U postgres <<'SQL'
   CREATE USER ztn WITH PASSWORD 'ztn@sim';
   CREATE DATABASE hospital_db OWNER ztn;
   GRANT ALL PRIVILEGES ON DATABASE hospital_db TO ztn;
   SQL
   ```

2. **Run migrations**
   ```bash
   source .venv/bin/activate
   flask db upgrade
   ```

   The Alembic scripts under `migrations/` provision the tables defined in `hospital_core/models.py`.

---

## Running the HMS locally

### Option 1: Flask CLI with TLS
```bash
source .venv/bin/activate
export FLASK_APP=main.py
flask run --host=0.0.0.0 --port=5000 \
  --cert=certs/hospital_app.crt \
  --key=certs/hospital_app.key
```

### Option 2: Python entry point
```bash
source .venv/bin/activate
python main.py
```
This starts the HTTPS development server defined in `main.py`, which references the same certificate pair.

### Option 3: Helper script
```bash
chmod +x run.sh
./run.sh
```
The script pins the host name (`localhost.localdomain`) to match the provided certificate subject.

---

## Working with the Zero Trust IAM API

All authentication flows terminate at the IAM service before users can reach the HMS dashboards:

1. **Login** — `auth_routes.login` (`/auth/login`) forwards credentials to `${ZTN_IAM_URL}/login` with the `X-API-KEY` header and captures the returned `access_token`, `role`, `user_id`, and `trust_score` in the Flask session.
2. **Adaptive MFA** — Session flags (`require_totp`, `require_webauthn`, `require_totp_setup`, `skip_all_mfa`) control which blueprint view to render next. TOTP enrollment uses `${ZTN_IAM_URL}/enroll-totp` and `${ZTN_IAM_URL}/setup-totp/confirm`; verification calls `${ZTN_IAM_URL}/verify-totp-login`. WebAuthn flows redirect to the IAM pages when `require_webauthn` is set.
3. **Role-based access** — Successful MFA writes cookies via Flask-JWT-Extended and routes the user to `dashboard/admin_dashboard`, `dashboard/doctor_dashboard`, or `dashboard/nurse_dashboard` as enforced by the `protect_role` decorator in `dashboard_routes.py`.

To connect to your IAM service:
- Ensure CORS/TLS settings allow the HMS origin.
- Reuse the same seed data (users, authenticators) between `ZTN_SIM` and the HMS so that role IDs and MFA enrollment states are predictable.

---

## Reproducing the experiment

1. **Provision IAM identities**
   - In `ZTN_SIM`, create at least three identities mapped to the `admin`, `doctor`, and `nurse` roles. Attach TOTP secrets and optionally WebAuthn credentials to exercise both MFA paths.

2. **Start all services**
   - Launch the IAM backend and expose its HTTPS endpoint.
   - Start PostgreSQL locally.
   - Run the HMS using the TLS instructions above.

3. **Verify login permutations**
   - Navigate to `https://localhost:5000/auth/login` and authenticate as each role.
   - When prompted, complete TOTP or WebAuthn to observe how the HMS honors the IAM policy flags (`require_totp`, `require_webauthn`).
   - Confirm that the trust score and access token are persisted in the Flask session (`session["trust_score"]`, `session["access_token"]`).

4. **Exercise CRUD functionality**
   - Seed patients, appointments, and diagnoses via the admin or doctor dashboards (templates in `templates/patients/` and `templates/appointments/`).
   - Inspect the PostgreSQL tables to verify that role-restricted views only expose data to authorized users.

5. **Document findings**
   - Capture screenshots of each role’s dashboard to mirror the `ZTN_SIM` documentation.
   - Record IAM API responses to highlight adaptive decisions for future reproducibility.

These steps mirror the methodology used for `ZTN_SIM`, making it straightforward to compare identity journeys between the IAM service and this relying party application.

---

## Operational tips

- **Certificate rotation:** Replace `certs/hospital_app.{crt,key}` with lab-specific certificates if your environment enforces custom trust stores. Update `run.sh`/`main.py` if the filenames change.
- **Session hardening:** Update `config.py` for production by setting `JWT_COOKIE_SECURE=True` and `JWT_COOKIE_SAMESITE='Strict'`, and by enabling CSRF protection once hosting externally.
- **Extending the data model:** Modify `hospital_core/models.py` and run `flask db migrate`/`flask db upgrade` to evolve schemas while keeping Alembic history consistent.
- **Background jobs:** If you need asynchronous tasks (e.g., syncing IAM profile updates), integrate Celery or APScheduler and document the worker entry points here.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError` for Flask packages | Using the legacy `venv/` that targets Python 3.10 | Recreate a `.venv` with Python 3.12 and reinstall from `requirements.txt`. |
| Unable to connect to PostgreSQL | Connection string mismatch or role missing | Update `SQLALCHEMY_DATABASE_URI` and verify the `ztn` role/database exist. |
| IAM API returns `401 Unauthorized` | Missing/incorrect `X-API-KEY` header | Confirm the HMS `.env` uses the correct API key from `ZTN_SIM`. |
| MFA loop when logging in | Flags `require_totp`/`require_webauthn` not cleared | Complete enrollment/verification flows; delete cookies if state becomes inconsistent. |
| Browser warns about self-signed certs | Dev cert not trusted | Import `certs/hospital_app.crt` into your OS/browser trust store or use HTTP for quick smoke testing. |

---

Happy experimenting! If you extend this HMS in lockstep with `ZTN_SIM`, update this README with the new steps so future researchers can reproduce your Zero Trust IAM evaluations.
