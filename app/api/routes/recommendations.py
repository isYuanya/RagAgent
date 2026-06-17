from fastapi import APIRouter, HTTPException

from app.schemas.recommendation import (
    AcceptRecommendationRequest,
    AcceptRecommendationResponse,
    NextSentenceRecommendationRequest,
)
from app.schemas.task import TaskResponse
from app.services import drafts, recommendations
from app.workers.recommendation_queue import enqueue_next_sentence_recommendation

router = APIRouter()


@router.post("/next-sentence", response_model=TaskResponse)
def next_sentence(payload: NextSentenceRecommendationRequest):
    return enqueue_next_sentence_recommendation(payload)


@router.post("/accepted", response_model=AcceptRecommendationResponse)
def accept_recommendation(payload: AcceptRecommendationRequest):
    try:
        return recommendations.accept_recommendation(payload)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except recommendations.RecommendationTaskNotFoundError:
        raise HTTPException(status_code=404, detail="Recommendation task not found") from None
    except recommendations.RecommendationCandidateNotFoundError:
        raise HTTPException(status_code=404, detail="Recommendation candidate not found") from None
