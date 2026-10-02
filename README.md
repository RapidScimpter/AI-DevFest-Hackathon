# AccountGuard AI

Behavioral transaction review with context, synthetic history, investigation cases and call/text screening. Independent hackathon prototype; no upay connection or real transaction processing.

## Upgrade an existing project

Stop Streamlit with Ctrl+C. Extract the latest ZIP separately. Copy app.py, requirements.txt, README.md, the entire src and tests folders, and .streamlit into your existing project. Keep your existing .venv and .git directories. Do not overwrite a Git repository with a fresh repository.

In your project terminal run, one command at a time:

```powershell
python -m pip install -r requirements.txt
python src/generate_data.py
python src/train.py
python tests/smoke.py
python -m streamlit run app.py
```

This version requires regeneration and retraining. It replaces generated synthetic data and the model; export any session cases/logs first. No external APIs or keys are required. Open http://localhost:8501 if the browser does not open.

## First-time setup on Windows

Install Python 3.11 or 3.12 with Add Python to PATH. Extract the ZIP and open the inner AccountGuard-AI folder in VS Code. Open a Command Prompt terminal:

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python src/generate_data.py
python src/train.py
python tests/smoke.py
python -m streamlit run app.py
```

On macOS/Linux use python3 -m venv .venv and source .venv/bin/activate, then the same Python commands.

## Use the dashboard

1. Transaction review: choose a customer and expand recent history. Select an example and edit amount, recipient, device, district or date/time. Click Analyze transaction.
2. The system calculates the baseline and recent transfer count from earlier events. The takeover demo injects three explicitly simulated earlier transfers at minus 8, 5 and 2 minutes.
3. Investigation cases: open the generated case, choose a simulated customer response and click Record simulated response. Travel/device confirmation explains novelty but does not override other concerning evidence.
4. Select a reviewer outcome, add notes and save. Unreachable customers keep cases pending. Reported unauthorized activity requires a recorded denial; contradictory legitimate outcomes are rejected.
5. Activity log: view and download the session investigation trail. Cases and logs are browser-session state, not durable storage. Refreshing or restarting can lose them.
6. Model performance: inspect held-out synthetic-user metrics and a basic-rule comparison.
7. Call & text check: enter a number and optional text. Number format and selected English/Bengali warning phrases are screened. Locally submitted reports are shown as unverified evidence; caller identity is not verified. Numbers with no reports remain unverified.

## What changed in the ML pipeline

The generator creates 200 customers with 90 events each. First 20 events per customer are warm-up history and excluded from model fitting/evaluation. Each later event is featurized using only same-customer events with strictly earlier timestamps. Amount median, common district, known devices/recipients and usual-hour range use the last 50 earlier events. Previous-ten-minute count uses earlier event timestamps. Attack labels and future events are never profile inputs.

Profiles include all previous observations, which can include suspicious transactions; real systems would need trusted-profile update controls against poisoning. Known-recipient membership is not equivalent to safety. Failed PIN count is a supplied session observation in this demo, not retrieved from authentication telemetry. Historical balances are simulated independently, not a reconciled financial ledger.

Random Forest evaluation holds out customers, uses a fixed 0.40 review threshold and reports precision, recall, F1, average precision and false-positive rate. A basic rule (new device AND amount above 3 times median) is evaluated on identical held-out events. Synthetic behavior overlaps between classes; these metrics do not establish production performance. Scores remain uncalibrated.

The separate investigation policy is a transparent demo rule layer, not a second trained model. Readable signals are feature flags, not SHAP contributions. Simulated customer confirmation is not real verification. The reviewer outcome is not independently confirmed fraud. No OTP is sent, account blocked or payment approved.

## Files

| File | Purpose |
|---|---|
| src/history.py | Strictly prior-history profile and counts |
| src/generate_data.py | Timestamped synthetic event generation |
| src/core.py | Feature definitions and ML scoring |
| src/train.py | User-disjoint evaluation and rule comparison |
| src/review.py | Context-aware investigation policy |
| src/contact_check.py | Number formatting and message phrase screening |
| app.py | Dashboard, case workflow and session log |
| tests/smoke.py | Future/label isolation, counts and verification checks |
| .streamlit/config.toml | Readable light theme |

## GitHub and submission

Commit actual work as it happens. Do not manufacture earlier history. The starter and updates were AI-assisted; disclose assistance as required and ensure teammates understand the implementation. Generated data/models and .venv are ignored; reviewers recreate them with the commands above. Do not publish real customer details, credentials or secrets.

For the report/video include the problem, synthetic-data assumptions, strictly prior features, split method, baseline comparison, verification limitations and one legitimate travel case alongside a suspicious case. Deployment and production integrations are not included.

## Troubleshooting

Missing module: install requirements with the same python interpreter you run. Missing timestamps: regenerate data and retrain. After changing generated data/models, restart Streamlit to clear caches. A transaction too early in history is rejected because it has fewer than 10 prior events. PowerShell activation issues: use Command Prompt. Never load joblib models from untrusted sources.

## Persistent call/text reports

Copy updated app.py, src/contact_check.py and the new src/reports.py into an existing installation. No regeneration or retraining is needed for this update.

Report call / text stores a normalized number, category, channel, sanitized user-provided evidence and UTC timestamp in data/contact_reports.sqlite3. Call & text check reads number reports and exact text-message matches (case/whitespace normalized, minimum 20 characters). Identical number/channel/category/text submissions are deduplicated. Reports are unverified allegations, not independent-victim counts or confirmed fraud. No lookup query is stored and no ML retraining occurs.

The database survives restarts on the same computer. Keep it private and out of Git. Back it up only to a trusted location; deleting this database deletes the local reports. Separate installations do not synchronize. Deploying for public use requires authentication, moderation, abuse controls and appropriate data handling; this version is a local prototype.
