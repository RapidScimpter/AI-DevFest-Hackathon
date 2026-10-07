"""Train the scam-message classifier (character + word TF-IDF, logistic regression).

Evaluated on message bodies that never appear in training.   Run:  python -m pipeline.train_nlp
"""
import json
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, make_pipeline
from app.config import ROOT
from app.ml.nlp import normalise

THRESHOLD = .5


def vectoriser():
    return FeatureUnion([('char', TfidfVectorizer(preprocessor=normalise, analyzer='char_wb', ngram_range=(2, 5), min_df=2, sublinear_tf=True)),
                         ('word', TfidfVectorizer(preprocessor=normalise, analyzer='word', token_pattern=r'\S+', ngram_range=(1, 2), min_df=2, sublinear_tf=True))])


def main():
    df = pd.read_csv(ROOT / 'data/messages.csv')
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=3).split(df, groups=df.body_id))
    train, test = df.iloc[tr], df.iloc[te]
    assert set(train.body_id).isdisjoint(test.body_id)
    scam = make_pipeline(vectoriser(), LogisticRegression(C=4, max_iter=2000, class_weight='balanced')).fit(train.text, train.is_scam)
    category = make_pipeline(vectoriser(), LogisticRegression(C=8, max_iter=3000)).fit(train.text, train.category)
    p = scam.predict_proba(test.text)[:, 1]

    def summary(mask):
        y, q = test.is_scam[mask], p[mask]
        return {'messages': int(mask.sum()), 'precision': float(precision_score(y, q >= THRESHOLD, zero_division=0)),
                'recall': float(recall_score(y, q >= THRESHOLD, zero_division=0)), 'false_positive_rate': float(((q >= THRESHOLD) & (y == 0)).sum() / max((y == 0).sum(), 1))}
    metrics = {'model': 'TF-IDF (character 2-5 grams + word 1-2 grams) + logistic regression', 'threshold': THRESHOLD,
               'train_messages': len(train), 'test_messages': len(test), 'held_out_bodies': int(test.body_id.nunique()),
               'average_precision': float(average_precision_score(test.is_scam, p)), 'brier': float(brier_score_loss(test.is_scam, p)),
               'overall': summary(test.is_scam >= 0), 'by_language': {l: summary(test.language == l) for l in ['en', 'bn', 'bl']},
               'recall_by_scam_category': {c: float((p[(test.category == c).values] >= THRESHOLD).mean()) for c in sorted(test[test.is_scam == 1].category.unique())},
               'category_accuracy': float((category.predict(test.text) == test.category).mean()),
               'note': 'Synthetic messages; test bodies are unseen phrasings. Real scam language will differ.'}
    joblib.dump({'scam': scam, 'category': category, 'threshold': THRESHOLD}, ROOT / 'models/nlp.joblib')
    (ROOT / 'models/nlp_metrics.json').write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=1))


if __name__ == '__main__':
    main()
