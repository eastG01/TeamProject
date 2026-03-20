# app/filter_service.py
from app.normalizer import normalize
from app.database   import match_badword, save_filter_log, update_user_penalty, get_user_status
from app.model      import predict, THRESHOLD_HATE, THRESHOLD_REVIEW


def run_filter(user_id: str, text: str) -> dict:

    # F-01: 댓글 수신
    original_text = text.strip()

    # 차단된 유저 확인
    user_status = get_user_status(user_id)
    if user_status == "차단":
        return {
            "result": "차단된 유저", "action": "차단", "method": "유저차단",
            "ai_score": None, "final_text": None, "warning_count": None,
            "user_status": "차단", "detected_word": None
        }

    # F-02: 정규화
    normalized_text = normalize(original_text)

    # F-03: 욕설 사전 1차 필터링
    detected_word = match_badword(normalized_text)

    if detected_word:
        save_filter_log(
            user_id=user_id, original_text=original_text,
            normalized_text=normalized_text, detect_method="욕설사전",
            result="악플", action="차단",
            detected_word=detected_word, ai_score=None
        )
        penalty = update_user_penalty(user_id)
        return {
            "result": "악플", "action": "차단", "method": "욕설사전",
            "ai_score": None, "final_text": None,
            "warning_count": penalty["warning_count"],
            "user_status": penalty["status"],
            "detected_word": detected_word  # ← 마스킹에 사용
        }

    # F-04: KcBERT 2차 분석
    ai_score = predict(normalized_text)

    # F-05: 임계값 판단
    if ai_score >= THRESHOLD_HATE:
        result, action = "악플", "차단"
    elif ai_score >= THRESHOLD_REVIEW:
        result, action = "보류", "대기"
    else:
        result, action = "정상", "통과"

    save_filter_log(
        user_id=user_id, original_text=original_text,
        normalized_text=normalized_text, detect_method="KcBERT",
        result=result, action=action,
        detected_word=None, ai_score=ai_score
    )

    penalty_info = None
    if result == "악플":
        penalty_info = update_user_penalty(user_id)

    # F-07: 정상이면 original_text 복원
    final_text = original_text if result == "정상" else None

    return {
        "result": result, "action": action, "method": "KcBERT",
        "ai_score": ai_score, "final_text": final_text,
        "warning_count": penalty_info["warning_count"] if penalty_info else None,
        "user_status": penalty_info["status"] if penalty_info else get_user_status(user_id),
        "detected_word": None  # KcBERT면 NULL
    }
