"""Train and evaluate NityaMed multilingual intent classifiers with zero data leakage.

Uses StratifiedGroupKFold grouped by template `family_id` so paraphrases, spelling
typos, and ASR errors from the same family never leak between training and test folds.
"""

from collections import defaultdict
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from app.modules.assistant.nlp import normalize_text
from ml.dataset import UtteranceSample, build_multilingual_dataset

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "intent_classifier.joblib"
REPORT_PATH = ARTIFACTS_DIR / "benchmark_report.json"
OOS_CONFIDENCE_THRESHOLD = 0.28
# Preserve Indic Unicode combining marks (Kannada/Devanagari matras) inside tokens.
INDIC_TOKEN_PATTERN = r"[^\s?.!,;:\"'()\[\]{}]+"


def _build_hybrid_features() -> FeatureUnion:
    """Build combined Indic-safe word + character n-gram TF-IDF feature union."""
    return FeatureUnion([
        (
            "word",
            TfidfVectorizer(
                ngram_range=(1, 3),
                token_pattern=INDIC_TOKEN_PATTERN,
                lowercase=True,
                sublinear_tf=True,
            ),
        ),
        (
            "char",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 6),
                lowercase=True,
                sublinear_tf=True,
            ),
        ),
    ])


def _build_candidate_pipelines() -> dict[str, Pipeline]:
    """Construct candidate classification pipelines from lightweight baseline to hybrid ensemble."""
    word_logreg = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                token_pattern=INDIC_TOKEN_PATTERN,
                lowercase=True,
                sublinear_tf=True,
            ),
        ),
        ("clf", LogisticRegression(max_iter=2500, C=4.0, class_weight="balanced")),
    ])

    hybrid_logreg = Pipeline([
        ("features", _build_hybrid_features()),
        ("clf", LogisticRegression(max_iter=2500, C=5.0, class_weight="balanced")),
    ])

    hybrid_svm = Pipeline([
        ("features", _build_hybrid_features()),
        ("clf", CalibratedClassifierCV(LinearSVC(C=1.2, class_weight="balanced"), cv=3)),
    ])

    hybrid_ensemble = Pipeline([
        ("features", _build_hybrid_features()),
        (
            "clf",
            VotingClassifier(
                estimators=[
                    ("lr", LogisticRegression(max_iter=2500, C=5.0, class_weight="balanced")),
                    ("svm", CalibratedClassifierCV(LinearSVC(C=1.2, class_weight="balanced"), cv=3)),
                    ("cnb", ComplementNB(alpha=0.3)),
                ],
                voting="soft",
                weights=[2.0, 2.0, 1.0],
            ),
        ),
    ])

    return {
        "word_tfidf_logreg": word_logreg,
        "hybrid_tfidf_logreg": hybrid_logreg,
        "hybrid_tfidf_calibrated_svm": hybrid_svm,
        "hybrid_tfidf_soft_ensemble": hybrid_ensemble,
    }


def evaluate_models(samples: list[UtteranceSample] | None = None, n_splits: int = 5) -> dict:
    """Run leak-free StratifiedGroupKFold cross-validation across candidate models."""
    data = samples or build_multilingual_dataset()
    texts = np.array([normalize_text(s.text) for s in data])
    labels = np.array([s.intent for s in data])
    groups = np.array([s.family_id for s in data])
    langs = np.array([s.lang_group for s in data])

    splitter = StratifiedGroupKFold(n_splits=n_splits)
    results: dict[str, dict] = {}
    unique_labels = sorted(set(labels))

    for name, base_pipeline in _build_candidate_pipelines().items():
        oof_preds = np.empty(len(data), dtype=object)
        oof_confs = np.zeros(len(data), dtype=float)

        for train_idx, test_idx in splitter.split(texts, labels, groups):
            # Assert zero family leakage between train and test splits
            assert set(groups[train_idx]).isdisjoint(set(groups[test_idx]))

            model = _build_candidate_pipelines()[name]
            model.fit(texts[train_idx], labels[train_idx])
            probs = model.predict_proba(texts[test_idx])
            best_idx = np.argmax(probs, axis=1)
            raw_preds = model.classes_[best_idx]
            confs = probs[np.arange(len(test_idx)), best_idx]
            # Confidence threshold rejects ambiguous/unseen inputs to out_of_scope
            oof_preds[test_idx] = np.where(confs < OOS_CONFIDENCE_THRESHOLD, "out_of_scope", raw_preds)
            oof_confs[test_idx] = confs

        acc = float(accuracy_score(labels, oof_preds))
        macro_f1 = float(f1_score(labels, oof_preds, average="macro", zero_division=0))
        cls_report = classification_report(
            labels, oof_preds, labels=unique_labels, output_dict=True, zero_division=0
        )
        cm = confusion_matrix(labels, oof_preds, labels=unique_labels).tolist()

        # Per-language accuracy & macro-F1 breakdown
        per_lang: dict[str, dict[str, float | int]] = {}
        lang_indices: dict[str, list[int]] = defaultdict(list)
        for idx, lg in enumerate(langs):
            lang_indices[str(lg)].append(idx)

        for lg, idxs in sorted(lang_indices.items()):
            lg_true = labels[idxs]
            lg_pred = oof_preds[idxs]
            per_lang[lg] = {
                "count": len(idxs),
                "accuracy": round(float(accuracy_score(lg_true, lg_pred)), 4),
                "macro_f1": round(float(f1_score(lg_true, lg_pred, average="macro", zero_division=0)), 4),
            }

        oos_mask = labels == "out_of_scope"
        oos_recall = float(np.mean(oof_preds[oos_mask] == "out_of_scope")) if np.any(oos_mask) else 0.0

        results[name] = {
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "macro_precision": round(float(cls_report["macro avg"]["precision"]), 4),
            "macro_recall": round(float(cls_report["macro avg"]["recall"]), 4),
            "oos_recall": round(oos_recall, 4),
            "per_language": per_lang,
            "labels": unique_labels,
            "confusion_matrix": cm,
        }

    return {
        "dataset_size": len(data),
        "unique_families": len(set(groups)),
        "n_splits": n_splits,
        "models": results,
    }


def train_and_save_best(output_model_path: Path = MODEL_PATH, report_path: Path = REPORT_PATH) -> dict:
    """Benchmark candidates, pick highest macro-F1 model, train on full dataset, and save artifact."""
    samples = build_multilingual_dataset()
    report = evaluate_models(samples)

    best_name = max(
        report["models"].keys(),
        key=lambda m: (
            round(report["models"][m]["macro_f1"] * 0.8 + report["models"][m]["oos_recall"] * 0.2, 4),
            report["models"][m]["macro_f1"],
            report["models"][m]["accuracy"],
        ),
    )
    report["selected_model"] = best_name

    best_pipeline = _build_candidate_pipelines()[best_name]
    texts = [normalize_text(s.text) for s in samples]
    labels = [s.intent for s in samples]
    best_pipeline.fit(texts, labels)

    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, output_model_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    summary = train_and_save_best()
    print(json.dumps({
        "dataset_size": summary["dataset_size"],
        "unique_families": summary["unique_families"],
        "selected_model": summary["selected_model"],
        "scores": {
            k: {
                "accuracy": v["accuracy"],
                "macro_f1": v["macro_f1"],
                "oos_recall": v["oos_recall"],
            }
            for k, v in summary["models"].items()
        },
    }, indent=2))
