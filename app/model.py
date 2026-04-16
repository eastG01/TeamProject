# app/model.py
# KcBERT 모델을 서버 시작 시 딱 한 번만 메모리에 로드

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# 전역 변수로 모델 보관 (서버 메모리에 상주)
_tokenizer = None
_model = None
THRESHOLD_HATE   = 0.7   # 이상 → 악플
THRESHOLD_REVIEW = 0.5   # 이상 → 보류


def load_model():
    """서버 시작 시 딱 한 번 호출"""
    global _tokenizer, _model
    print("KcBERT 모델 로딩 중...")
    _tokenizer = AutoTokenizer.from_pretrained("my_best_model")
    _model     = AutoModelForSequenceClassification.from_pretrained("my_best_model")
    _model.eval()
    print("KcBERT 모델 로딩 완료 ✅")


def predict(text: str) -> float:
    """
    텍스트를 받아 악플 확률(0.0 ~ 1.0) 반환
    - 0.7 이상 → 악플
    - 0.5 ~ 0.7 → 보류
    - 0.5 미만  → 정상
    """
    if _model is None or _tokenizer is None:
        raise RuntimeError("모델이 아직 로드되지 않았습니다.")

    inputs = _tokenizer(
        text,
        return_tensors="pt",
        max_length=128,
        truncation=True,
        padding=True
    )

    with torch.no_grad():
        outputs = _model(**inputs)
        probs   = torch.softmax(outputs.logits, dim=-1)
        # index 1 = 악플 확률
        hate_score = probs[0][1].item()

    return round(hate_score, 4)
