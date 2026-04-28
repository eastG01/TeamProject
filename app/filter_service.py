# app/filter_service.py
from app.normalizer import normalize
from app.database   import match_badword, save_filter_log, update_user_penalty, get_user_status
from app.model      import predict_and_mask, THRESHOLD_HATE, THRESHOLD_REVIEW

def run_filter(user_id: str, text: str) -> dict:
    original_text = text.strip()
    user_status = get_user_status(user_id)
    if user_status == "차단":
        return {"result": "차단된 유저", "action": "차단", "method": "유저차단", "ai_score": None, "final_text": None, "user_status": "차단"}

    normalized_text = normalize(original_text)

    detected_word = match_badword(normalized_text)

    ai_score, ai_masked_text = predict_and_mask(normalized_text)

    if detected_word:
        # 욕설사전 마스킹 + KcBERT 마스킹 결합
        final_text = ai_masked_text.replace(detected_word, "*" * len(detected_word)) if ai_score >= THRESHOLD_HATE else original_text.replace(detected_word, "*" * len(detected_word))
        save_filter_log(user_id, original_text, normalized_text, "욕설사전", "악플", "차단", detected_word)
        penalty = update_user_penalty(user_id)
        return {"result": "악플", "action": "차단", "method": "욕설사전", "ai_score": ai_score, "final_text": final_text, "user_status": penalty["status"]}

    # 임계값 판단
    if ai_score >= THRESHOLD_HATE:
        result, action = "악플", "차단"
    elif ai_score >= THRESHOLD_REVIEW:
        result, action = "보류", "대기"
    else:
        result, action = "정상", "통과"

    save_filter_log(user_id, original_text, normalized_text, "KcBERT", result, action, None, ai_score)
    penalty_info = update_user_penalty(user_id) if result == "악플" else None
    
    return {
        "result": result,
        "action": action,
        "method": "KcBERT",
        "ai_score": ai_score,
        "final_text": ai_masked_text if result in ["악플", "보류"] else original_text,
        "user_status": penalty_info["status"] if penalty_info else (user_status or "정상")
    }