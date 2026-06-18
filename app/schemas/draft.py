import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.copy import CopyAssetSummary
from app.schemas.knowledge import FragmentExtractionResult


DraftStatus = Literal["draft", "ready", "archived"]
HIGH_RISK_VIDEO_EXPORT_TERMS = (
    "白户",
    "黑户",
    "包过",
    "包下",
    "秒批",
    "必下",
    "强开",
    "无视征信",
    "洗白征信",
    "包装资料",
    "刷流水",
    "百分百",
    "100%",
)
INTERACTIVE_ENDING_PATTERNS = (
    "评论",
    "留言",
    "私信",
    "加好友",
    "打关键词",
    "说出自己情况",
)
PINYIN_ANNOTATION_PATTERN = re.compile(r"\[[A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüÜ]+\]")


class DraftCreate(BaseModel):
    title: str = Field(min_length=1)
    goal: str | None = None
    audience: str | None = None
    platform: str | None = None
    purpose: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    goal: str | None = None
    audience: str | None = None
    platform: str | None = None
    purpose: str | None = None
    status: DraftStatus | None = None
    metadata: dict[str, Any] | None = None


class DraftItemCreate(BaseModel):
    source_fragment_id: str | None = None
    edited_text: str | None = Field(default=None, min_length=1)
    role: str | None = None
    position: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_source_or_text(self) -> "DraftItemCreate":
        if self.source_fragment_id is None and self.edited_text is None:
            raise ValueError("source_fragment_id or edited_text is required")
        return self


class DraftItemUpdate(BaseModel):
    edited_text: str | None = Field(default=None, min_length=1)
    role: str | None = None
    position: str | None = None
    metadata: dict[str, Any] | None = None


class DraftItemReorder(BaseModel):
    item_id: str
    order_index: int = Field(ge=0)


class DraftItemReorderRequest(BaseModel):
    items: list[DraftItemReorder] = Field(min_length=1)


class DraftItem(BaseModel):
    id: str
    draft_id: str
    source_fragment_id: str | None = None
    source_copy_id: str | None = None
    order_index: int
    original_fragment_text: str | None = None
    edited_text: str
    role: str | None = None
    position: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftSummary(BaseModel):
    id: str
    title: str
    goal: str | None = None
    audience: str | None = None
    platform: str | None = None
    purpose: str | None = None
    status: DraftStatus
    current_text: str
    item_count: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftDetail(DraftSummary):
    items: list[DraftItem] = Field(default_factory=list)


class DraftListResponse(BaseModel):
    items: list[DraftSummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class DraftVersionCreate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftItemSnapshot(BaseModel):
    id: str
    source_fragment_id: str | None = None
    source_copy_id: str | None = None
    order_index: int
    original_fragment_text: str | None = None
    edited_text: str
    role: str | None = None
    position: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftVersionSummary(BaseModel):
    id: str
    draft_id: str
    version_number: int = Field(ge=1)
    label: str | None = None
    current_text: str
    item_count: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftVersionDetail(DraftVersionSummary):
    items: list[DraftItemSnapshot] = Field(default_factory=list)


class DraftApprovalResponse(BaseModel):
    draft: DraftDetail
    raw_copy: CopyAssetSummary
    fragment_extraction: FragmentExtractionResult


class DraftVideoExportPayload(BaseModel):
    title: str = Field(min_length=2, max_length=16)
    title_break: str = Field(min_length=2, max_length=40)
    description: str = Field(min_length=10, max_length=100)
    script: str = Field(min_length=1)
    tts_script: str = Field(min_length=1)
    hashtags: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("title", "title_break", "description", "script", "tts_script")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("title", "title_break", "description")
    @classmethod
    def _reject_high_risk_terms(cls, value: str) -> str:
        matched = [term for term in HIGH_RISK_VIDEO_EXPORT_TERMS if term in value]
        if matched:
            raise ValueError(f"high-risk marketing terms are not allowed: {', '.join(matched)}")
        return value

    @field_validator("title_break")
    @classmethod
    def _validate_title_break_lines(cls, value: str) -> str:
        if value.count("\n") > 1:
            raise ValueError("title_break must contain at most one newline")
        if any(not line.strip() for line in value.split("\n")):
            raise ValueError("title_break lines must not be empty")
        return value

    @field_validator("script")
    @classmethod
    def _validate_script(cls, value: str) -> str:
        if PINYIN_ANNOTATION_PATTERN.search(value):
            raise ValueError("script must not contain pinyin annotations")
        ending = value.strip()[-40:]
        matched = [term for term in INTERACTIVE_ENDING_PATTERNS if term in ending]
        if matched:
            raise ValueError("script ending must not contain interactive instructions")
        return value

    @field_validator("hashtags")
    @classmethod
    def _clean_hashtags(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip().lstrip("#").strip()
            if not text:
                continue
            cleaned.append(text)
        return cleaned[:5]

    @model_validator(mode="after")
    def _validate_tts_matches_script(self) -> "DraftVideoExportPayload":
        tts_without_annotations = PINYIN_ANNOTATION_PATTERN.sub("", self.tts_script)
        if _compact_text(tts_without_annotations) != _compact_text(self.script):
            raise ValueError("tts_script must match script except for pinyin annotations")
        return self


class DraftVideoExportRecord(BaseModel):
    id: str
    draft_id: str
    status: str
    result: DraftVideoExportPayload
    model: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class DraftVideoExportListResponse(BaseModel):
    items: list[DraftVideoExportRecord]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", "", value)
