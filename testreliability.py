import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def check_reliability():
    model_path = "my_best_model"
    
    print(f"모델 로딩 중...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        model.eval()
        print("로딩 완료! 분석을 시작합니다. (종료: exit)")
    except Exception as e:
        print(f"모델을 찾을 수 없습니다: {e}")
        return

    while True:
        text = input("\n테스트할 문장 입력: ").strip()
        
        if text.lower() in ['exit', 'quit', '종료']:
            break
        if not text:
            continue

        # 1. 토큰화 및 모델 입력
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        
        # 2. 확률 계산
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            
            hate_score = probs[0][1].item() 

        # 3. 결과 출력
        print(f"---------------------------------")
        print(f"입력 문장: {text}")
        print(f"악플 확률: {hate_score:.2%}")
        
        
        if hate_score >= 0.7:
            print("결과: [위험] 악플입니다.")
        elif hate_score >= 0.5:
            print("결 result: [보류] 악플 가능성이 있습니다.")
        else:
            print("결과: [정상] 깨끗한 문장입니다.")
        print(f"---------------------------------")

if __name__ == "__main__":
    check_reliability()