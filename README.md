# সুরক্ষা Wallet

**A little context. A smarter guard.**

সুরক্ষা Wallet is an AI-assisted security prototype for mobile financial services. It combines transaction behavior analysis, locally reported contact concerns, and an investigation workflow to help customers review suspicious activity before proceeding.

The project is designed as a protection layer that could integrate with an MFS provider. It is an independent hackathon prototype, with no affiliation or live connection to upay.

> **Project status:** customer-facing preview with virtual money, synthetic history, one fixed customer account, and local databases. No real payments, login, identity verification or live device telemetry are connected.

## Problem and customer value

Customers may send money to suspicious recipients, encounter impersonation calls, or receive messages requesting credentials. At the same time, travel, a new device, or an unusual payment can be legitimate.

Our approach raises understandable concerns and keeps questionable transfers available for investigation rather than declaring unfamiliar activity to be fraud. Customers can confirm or reject requests; reviewers can inspect the evidence and record a decision.

## Features

| Customer wallet | Analyst workspace |
|---|---|
| Available preview balance and recent activity | Customer transfer requests and status |
| Send-money request and confirmation | Behavioral model scores and observed signals |
| Green-to-red concern meter | Number report counts and review reasons |
| Cancellation and reserved-fund release | Approve or cancel held preview requests with notes |
| Downloadable activity statement | Investigation cases and evaluation results |
| Call/text checks and local reporting | Rule-baseline comparison and session activity logs |

The interface uses the supplied সুরক্ষা Wallet logo, a faint watermark, Bengali accents, collapsible tile navigation and reduced-motion-aware animations.

## How a transfer works

1. The customer chooses a saved recipient or enters a number and an amount.
2. The system derives behavioral features from strictly earlier same-customer events.
3. A Random Forest generates an uncalibrated model score.
4. A separate decision policy combines model output, behavioral concerns and local number reports.
5. The customer sees the reasons and reviews the request.
6. Routine requests complete after confirmation. Flagged requests stay under review, even when the customer confirms.
7. An analyst records notes and approves or cancels a held preview request.

Pending requests reserve funds. Completion debits the preview ledger once; cancellation releases the reservation. The backend rechecks current reports at confirmation, so reports submitted after the original request can still raise a concern.

### Current decision policy

| Signal | Result |
|---|---|
| Model score at least 40/100 | Further review |
| Strong behavioral concern or unexplained device/location change | Further review or context check |
| One local number report | Customer caution |
| Two or more local number reports | Further review |
| No review requirement | Ordinary review and confirmation |

These are initial prototype policy thresholds, not production-calibrated thresholds. Report counts represent unverified submissions, not distinct verified victims. A report count is not a learned ML feature.

The customer meter shows **Safe → Use caution → Dangerous** with a categorical marker. It is not a fraud probability. “Safe” means lower concern under the available checks; “Dangerous” means elevated concern requiring review. Neither endpoint establishes safety or guilt.

## Call and text protection

The checker normalizes common Bangladesh mobile-number formats, searches locally submitted reports and screens optional English/Bengali message text for selected warning patterns, including OTP/PIN requests, urgency, prizes, payments, links and remote access.

Reports store the number, contact type, category, incident text and UTC timestamp. Identical number/channel/category/text submissions are deduplicated. Text matching is exact after case and whitespace normalization, with a minimum of 20 characters, and only matches text-message reports.

This is heuristic screening and database lookup, not a trained scam-message model or a verified caller-reputation service. No reports does not mean safe. Caller numbers can be spoofed. Queries are not stored; reports are saved only when explicitly submitted.

## Technology

- **Interface:** Streamlit, Python and CSS
- **ML:** scikit-learn Random Forest
- **Data:** pandas, NumPy and generated synthetic transactions
- **Persistence:** SQLite for wallet requests and contact reports
- **Model storage:** joblib

No API key or external service is needed to run the local prototype.

## Quick start

