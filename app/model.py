import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 전역 변수
_tokenizer = None
_model = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 임계값 통일 설정
THRESHOLD_HATE = 0.70   # 악플 기준
THRESHOLD_REVIEW = 0.50 # 보류 기준

def load_model():
    global _tokenizer, _model
    if _model is not None:
        return
    
    model_path = "my_best_model"
    _tokenizer = AutoTokenizer.from_pretrained(model_path)
    _model = AutoModelForSequenceClassification.from_pretrained(
        model_path, output_attentions=True
    )
    _model.to(_device)
    _model.eval()

def predict_and_mask(user_input: str):
    if not user_input.strip() or _model is None:
        return 0.0, user_input

    inputs = _tokenizer(user_input, return_tensors="pt", truncation=True, padding=True).to(_device)
    with torch.no_grad():
        outputs = _model(**inputs)
        ai_score = torch.softmax(outputs.logits, dim=-1)[0][1].item()

    if ai_score < THRESHOLD_HATE:
        return ai_score, user_input

    tokens = _tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    attentions = outputs.attentions[-1][0].mean(dim=0)[0].cpu().detach().numpy()

    valid_indices = [i for i, t in enumerate(tokens) if t not in [_tokenizer.cls_token, _tokenizer.sep_token]]
    valid_attn_scores = [attentions[i] for i in valid_indices]
    attn_limit = max(min(np.mean(valid_attn_scores) + np.std(valid_attn_scores), 0.20), 0.12)

    final_output = ""
    ptr = 0
    for i in valid_indices:
        clean_t = tokens[i].replace("##", "")
        indiv_inputs = _tokenizer(clean_t, return_tensors="pt").to(_device)
        with torch.no_grad():
            indiv_outputs = _model(**indiv_inputs)
            indiv_score = torch.softmax(indiv_outputs.logits, dim=-1)[0][1].item()

        is_bad = (attentions[i] > attn_limit and indiv_score >= 0.49) or (indiv_score > THRESHOLD_HATE)

        m_count = 0
        while m_count < len(clean_t) and ptr < len(user_input):
            if user_input[ptr] == " ":
                final_output += " "; ptr += 1; continue
            final_output += "*" if is_bad else user_input[ptr]
            m_count += 1; ptr += 1

    return ai_score, final_output + user_input[ptr:]