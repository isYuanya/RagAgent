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
    level: str = Field(
        default="low",
        description="风险等级，当前约定为 low、medium、high。",
        examples=["low", "medium", "high"],
    )
    message: str = Field(description="风险说明，描述文案中可能存在的问题。")
    suggestion: str | None = Field(default=None, description="风险修改建议，没有建议时为空。")


class CopyContext(BaseModel):
    industry: str | None = Field(default=None, description="行业或赛道，例如美妆、教育、本地生活。")
    audience: str | None = Field(default=None, description="目标人群，例如25-35岁女性、新手宝妈。")
    platform: str | None = Field(default=None, description="内容发布平台，例如抖音、小红书、视频号。")
    purpose: str | None = Field(default=None, description="内容目标，例如引流、成交、涨粉、私域转化。")
    style: str | None = Field(default=None, description="表达风格，例如犀利、共情、专业。")
    structure_type: str | None = Field(default=None, description="内容结构类型，例如痛点放大型。")
    content_type: ContentType | None = Field(default=None, description="内容类型，只能使用预设枚举值。")