### Requirements

Python 3.11 or 3.12 is recommended. Package installation needs internet access. After installing dependencies, the prototype runs locally without an external API.

Download or clone this repository and open the folder containing `app.py` and `requirements.txt`.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/generate_data.py
python src/train.py
python tests/smoke.py
python tests/wallet_smoke.py
python tests/decision_smoke.py
python -m streamlit run app.py
```

If PowerShell prevents activation, use a Command Prompt terminal:

```bat
.venv\Scripts\activate.bat
```

Or use the environment's Python directly without activating it:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Run generation and training with that same interpreter if using this approach.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/generate_data.py
python src/train.py
python tests/smoke.py
python tests/wallet_smoke.py
python tests/decision_smoke.py
python -m streamlit run app.py
```

Open **http://localhost:8501** for the customer wallet.

### Analyst workspace

Open a second terminal in the same project folder and activate the same environment:

```powershell
python -m streamlit run analyst_app.py --server.port 8502
```

Open **http://localhost:8502**. Customer and analyst apps share the local wallet database when launched from this project.

**The analyst entry point has no authentication or authorization. Keep it local; do not expose it as a public admin service.**

Press Ctrl+C to stop an app. Run `deactivate` to exit an activated environment.

## Data and AI approach

The generator creates **200 synthetic customers with 90 timestamped events each**: 18,000 events total. The first 20 events per customer establish warm-up history and are excluded from model fitting and evaluation.

For each later event, the profile uses the last 50 strictly earlier events belonging to the same customer. It derives the median amount, common district, familiar devices/recipients and usual-hour range. The previous-ten-minute transfer count is calculated from timestamps.

| Feature | Meaning |
|---|---|
| `amount_ratio` | Amount relative to the prior median |
| `new_device` | Device absent from recent history |
| `new_recipient` | Recipient absent from recent history |
| `location_change` | District differs from the prior common district |
| `unusual_hour` | Time outside the prior usual-hour range |
| `transactions_10min` | Earlier activity in the preceding 10 minutes |
| `balance_drain_ratio` | Amount relative to available balance |
| `failed_pin_attempts` | Supplied session observation |

Future events and attack labels are not profile inputs. Training and evaluation hold out different customers. The customer preview supplies historical defaults for device/location and zero failed PIN attempts; these are not real telemetry. Consequently, those attack signals are better explored in the analyst simulator until integration exists.

Earlier non-cancelled wallet requests contribute to the customer activity history. The synthetic historical events establish behavior but are not part of the new virtual-wallet ledger.

## Evaluation

The following results come from the current deterministic synthetic run using seed 42 and a fixed 0.40 review threshold. Regenerate `models/metrics.json` to obtain results for your environment; package versions can affect them.

| Metric | Random Forest | Basic rule |
|---|---:|---:|
| Precision | 84.81% | 64.29% |
| Attack recall | 74.44% | 3.33% |
| False-positive rate | 1.11% | 0.15% |
| F1 | 0.793 | — |
| Average precision | 0.872 | — |

The rule flags a **new device AND an amount above three times the prior median**. Both approaches use the same held-out test events. The model detects more simulated attacks, with more false alerts; the comparison does not establish superiority over a production fraud system.

| Actual / prediction | Not flagged | Flagged |
|---|---:|---:|
| Legitimate | 3,194 | 36 |
| Simulated attack | 69 | 201 |

There are 3,500 test events: 3,230 legitimate events and 270 simulated attacks. Metrics evaluate the behavioral model, not the combined report policy or verification workflow. Synthetic results do not establish real-world accuracy. Scores are uncalibrated; readable activity signals are feature flags, not SHAP attributions or causal explanations.

## Persistence and preview balances

Fresh preview wallets start at **BDT 10,00,000**. An existing wallet from the original BDT 30,000 version receives a one-time BDT 9,70,000 adjustment, preserving earlier debits and pending reservations.

