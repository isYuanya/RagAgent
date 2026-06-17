from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


DraftStatus = Literal["draft", "ready", "archived"]


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
