# AccountGuard AI — beginner setup guide

A runnable ML prototype for detecting possible account takeover in mobile financial services. It generates synthetic events, trains a Random Forest, and presents transaction scoring in Streamlit. No real customers, financial transactions, OTPs, or upay integration are involved.

## 1. Install the tools

Install Python 3.11 or 3.12 from https://www.python.org/downloads/ . On Windows, select **Add Python to PATH** during installation. Install VS Code from https://code.visualstudio.com/ . Install Git from https://git-scm.com/downloads/ if using terminal Git, or use GitHub Desktop.

## 2. Extract and open this project

Extract AccountGuard-AI.zip. Open the extracted **AccountGuard-AI** folder in VS Code using File → Open Folder. Choose Terminal → New Terminal. The terminal must be inside the folder containing requirements.txt and app.py. Do not type the Markdown backticks around commands.

## 3. Create a Python environment

Windows Command Prompt (in VS Code choose the terminal dropdown → Command Prompt):

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

If `py` is unavailable, try `python -m venv .venv` for the first command.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The environment keeps this project's packages together. Internet access is needed to install packages; the demo needs no external API key.

## 4. Generate the data

```bash
python src/generate_data.py
```

Expected: `Created 24000 events and 600 synthetic profiles.` This creates data/transactions.csv and data/profiles.json. Do not edit the label to influence a prediction. The label is used only for training and evaluation.

## 5. Train and evaluate

```bash
python src/train.py
```

This creates models/model.joblib and models/metrics.json. It prints precision, recall, F1, average precision (PR-AUC summary), false-positive rate and confusion matrix. The confusion matrix has rows actual normal/attack and columns predicted normal/attack. The model uses a fixed 0.40 review threshold; high risk starts at 0.70.

Different users are held out for testing. User IDs, transaction IDs and labels are never model inputs. Trusted profiles stand in for an earlier enrollment/history period; this first version does not compute rolling history from timestamps.

## 6. Run a basic check

```bash
python tests/smoke.py
```

Expected: `Smoke checks passed` and two scores. A conspicuous attack should score above a normal transfer, and amounts above balance should be rejected.

## 7. Open the dashboard

```bash
python -m streamlit run app.py
```

Open the Local URL printed in the terminal, usually http://localhost:8501 . Leave the terminal running. Press Ctrl+C to stop it.

1. Select a synthetic customer in the sidebar.
2. Choose Everyday payment and click Analyze transaction.
3. Choose Possible account takeover and click Analyze transaction.
4. Compare scores and signals.
5. Try New phone & travel. This demonstrates why unfamiliar behavior alone must not be treated as proof of fraud.
6. Change the amount or failed PIN count and score again.
7. Open evaluation results to discuss false positives and missed attacks.

Signals are readable feature flags, not model attribution. The Random Forest score is uncalibrated and should be called a **model risk score**, not a confirmed probability of fraud. Step-up verification is a simulation only.

## 8. Start your actual GitHub history now

Create a public repository called AccountGuard-AI on GitHub. Keep README initialization unchecked if importing this existing folder. With GitHub Desktop: File → Add local repository → select this folder → create repository if asked. Review files, commit with an honest message such as `feat: add assisted synthetic-data ML starter`, and Publish repository with the private checkbox unchecked.

Or, after creating an empty GitHub repository:

```bash
git init
git add .
git commit -m "feat: add assisted synthetic-data ML starter"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/AccountGuard-AI.git
git push -u origin main
```

Replace YOUR_USERNAME. If Git requests identity, set your own name and email. Use GitHub Desktop/browser authentication rather than putting a token in code. Do not invent earlier commits: this starter was generated together. Commit each real change from now on and disclose AI assistance as required.

## 9. Understand the files

| File | Purpose |
|---|---|
| src/generate_data.py | Reproducible synthetic profiles and labeled events |
| src/core.py | Shared feature builder, scoring and signal descriptions |
| src/train.py | Model training and user-disjoint evaluation |
| app.py | Dashboard and editable demo event |
| tests/smoke.py | Normal/attack scoring and invalid-balance checks |
| requirements.txt | Python packages |
| .gitignore | Excludes generated data, model and local environment |

The synthetic generator contains legitimate unusual behavior and subtle attacks. Labels influence how synthetic events are sampled, not how feature extraction calculates values. Dataset assumptions still create bias: performance only measures this simulator, and attackers in the real world may behave very differently.

## 10. Next improvements for the competition

First get this version running on each teammate's laptop. Then commit actual improvements:

- Add timestamped history and calculate counts/medians from earlier events only.
- Compare the model against a simple rule baseline on the same held-out users.
- Add validation data for threshold selection/calibration; keep test labels untouched.
- Add SHAP explanations if you can validate their interpretation.
- Measure scoring latency and analyze legitimate travel/new-phone false positives.
- Add a FastAPI endpoint only if another frontend or integration needs it.
- Deploy a demo, record the video and prepare the report; deployment is not included here.

For a report, document problem, synthetic-data assumptions, model/features, split method, metrics, simulated action, privacy limitations and future integration. Keep the presentation honest about the prototype's scope.

## Troubleshooting

- `No module named ...`: activate .venv and run `python -m pip install -r requirements.txt` again.
- `can't open file`: open the terminal in the folder containing app.py.
- Missing transactions.csv: run generation before training.
- Missing model.joblib: run training before opening the dashboard.
- Windows PowerShell blocks activation: switch to Command Prompt and use the Windows commands above.
- Browser does not open: copy the Local URL from the Streamlit terminal.
- Changing data/model files: stop the dashboard, rerun generation/training as appropriate, then restart so its cached model refreshes.

Never load a joblib model from an untrusted source. There are no secrets required; never commit actual customer information or credentials.

## Investigation interface update

To update an existing installation, copy app.py, src/review.py and .streamlit/config.toml into matching locations. Stop and restart Streamlit. No retraining is needed.

The raw model score is unchanged. A separate, explicit demo policy considers simulated trusted-channel travel/device verification. Unexplained novelty asks for context; corroborating concerns ask for further investigation. Verified travel alone never overrides rapid transfers, repeated PIN failures or a large transfer to a new recipient. No event receives a confirmed-fraud verdict. This policy has not been evaluated by the model metrics. Checkboxes simulate verification, not actual identity checks.

Light theme, higher contrast, entrance/hover animation and reduced-motion support improve readability. If your browser retained dark mode, select Light in Streamlit Settings.
