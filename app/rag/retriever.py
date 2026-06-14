from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedContext:
    text: str
    score: float
    metadata: dict


class CopyKnowledgeRetriever:
    def retrieve(self, query: str, limit: int = 5) -> list[RetrievedContext]:
        return [
            RetrievedContext(
                text=f"stub context for: {query}",
                score=0.1,
                metadata={"source": "stub", "limit": limit},
            )
        ]
