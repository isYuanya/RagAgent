from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    task_id: str = Field(description="任务ID。")
    status: str = Field(description="任务状态，例如 queued、running、finished、failed。")
    result: dict | None = Field(default=None, description="任务完成后的结果数据。")
    error: str | None = Field(default=None, description="任务失败时的错误信息。")
