# Running version 2 (FastAPI + React)

README.md still describes the earlier Streamlit prototype; these are the current run steps.

## Quick start (Python 3.12 or 3.13)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.seed                   # demo accounts, wallet histories, sample reports
python -m uvicorn app.main:app --port 8000
```

Open http://localhost:8000. Customers and analysts use the same address; the role decides what you see.

| Account | Sign in | Password | Wallet PIN |
|---|---|---|---|
| Six customers (student, salaried, merchant, remittance, freelancer, senior) | 01700000001 … 01700000006 | Demo#2026 | 2468 |
| Analyst | analyst | Analyst#2026 | |
| Admin | admin | Admin#2026! | |

Test numbers with seeded reports: 00000000001 (one report), 00000000002 (three).

Trained models and the built web app are included, so nothing else is needed. Or run `docker compose up --build`.

## Tests

```bash
python -m pytest -q tests
```

## Retrain everything (about 6 minutes)

```bash
python -m pipeline.build_all
```

Generates 3,000 synthetic customers (about 580,000 events), a separate unseen-attack stream and about 7,500 messages, then trains the fraud, sequence, attack-pattern and message models and writes `models/metrics.json`.

## Change the web app

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to port 8000
npm run build      # writes app/static
```

Brand colours are the variables at the top of `frontend/src/styles.css`.

## Where each feature lives

| Feature | Location |
|---|---|
| Calibrated fraud probability, LightGBM | `pipeline/train_fraud.py`, `app/ml/scoring.py` |
| Customer segments, attack patterns | `pipeline/generate_data.py` |
| Burst and sequence features | `app/ml/features.py`, `app/ml/sequence.py` |
| Scam message model | `pipeline/generate_messages.py`, `pipeline/train_nlp.py`, `app/ml/nlp.py` |
| Changing scam methods (drift) | `app/ml/drift.py`, `/api/analyst/drift` |
| Login, lockout, roles | `app/security.py`, `app/routers/auth.py` |
| Multiple wallets, ledger, review flow | `app/services/wallet.py` |
| Prevented value, review time | `/api/analyst/overview` in `app/routers/analyst.py` |
| Permissions (device, location, camera) | `app/routers/customer.py` |
| Audit log (hash chained) | `app/audit.py` |
| Settings | `app/config.py`, `.env.example` |

API reference: http://localhost:8000/api/docs (off when `SUROKKHA_ENVIRONMENT=production`).