| Storage | What it contains |
|---|---|
| `data/transactions.csv` | Generated synthetic history |
| `data/profiles.json` | Generated profile summary |
| `data/wallet.sqlite3` | Persistent virtual balance, transfer requests and action records |
| `data/contact_reports.sqlite3` | Persistent local contact reports |
| `models/model.joblib` | Trained model |
| `models/metrics.json` | Evaluation output |

Databases survive app restarts on the same computer. Separate computers do not synchronize. Older analyst investigation cases and session activity logs remain browser-session state; download them before restarting. Wallet requests are persistent.

Generated files, local databases and the virtual environment are excluded from Git. Never commit real customer data or credentials. Avoid OTPs, passwords and financial account details in report descriptions. Regeneration replaces synthetic files/model output; it does not reset SQLite databases.

## Project structure

```text
app.py                       Customer entry point
analyst_app.py               Analyst entry point
assets/                     Supplied brand logo
.streamlit/config.toml      Theme settings
src/
  core.py                   Feature definitions and ML score
  history.py                Strictly prior history extraction
  generate_data.py          Synthetic event generation
  train.py                  Training and evaluation
  review.py                 Behavioral/context checks
  decision.py               Combined ML/report decision policy
  wallet_store.py           Virtual ledger and request states
  reports.py                Persistent report storage and lookup
  contact_check.py          Contact/message screening
  views/customer.py         Customer screens
tests/
  smoke.py                  Prior-only history and feature checks
  wallet_smoke.py           Reservation and settlement checks
  decision_smoke.py         ML/report routing and confirmation checks
requirements.txt
README.md
```

## Suggested judging walkthrough

1. Show the customer wallet and complete a small transfer to a saved contact.
2. Submit two different reports for a test number. Explain that these are unverified submissions.
3. Check that number, then request a transfer to it.
4. Show the reasons and concern meter. Record customer confirmation and demonstrate that the request stays under review.
5. Open Analyst → Wallet requests, inspect evidence, record notes and cancel the transfer.
6. Refresh the customer view to show cancellation and released funds.
7. Open the model-performance page and explain the synthetic evaluation and rule comparison.

## Responsible use and limitations

- One fixed preview account; no real registration, login or role-based authorization.
- Virtual money only; no MFS/payment provider integration.
- Customer confirmation is a recorded response, not trusted identity verification.
- Local reports are unverified and lack reporter identity, moderation and robust abuse prevention.
- Behavior profiles include earlier observations that may be suspicious; production needs controls against profile poisoning.
- Synthetic balances are not a reconciled historical financial ledger.
- Prototype thresholds require representative validation and calibration before production use.
- No real device/location telemetry, live notification service, OTP system or global reputation feed.
- Do not load joblib models from untrusted sources.

Production integration would require authenticated accounts, authorization, secure verification, representative evaluation data, telemetry, moderated reporting, durable deployment storage and provider-approved payment APIs.

## Troubleshooting

| Issue | Fix |
|---|---|
| `app.py` does not exist | Change into the inner project folder containing `app.py` |
| Missing Python module | Install requirements using the same interpreter that runs the app |
| Missing data/model | Run generation, then training |
| Missing timestamps | Regenerate timestamped data and retrain |
| Old logo | Replace `app.py` and put `assets` beside it; restart |
| Old model or generated history | Restart Streamlit after regeneration to clear caches |
| Port in use | Stop the old process or choose another `--server.port` |
| Confirmation leaves transfer pending | Review reasons; this is expected for flagged requests |

## Submission and development transparency

This project was developed with AI assistance for code, interface design and documentation. Team members should review and understand the implementation and disclose assistance as required by the competition.

Keep genuine incremental Git commits. Do not manufacture development history. Add your actual team details and repository/deployment URLs to submission materials. **This package has no deployed URL or deployment configuration.**

## License

No open-source license is assigned in this package. The team should choose and add an appropriate license before distributing it under specific reuse terms.
