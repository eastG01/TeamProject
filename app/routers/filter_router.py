# app/routers/filter_router.py
from fastapi           import APIRouter, HTTPException
from pydantic          import BaseModel
from typing            import Optional
from app.filter_service import run_filter

router = APIRouter(prefix="/api", tags=["필터링"])


class FilterRequest(BaseModel):
    user_id: str
    text:    str
    class Config:
        json_schema_extra = {"example": {"user_id": "user_001", "text": "si발 꺼져"}}


class FilterResponse(BaseModel):
    result:        str
    action:        str
    method:        str
    ai_score:      Optional[float]
    final_text:    Optional[str]
    warning_count: Optional[int]
    user_status:   str
    detected_word: Optional[str]  # 욕설사전 매칭된 단어 (마스킹에 사용)


@router.post("/filter", response_model=FilterResponse, summary="댓글 악플 필터링")
async def filter_comment(req: FilterRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="댓글 내용이 비어있습니다.")
    if len(req.text) > 500:
        raise HTTPException(status_code=400, detail="댓글은 500자를 초과할 수 없습니다.")
    result = run_filter(user_id=req.user_id, text=req.text)
    return FilterResponse(**result)
