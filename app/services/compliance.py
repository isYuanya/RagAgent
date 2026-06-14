from app.schemas.common import RiskWarning


BLOCKED_TERMS = ["绝对有效", "百分百", "稳赚", "根治"]


def inspect_risks(text: str) -> list[RiskWarning]:
    warnings: list[RiskWarning] = []
    for term in BLOCKED_TERMS:
        if term in text:
            warnings.append(
                RiskWarning(
                    level="medium",
                    message=f"包含可能夸大或违规的表达：{term}",
                    suggestion="替换为可验证、可限定范围的表达。",
                )
            )
    return warnings
