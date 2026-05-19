import pandas as pd
import torch
from datasets import load_dataset, Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
from sklearn.metrics import f1_score, accuracy_score
import numpy as np

MODEL_PATH = "my_best_model"
OUTPUT_PATH = "my_best_model_finetuned"
FP_CSV = "fn_cases.csv"
MAX_LENGTH = 64

# 1. 기존 데이터셋 로드 (kor_unsmile)
print("기존 데이터셋 로딩 중...")
original = load_dataset("jeanlee/kmhas_korean_hate_speech")
df_original = pd.DataFrame({
    "text": original["train"]["text"],
    "label": [0 if l == 1 else 1 for l in original["train"]["label"]]  # clean=1→정상(0), clean=0→악플(1)
})

# 2. 오탐 데이터 로드 (fn_cases.csv)
print("오탐 데이터 로딩 중...")
df_fp = pd.read_csv(FP_CSV)
df_fp = df_fp[["comment", "label"]].rename(columns={"comment": "text"})

# 3. 합치기
df_all = pd.concat([df_original, df_fp], ignore_index=True).dropna()
df_all = df_all.sample(frac=1, random_state=42).reset_index(drop=True)

print(f"전체 데이터: {len(df_all)}개 (정상: {(df_all['label']==0).sum()}, 악플: {(df_all['label']==1).sum()})")

# 4. train/val 분리 (9:1)
split = int(len(df_all) * 0.9)
df_train = df_all[:split]
df_val   = df_all[split:]

# 5. 토크나이저
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

def tokenize(batch):
    return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=MAX_LENGTH)

train_dataset = Dataset.from_pandas(df_train).map(tokenize, batched=True)
val_dataset   = Dataset.from_pandas(df_val).map(tokenize, batched=True)
train_dataset.set_format("torch", columns=["input_ids", "attention_mask", "label"])
val_dataset.set_format("torch", columns=["input_ids", "attention_mask", "label"])

# 6. 모델 로드
print("모델 로딩 중...")
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=2)

# 7. 평가 함수
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds, average="binary")
    }

# 8. 학습 설정
args = TrainingArguments(
    output_dir=OUTPUT_PATH,
    num_train_epochs=3,
    learning_rate=1e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    logging_steps=50,
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
)

# 9. 파인튜닝
print("파인튜닝 시작...")
trainer.train()

# 10. 저장
trainer.save_model(OUTPUT_PATH)
tokenizer.save_pretrained(OUTPUT_PATH)
print(f"완료. 모델 저장: {OUTPUT_PATH}")
