"""Regenerate data and retrain every model.   Run:  python -m pipeline.build_all"""
from . import export_demo, generate_data, generate_messages, train_fraud, train_nlp

if __name__ == '__main__':
    for step in (generate_data, generate_messages, train_fraud, train_nlp, export_demo):
        print(f'\n=== {step.__name__} ==='); step.main()
