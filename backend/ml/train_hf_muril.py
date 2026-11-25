"""Fine-tune google/muril-base-cased on NityaMed's leak-free multilingual dataset.

Run this script on Google Colab (free T4 GPU) or a machine with PyTorch + Transformers installed:
    pip install transformers datasets torch scikit-learn accelerate
    python -m ml.train_hf_muril --output_dir ./ml/artifacts/muril_nityamed
"""

import argparse
from pathlib import Path

from sklearn.model_selection import StratifiedGroupKFold

from ml.dataset import build_multilingual_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune MuRIL for NityaMed intent routing")
    parser.add_argument("--model_name", default="google/muril-base-cased")
    parser.add_argument("--output_dir", default="./ml/artifacts/muril_nityamed")
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch_size", type=int, default=16)
    args = parser.parse_args()

    try:
        from datasets import Dataset
        import numpy as np
        from sklearn.metrics import accuracy_score, f1_score
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Install Hugging Face dependencies first: pip install transformers datasets torch scikit-learn accelerate"
        ) from exc

    samples = build_multilingual_dataset()
    labels = sorted({s.intent for s in samples})
    label2id = {lbl: idx for idx, lbl in enumerate(labels)}
    id2label = {idx: lbl for lbl, idx in label2id.items()}

    texts = [s.text for s in samples]
    y = [label2id[s.intent] for s in samples]
    groups = [s.family_id for s in samples]

    # Leak-free 80/20 split grouped by family_id
    sgkf = StratifiedGroupKFold(n_splits=5)
    train_idx, val_idx = next(sgkf.split(texts, y, groups))
    assert set(groups[i] for i in train_idx).isdisjoint({groups[i] for i in val_idx})

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    def _make_ds(indices):
        ds = Dataset.from_dict({
            "text": [texts[i] for i in indices],
            "label": [y[i] for i in indices],
        })
        return ds.map(lambda b: tokenizer(b["text"], truncation=True, padding="max_length", max_length=96), batched=True)

    train_ds = _make_ds(train_idx)
    val_ds = _make_ds(val_idx)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )

    def compute_metrics(eval_pred):
        logits, true_y = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {
            "accuracy": float(accuracy_score(true_y, preds)),
            "macro_f1": float(f1_score(true_y, preds, average="macro", zero_division=0)),
        }

    out_path = Path(args.output_dir)
    training_args = TrainingArguments(
        output_dir=str(out_path / "checkpoints"),
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=3e-5,
        weight_decay=0.01,
        logging_steps=20,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    eval_metrics = trainer.evaluate()
    print("MuRIL validation metrics (leak-free fold):", eval_metrics)

    out_path.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(out_path))
    tokenizer.save_pretrained(str(out_path))
    print(f"Saved fine-tuned MuRIL model to {out_path.resolve()}")


if __name__ == "__main__":
    main()
