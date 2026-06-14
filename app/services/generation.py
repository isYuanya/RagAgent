from app.core.llm import get_llm_client
from app.schemas.generate import GeneratedVariant, GenerateRequest, GenerateResponse
from app.services.compliance import inspect_risks


def generate_copy(payload: GenerateRequest) -> GenerateResponse:
    llm = get_llm_client()
    product = payload.product_name or "你的产品"
    audience = payload.audience or "目标用户"
    purpose = payload.purpose or "转化"
    style = payload.style or "专业且有共情"
    direction = f"面向{audience}，围绕{product}做{purpose}型内容"

    llm.complete(f"生成{payload.version_count}条{style}风格文案：{direction}")

    variants = [
        GeneratedVariant(
            title=f"{product}内容方向 {index + 1}",
            hook=f"如果你正在为{product}纠结，先看这一点。",
            script=(
                f"很多{audience}不是不想行动，而是不知道该从哪里开始。"
                f"这条内容会先放大真实痛点，再给出一个清晰的{product}解决路径。"
            ),
            comment_guide="评论区告诉我你的具体场景，我帮你拆下一步。",
        )
        for index in range(payload.version_count)
    ]

    script = variants[0].script
    return GenerateResponse(
        topic_direction=direction,
        hooks=[variant.hook for variant in variants],
        script=script,
        shot_suggestions=["痛点场景开场", "产品使用过程", "前后对比", "结尾行动引导"],
        titles=[variant.title for variant in variants],
        comment_guides=[variant.comment_guide for variant in variants],
        variants=variants,
        risk_warnings=inspect_risks(script),
    )
