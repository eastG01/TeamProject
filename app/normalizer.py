# app/normalizer.py
# F-02: 변형 욕설 정규화
# 순서: 특수문자 제거 → 숫자 욕설 변환 → 영어 발음 변환 → 초성 복원

import re

# ── 숫자 욕설 조합 사전 ────────────────────────────────────────────────────────
# 일반 숫자는 변환하지 않고 욕설로 쓰이는 조합만 변환
NUMBER_SLANG_MAP = {
    "18새끼": "십팔새끼",
    "18놈":   "십팔놈",
    "18년":   "십팔년",
    "18":     "십팔",
}

# ── 영어 발음 → 한글 변환 사전 ───────────────────────────────────────────────
ENGLISH_MAP = {
    "si": "시",
    "bi": "비",
    "fu": "퍼",
    "se": "세",
    "sh": "쉬",
    "ck": "크",
    "ki": "키",
    "ya": "야",
    "mi": "미",
    "na": "나",
}

# ── 초성 → 원형 복원 사전 ────────────────────────────────────────────────────
CHOSUNG_MAP = {
    "ㅅㅂ":   "시발",
    "ㅂㅅ":   "병신",
    "ㅅㄲ":   "새끼",
    "ㅈㄹ":   "지랄",
    "ㄷㅊ":   "닥쳐",
    "ㅁㅊ 놈": "미친 놈",
    "ㅁㅊ 년": "미친 년",
    "ㅁㅊ나":  "미쳤나",
    "ㅁㅊ어":  "미쳤어",
    "ㅁㅊ":    "미친",   # 위에서 못 잡으면 기본값
}


def _remove_special_chars(text: str) -> str:
    """1단계: 특수문자 제거 (한글, 영어, 숫자, 공백만 남김)"""
    return re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]', '', text)


def _replace_number_slang(text: str) -> str:
    """2단계: 욕설 숫자 조합만 한글로 변환 (일반 숫자는 그대로 유지)"""
    for slang, normal in NUMBER_SLANG_MAP.items():
        text = text.replace(slang, normal)
    return text


def _replace_english(text: str) -> str:
    """3단계: 영어 발음 → 한글 변환"""
    lowered = text.lower()
    for eng, kor in ENGLISH_MAP.items():
        lowered = lowered.replace(eng, kor)
    return lowered


def _replace_chosung(text: str) -> str:
    """4단계: 초성 → 원형 복원"""
    for chosung, word in CHOSUNG_MAP.items():
        text = text.replace(chosung, word)
    return text


def normalize(text: str) -> str:
    """
    F-02 전체 정규화 실행
    입력: "si발 ㅅㅂ 시*발 18새끼"
    출력: "시발 시발 시발 십팔새끼"
    """
    text = _remove_special_chars(text)
    text = _replace_number_slang(text)
    text = _replace_english(text)
    text = _replace_chosung(text)
    return text.strip()
