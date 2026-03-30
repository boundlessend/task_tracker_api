from pydantic import BaseModel


class CommentRead(BaseModel):
    id: int
    task_id: int
    text: str
