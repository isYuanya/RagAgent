from app.schemas.copy import CopyAnalysisRequest, CopyAnalysisResponse
from app.services.compliance import inspect_risks


def analyze_copy(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    text = payload.source_text.strip()
    first_sentence = text.split("。")[0].split("\n")[0][:80] or "待识别主题"

    return CopyAnalysisResponse(
        topic=first_sentence,
        target_user=payload.audience or "待确认目标用户",
        core_pain="用户注意力不足或转化阻力",
        emotion_buttons=["好奇", "共鸣", "危机感"],
        hook=first_sentence,
        structure=["提出问题", "放大痛点", "给出观点", "举例说明", "行动建议"],
        expression_skills=["短句", "反问", "对比", "数字化表达"],
        reusable_template="如果你是____，一定要注意____。",
        suitable_scenarios=["直播引流", "私域成交", "课程种草", "个人IP"],
        risk_warnings=inspect_risks(text),
        confidence=0.62,
    )
