"""Lightweight FastAPI server for hosting fine-tuned NityaMed MuRIL on Hugging Face Spaces (16 GB free CPU)."""

import os

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

MODEL_ID_OR_PATH = os.getenv("MURIL_MODEL_PATH", "./muril_nityamed")

app = FastAPI(title="NityaMed MuRIL Intent Classifier Space")
classifier = pipeline("text-classification", model=MODEL_ID_OR_PATH, tokenizer=MODEL_ID_OR_PATH)


class ClassifyRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_ID_OR_PATH}


@app.post("/classify")
def classify(req: ClassifyRequest) -> dict[str, float | str]:
    out = classifier(req.text, truncation=True, max_length=96)[0]
    return {"intent": str(out["label"]), "confidence": round(float(out["score"]), 4)}
