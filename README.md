# সুরক্ষা Wallet — polished v2.1

**আপনার অর্থ, আপনার নিয়ন্ত্রণে।**

A customer wallet interface with transfer checks, understandable warnings, contact checking/reporting and human review. This version uses virtual money and synthetic histories; it does not send real payments.

## Run on Windows (PowerShell)

Open PowerShell in the extracted folder containing `requirements.txt`, `app/` and `models/`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Keep the terminal open. Press Ctrl+C to stop.

The frontend and models are already built. You do not need Node.js or model training for normal startup. Do not use `streamlit run app.py`: this release uses FastAPI and React.

## Sign in

The login page has **no demo-account buttons, account list, exposed passwords or automatic sign-in**. Enter your account details normally, or use **Create an account**. Customer and analyst roles keep their existing separate views.

For a controlled local judge walkthrough, operator credentials are listed in `RUN.md`, not displayed on the login page. Seeding preserves existing accounts. Seeded sample accounts remain fictional and are not appropriate for deployment with real funds.

## Interface update

- Green/yellow brand palette, clearer typography, refined spacing and a faint logo watermark.
- Subtle Bangla tagline and wallet/navigation labels, with English action labels for clarity.
- Consistent SVG icons, password visibility control and keyboard focus indicators.
- Smooth entrance, hover, balance and meter motion, with reduced-motion support.
- Removed public credential shortcuts and customer presenter overrides.
- Customer concerns remain understandable; a warning is not a proven fraud verdict. Technical scores stay in staff views and remain synthetic-model evidence.

## Developer checks

```bash
python -m pytest -q tests
cd frontend
npm ci
npm run build
```

The UI build is written to `app/static/`. The existing requirements pin the versions used by the included model files; do not substitute an older scikit-learn without retraining.

See `RUN.md` for developer commands and `POLISH_NOTES.md` for checked changes. No real-world fraud-accuracy or production-readiness claim is made.
