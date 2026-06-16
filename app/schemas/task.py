from pydantic import BaseModel, Field


class TaskProgress(BaseModel):
    phase: str = Field(default="queued", description="当前阶段。")
    model: str | None = Field(default=None, description="本任务使用的 LLM 模型。")
    current_row: int = Field(default=0, ge=0, description="当前处理到的 CSV 行号。")
    total_rows: int = Field(default=0, ge=0, description="CSV 数据总行数，不含表头。")
    processed_count: int = Field(default=0, ge=0, description="已处理行数。")
    success_count: int = Field(default=0, ge=0, description="成功导入数量。")
    failed_count: int = Field(default=0, ge=0, description="失败行数。")
    percent: int = Field(default=0, ge=0, le=100, description="任务进度百分比。")
    current_message: str | None = Field(default=None, description="当前状态说明。")
    errors: list[dict] = Field(default_factory=list, description="行级错误。")


class TaskResponse(BaseModel):
    task_id: str = Field(description="任务 ID。")
    status: str = Field(description="任务状态，例如 queued、running、finished、failed。")
    result: dict | None = Field(default=None, description="任务完成后的结果数据。")
    error: str | None = Field(default=None, description="任务失败时的错误信息。")
    progress: TaskProgress | None = Field(default=None, description="任务进度信息。")
