import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

_tokenizer = None
_model = None

def load_model():
    global _tokenizer, _model  
    model_path = "my_best_model" 
    print(f"\n[{model_path}] AI 엔진 로딩 중... 잠시만 기다려주세요.")
    try:
        _tokenizer = AutoTokenizer.from_pretrained(model_path)
        _model = AutoModelForSequenceClassification.from_pretrained(model_path, output_attentions=True)
        _model.eval()
        print("로딩 완료  문장을 입력받을 준비가 되었습니다.")
    except Exception as e:
        print(f"로딩 실패: {e}")

def get_pure_score(text: str):
    """단어 조각의 순수 악플 점수 확인 (2차 검증)"""
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = _model(**inputs)
        score = torch.softmax(outputs.logits, dim=-1)[0][1].item()
    return score

def analyze_and_mask():
    if _model is None: load_model()

    print("\n" + "="*75)
    print("AI 정밀 타격 분석기 (띄어쓰기 유무 자동 대응 모드)")
    print(" - 0.49 미만 단어: 문맥 점수가 높아도 구출")
    print(" - 0.70 이상 단어: 문맥 점수가 낮아도 즉시 검거")
    print("="*75)

    while True:
        user_input = input("\n분석할 문장 입력 (종료: exit): ").strip()
        if user_input.lower() in ['exit', 'quit', '종료']: break
        if not user_input: continue

        # 1. 전체 악플 확률 체크
        inputs = _tokenizer(user_input, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = _model(**inputs)
            ai_score = torch.softmax(outputs.logits, dim=-1)[0][1].item()

        print(f"\n[전체 분석] 악플 확률: {ai_score:.2%}")

        if ai_score < 0.7:
            print(f"결과: {user_input}")
            continue

        # 2. 가중치(Attention) 분석
        attentions = outputs.attentions[-1][0].mean(dim=0)[0].cpu().detach().numpy()
        tokens = _tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        
        # 기준점(Threshold) 계산
        valid_scores = [attentions[i] for i, t in enumerate(tokens) if t not in [_tokenizer.cls_token, _tokenizer.sep_token]]
        threshold = max(min(np.mean(valid_scores) + np.std(valid_scores), 0.20), 0.12)

        # 3. 글자 단위 정밀 매칭 마스킹
        # 원문의 글자 하나하나를 보존하면서 마스킹 여부만 결정함
        final_output = ""
        current_char_ptr = 0 # 원문 글자를 가리키는 포인터
        
        print(f"기준점: {threshold:.4f}")
        print(f"{'토큰':<15} | {'문맥점수':<8} | {'단독점수':<8} | {'판단'}")
        print("-" * 75)

        for i, token in enumerate(tokens):
            if token in [_tokenizer.cls_token, _tokenizer.sep_token]: continue
            
            clean_token = token.replace("##", "")
            indiv_score = get_pure_score(clean_token)
            
            # 마스킹 조건 적용
            is_bad = (attentions[i] > threshold and indiv_score >= 0.49) or (indiv_score > 0.7)
            status = "마스킹 ★" if is_bad else "생존"
            print(f"[{token:<13}] | {attentions[i]:.4f} | {indiv_score:.4f} | {status}")

            # 원문의 글자와 토큰 매칭 (띄어쓰기 보존 로직)
            match_count = 0
            while match_count < len(clean_token) and current_char_ptr < len(user_input):
                char = user_input[current_char_ptr]
                
                if char == " ": # 공백은 무조건 그대로 통과
                    final_output += " "
                    current_char_ptr += 1
                    continue
                
                # 글자 매칭 및 마스킹 처리
                final_output += "*" if is_bad else char
                match_count += 1
                current_char_ptr += 1

        # 남은 공백 처리
        if current_char_ptr < len(user_input):
            final_output += user_input[current_char_ptr:]

        print("-" * 75)
        print(f"최종 결과: {final_output}")

if __name__ == "__main__":
    analyze_and_mask()