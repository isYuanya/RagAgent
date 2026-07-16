import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievedContext:
    text: str
    score: float
    metadata: dict[str, Any]


@dataclass(slots=True)
class VectorDocument:
    id: str
    text: str
    metadata: dict[str, Any]


class EmbeddingUnavailableError(RuntimeError):
    pass


class EmbeddingClient:
    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not settings.openai_api_key:
            raise EmbeddingUnavailableError("OPENAI_API_KEY is not configured")
        try:
            from langchain_openai import OpenAIEmbeddings

            client = OpenAIEmbeddings(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.embedding_model,
                check_embedding_ctx_length=False,
            )
            return client.embed_documents(texts)
        except Exception as exc:
            raise EmbeddingUnavailableError(f"Embedding call failed: {exc}") from exc


class MilvusVectorStore:
    collection_name = "ragagent_fragments"

    def __init__(self) -> None:
        self._client = None

    def _connect(self):
        if self._client is not None:
            return self._client
        try:
            from pymilvus import MilvusClient

            self._client = MilvusClient(uri=settings.milvus_uri)
            self._ensure_collection()
            return self._client
        except Exception as exc:
            logger.warning("Milvus is unavailable; vector operation skipped: %s", exc)
            return None

    def _ensure_collection(self) -> None:
        if self._client is None:
            return
        if not self._client.has_collection(self.collection_name):
            from pymilvus import DataType

            schema = self._client.create_schema(auto_id=False, enable_dynamic_field=True)
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=1536)
            self._client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                metric_type="COSINE",
            )
            index_params = self._client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                index_type="AUTOINDEX",
                metric_type="COSINE",
            )
            self._client.create_index(
                collection_name=self.collection_name,
                index_params=index_params,
            )
        self._client.load_collection(collection_name=self.collection_name)

    def upsert(self, documents: list[VectorDocument], vectors: list[list[float]]) -> bool:
        client = self._connect()
        if client is None:
            return False
        data = [
            {
                "id": document.id,
                "vector": vector,
                "text": document.text,
                **document.metadata,
            }
            for document, vector in zip(documents, vectors, strict=True)
        ]
        try:
            client.upsert(collection_name=self.collection_name, data=data)
            return True
        except Exception as exc:
            logger.warning("Milvus upsert failed: %s", exc)
            return False

    def search(
        self,
        vector: list[float],
        *,
        limit: int,
        filters: dict[str, str | None] | None = None,
    ) -> list[RetrievedContext]:
        client = self._connect()
        if client is None:
            return []
        expr = _filter_expression(filters or {})
        try:
            results = client.search(
                collection_name=self.collection_name,
                data=[vector],
                limit=limit,
                filter=expr or "",
                output_fields=[
                    "text",
                    "fragment_id",
                    "source_copy_id",
                    "fragment_role",
                    "position",
                    "platform",
                    "purpose",
                    "audience",
                    "industry",
                    "status",
                ],
            )
        except Exception as exc:
            logger.warning("Milvus search failed: %s", exc)
            return []
        return [_hit_to_context(hit) for hit in (results[0] if results else [])]

    def delete(self, ids: list[str]) -> bool:
        if not ids:
            return True
        client = self._connect()
        if client is None:
            return False
        quoted = ", ".join(f'"{item}"' for item in ids)
        try:
            client.delete(collection_name=self.collection_name, filter=f"id in [{quoted}]")
            return True
        except Exception as exc:
            logger.warning("Milvus delete failed: %s", exc)
            return False


class CopyKnowledgeRetriever:
    def __init__(
        self,
        *,
        embeddings: EmbeddingClient | None = None,
        vector_store: MilvusVectorStore | None = None,
    ) -> None:
        self.embeddings = embeddings or EmbeddingClient()
        self.vector_store = vector_store or MilvusVectorStore()

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, str | None] | None = None,
    ) -> list[RetrievedContext]:
        query = query.strip()
        if not query:
            return []
        try:
            vector = self.embeddings.embed_query(query)
        except EmbeddingUnavailableError as exc:
            logger.info("Semantic retrieval skipped: %s", exc)
            return []
        except Exception as exc:
            logger.warning("Semantic retrieval embedding failed: %s", exc)
            return []
        return self.vector_store.search(vector, limit=limit, filters=filters)


def upsert_fragment_vector(document: VectorDocument) -> bool:
    try:
        vector = EmbeddingClient().embed_query(document.text)
    except Exception as exc:
        logger.info("Fragment vector upsert skipped for %s: %s", document.id, exc)
        return False
    return MilvusVectorStore().upsert([document], [vector])


def delete_fragment_vectors(fragment_ids: list[str]) -> bool:
    vector_ids = [fragment_vector_id(fragment_id) for fragment_id in fragment_ids]
    return MilvusVectorStore().delete(vector_ids)


def fragment_vector_id(fragment_id: str) -> str:
    return f"fragment:{fragment_id}"


def _filter_expression(filters: dict[str, str | None]) -> str:
    parts = [f'{key} == "{value}"' for key, value in filters.items() if value is not None]
    return " and ".join(parts)


def _hit_to_context(hit: Any) -> RetrievedContext:
    entity = hit.get("entity", {}) if isinstance(hit, dict) else getattr(hit, "entity", {})
    score = hit.get("distance", 0) if isinstance(hit, dict) else getattr(hit, "distance", 0)
    text = entity.get("text", "") if isinstance(entity, dict) else ""
    return RetrievedContext(text=text, score=float(score or 0), metadata=dict(entity or {}))
