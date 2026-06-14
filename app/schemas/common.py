from enum import StrEnum

from pydantic import BaseModel, Field


class ContentType(StrEnum):
    planting = "种草"
    emotion = "情绪"
    knowledge = "知识"
    reversal = "反转"
    story = "故事"
    practical = "干货"
    controversy = "争议"


class RiskWarning(BaseModel):
    level: str = Field(default="low", examples=["low", "medium", "high"])
    message: str
    suggestion: str | None = None


class CopyContext(BaseModel):
    industry: str | None = None
    audience: str | None = None
    platform: str | None = None
    purpose: str | None = None
    style: str | None = None
    structure_type: str | None = None
    content_type: ContentType | None = None
