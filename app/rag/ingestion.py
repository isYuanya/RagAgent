from dataclasses import dataclass, field


@dataclass(slots=True)
class IngestionDocument:
    text: str
    metadata: dict = field(default_factory=dict)


def normalize_document(text: str, metadata: dict | None = None) -> IngestionDocument:
    return IngestionDocument(text=text.strip(), metadata=metadata or {})
