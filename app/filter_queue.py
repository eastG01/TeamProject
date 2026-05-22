from app.filter_service import filter_and_update_comment

# 추상화 레이어: 현재는 BackgroundTasks 사용, 향후 Kafka 등으로 교체 가능
def enqueue_filter_task(background_tasks, comment_id: int, user_id: str, content: str):
    background_tasks.add_task(filter_and_update_comment, comment_id, user_id, content)
