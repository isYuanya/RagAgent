# app/schemas 说明文档

## 1. schemas 的作用

`app/schemas/` 存放的是项目的 Pydantic 数据模型。

这些模型不是数据库表，而是 API 层、服务层、工作流层之间传递数据时使用的“数据契约”。它们主要解决三件事：

- 定义接口入参和出参长什么样。
- 自动校验字段类型、必填项、数值范围。
- 让 FastAPI 自动生成 `/docs` 接口文档。

当前 schema 按业务拆成 5 类：

```text
common.py    通用字段、通用枚举、风险提示模型
copy.py      文案拆解请求和响应
generate.py  文案生成请求和响应
task.py      异步任务状态响应
feedback.py  用户反馈请求和响应
```

`__init__.py` 负责集中导出常用 schema，方便其他模块统一导入。

## 2. common.py

`common.py` 放的是多个业务场景都会复用的基础模型。

### ContentType

`ContentType` 是内容类型枚举，继承自 `StrEnum`。

它限制 `content_type` 只能从预设内容类型里选择，避免前端或调用方传入完全不可控的字符串。

当前可选值：

| 枚举名 | 接口传值 | 含义 |
| --- | --- | --- |
| `planting` | `种草` | 产品推荐、消费决策引导类内容 |
| `emotion` | `情绪` | 情绪共鸣、观点表达类内容 |
| `knowledge` | `知识` | 科普、教程、解释型内容 |
| `reversal` | `反转` | 前后反差、认知反转型内容 |
| `story` | `故事` | 用故事推进表达的内容 |
| `practical` | `干货` | 方法论、清单、步骤型内容 |
| `controversy` | `争议` | 有争议点、讨论点、冲突点的内容 |

示例：

```json
{
  "content_type": "种草"
}
```

如果传入不在枚举里的值，FastAPI 会返回 `422 Unprocessable Entity`。

### RiskWarning

`RiskWarning` 表示一条风险提醒，用于文案拆解和生成结果里提示合规风险。

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `level` | `str` | 否 | 风险等级，默认 `low`。当前约定值为 `low`、`medium`、`high` |
| `message` | `str` | 是 | 风险说明 |
| `suggestion` | `str \| None` | 否 | 修改建议 |

示例：

```json
{
  "level": "medium",
  "message": "包含可能夸大或违规的表达：百分百",
  "suggestion": "替换为可验证、可限定范围的表达。"
}
```

### CopyContext

`CopyContext` 是文案拆解和文案生成共用的上下文字段。

它描述“这次内容要写给谁、在哪个平台、达成什么目的、用什么风格”。

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `industry` | `str \| None` | 否 | 行业或赛道，例如 `美妆`、`教育`、`本地生活` |
| `audience` | `str \| None` | 否 | 目标人群，例如 `25-35岁女性`、`新手宝妈` |
| `platform` | `str \| None` | 否 | 发布平台，例如 `抖音`、`小红书`、`视频号` |
| `purpose` | `str \| None` | 否 | 内容目的，例如 `引流`、`成交`、`涨粉`、`私域转化` |
| `style` | `str \| None` | 否 | 表达风格，例如 `犀利/共情/专业` |
| `structure_type` | `str \| None` | 否 | 内容结构类型，例如 `痛点放大型` |
| `content_type` | `ContentType \| None` | 否 | 内容类型，只能使用 `ContentType` 里的枚举值 |

这个模型本身一般不会直接作为 API 请求体使用，而是被 `CopyAnalysisRequest` 和 `GenerateRequest` 继承。

## 3. copy.py

`copy.py` 定义文案拆解接口的数据结构，对应 API：

```text
POST /api/copy/analyze
```

### CopyAnalysisRequest

`CopyAnalysisRequest` 是文案拆解请求体。

它继承了 `CopyContext`，所以除了自己的字段外，也可以传 `industry`、`audience`、`platform`、`purpose`、`style`、`structure_type`、`content_type`。

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `source_text` | `str` | 是 | 待拆解的原始文案，最少 1 个字符 |
| `source_url` | `str \| None` | 否 | 文案来源链接 |
| `metrics` | `dict[str, int] \| None` | 否 | 表现数据，例如点赞、评论、收藏、转发 |

校验规则：

- `source_text` 使用 `Field(min_length=1)`，不能为空字符串。
- `metrics` 的 key 是字符串，value 是整数。

请求示例：

```json
{
  "source_text": "如果你总觉得护肤没效果，先别急着换产品，可能是你的使用顺序错了。",
  "industry": "美妆",
  "audience": "25-35岁女性",
  "purpose": "引流",
  "style": "专业/共情",
  "content_type": "干货",
  "metrics": {
    "likes": 1200,
    "comments": 88,
    "favorites": 300,
    "shares": 42
  }
}
```

### CopyAnalysisResponse

`CopyAnalysisResponse` 是文案拆解结果。

字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `topic` | `str` | 主题，这条内容主要讲什么 |
| `target_user` | `str` | 目标用户，内容说给谁听 |
| `core_pain` | `str` | 核心痛点，用户为什么会停留 |
| `emotion_buttons` | `list[str]` | 情绪按钮，例如焦虑、好奇、共鸣、爽感、危机感 |
| `hook` | `str` | 开头钩子，一句话如何抓注意力 |
| `structure` | `list[str]` | 内容结构步骤 |
| `expression_skills` | `list[str]` | 表达技巧，例如短句、反问、对比、数字化表达 |
| `reusable_template` | `str` | 可复用模板或句式 |
| `suitable_scenarios` | `list[str]` | 适用场景，例如直播引流、私域成交、课程种草 |
| `risk_warnings` | `list[RiskWarning]` | 风险提示列表 |
| `confidence` | `float` | 置信度，范围是 0 到 1 |

校验规则：

- `confidence` 使用 `Field(ge=0, le=1)`，必须在 `[0, 1]` 之间。
- `risk_warnings` 里的每一项都必须符合 `RiskWarning` 结构。

响应示例：

```json
{
  "topic": "护肤没效果先检查使用顺序",
  "target_user": "25-35岁女性",
  "core_pain": "用户尝试护肤但效果不明显",
  "emotion_buttons": ["好奇", "共鸣", "危机感"],
  "hook": "如果你总觉得护肤没效果，先别急着换产品。",
  "structure": ["提出问题", "放大痛点", "给出观点", "举例说明", "行动建议"],
  "expression_skills": ["短句", "反问", "对比", "数字化表达"],
  "reusable_template": "如果你是____，一定要注意____。",
  "suitable_scenarios": ["直播引流", "私域成交", "课程种草"],
  "risk_warnings": [],
  "confidence": 0.62
}
```

## 4. generate.py

`generate.py` 定义文案生成接口的数据结构，对应 API：

```text
POST /api/generate
```

### GenerateRequest

`GenerateRequest` 是文案生成请求体。

它同样继承 `CopyContext`，因此可以复用行业、人群、平台、目的、风格、结构类型、内容类型等字段。

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `product_name` | `str \| None` | 否 | 产品、课程、服务或 IP 名称 |
| `selling_points` | `list[str]` | 否 | 卖点列表，默认空列表 |
| `user_pains` | `list[str]` | 否 | 用户痛点列表，默认空列表 |
| `reference_text` | `str \| None` | 否 | 参考文案，可用于生成风格或结构参考 |
| `version_count` | `int` | 否 | 生成版本数量，默认 3，范围 1 到 10 |

校验规则：

- `selling_points` 使用 `default_factory=list`，避免多个请求共享同一个默认列表。
- `user_pains` 使用 `default_factory=list`，同样避免共享默认列表。
- `version_count` 使用 `Field(default=3, ge=1, le=10)`，最少 1 个版本，最多 10 个版本。

请求示例：

```json
{
  "industry": "美妆",
  "audience": "25-35岁女性",
  "platform": "小红书",
  "purpose": "引流",
  "style": "专业/共情",
  "structure_type": "痛点放大型",
  "content_type": "干货",
  "product_name": "敏感肌修护精华",
  "selling_points": ["温和", "修护屏障", "适合换季"],
  "user_pains": ["泛红", "刺痛", "护肤没效果"],
  "reference_text": "如果你换季就泛红刺痛，先别急着叠加猛药。",
  "version_count": 3
}
```

### GeneratedVariant

`GeneratedVariant` 表示生成结果中的一个候选版本。

字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | `str` | 标题 |
| `hook` | `str` | 开头钩子 |
| `script` | `str` | 完整口播文案 |
| `comment_guide` | `str` | 评论区引导 |

示例：

```json
{
  "title": "敏感肌换季别乱叠加",
  "hook": "如果你一到换季就泛红刺痛，先停下这一步。",
  "script": "很多敏感肌不是缺产品，而是屏障已经被过度折腾了...",
  "comment_guide": "评论区告诉我你的肤质状态，我帮你判断该先停什么。"
}
```

### GenerateResponse

`GenerateResponse` 是文案生成接口返回值。

字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `topic_direction` | `str` | 选题方向 |
| `hooks` | `list[str]` | 多个开头钩子 |
| `script` | `str` | 主版本完整口播文案 |
| `shot_suggestions` | `list[str]` | 分镜建议 |
| `titles` | `list[str]` | 标题候选 |
| `comment_guides` | `list[str]` | 评论区引导候选 |
| `variants` | `list[GeneratedVariant]` | 多个可替换版本 |
| `risk_warnings` | `list[RiskWarning]` | 风险提示列表 |

响应示例：

```json
{
  "topic_direction": "面向25-35岁女性，围绕敏感肌修护精华做引流型内容",
  "hooks": ["如果你一到换季就泛红刺痛，先停下这一步。"],
  "script": "很多敏感肌不是缺产品，而是屏障已经被过度折腾了...",
  "shot_suggestions": ["痛点场景开场", "产品使用过程", "前后对比", "结尾行动引导"],
  "titles": ["敏感肌换季别乱叠加"],
  "comment_guides": ["评论区告诉我你的肤质状态，我帮你判断该先停什么。"],
  "variants": [
    {
      "title": "敏感肌换季别乱叠加",
      "hook": "如果你一到换季就泛红刺痛，先停下这一步。",
      "script": "很多敏感肌不是缺产品，而是屏障已经被过度折腾了...",
      "comment_guide": "评论区告诉我你的肤质状态，我帮你判断该先停什么。"
    }
  ],
  "risk_warnings": []
}
```

## 5. task.py

`task.py` 定义异步任务状态响应，对应 API：

```text
GET /api/tasks/{task_id}
```

### TaskResponse

`TaskResponse` 用来描述一个后台任务当前的执行状态。

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_id` | `str` | 是 | 任务 ID |
| `status` | `str` | 是 | 任务状态，例如 `queued`、`running`、`finished`、`failed` |
| `result` | `dict \| None` | 否 | 任务完成后的结果 |
| `error` | `str \| None` | 否 | 任务失败时的错误信息 |

示例：

```json
{
  "task_id": "8fd3a75f-2d1f-4c59-9fb2-f6a80f64a7a8",
  "status": "finished",
  "result": {
    "message": "生成完成"
  },
  "error": null
}
```

当前项目里的任务状态还是内存实现，后续接 RQ 后，`TaskResponse` 可以继续作为对外响应格式，不需要前端改字段。

## 6. feedback.py

`feedback.py` 定义用户反馈的数据结构，对应 API：

```text
POST /api/feedback
```

### FeedbackRequest

`FeedbackRequest` 是用户反馈请求体。

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `artifact_id` | `str \| None` | 否 | 被评价的产物 ID，例如某次生成结果 ID |
| `rating` | `int` | 是 | 用户评分，范围 1 到 5 |
| `comment` | `str \| None` | 否 | 用户文字反馈 |
| `selected_variant` | `str \| None` | 否 | 用户选择或偏好的版本 ID/标题 |

校验规则：

- `rating` 使用 `Field(ge=1, le=5)`，必须是 1 到 5 的整数。

请求示例：

```json
{
  "artifact_id": "generation-001",
  "rating": 5,
  "comment": "第二版更适合小红书，钩子更直接。",
  "selected_variant": "version-2"
}
```

### FeedbackResponse

`FeedbackResponse` 是反馈接口返回值。

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `feedback_id` | `str` | 是 | 反馈记录 ID |
| `status` | `str` | 否 | 记录状态，默认 `recorded` |

响应示例：

```json
{
  "feedback_id": "f4f09b48-e789-4db1-a205-c48cf2324da5",
  "status": "recorded"
}
```

## 7. __init__.py

`app/schemas/__init__.py` 集中导出常用 schema：

```python
from app.schemas.copy import CopyAnalysisRequest, CopyAnalysisResponse
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.generate import GenerateRequest, GenerateResponse
from app.schemas.task import TaskResponse
```

这样其他模块可以写：

```python
from app.schemas import GenerateRequest, GenerateResponse
```

而不需要分别从多个文件导入。

## 8. schema 和其他层的关系

### API 层

API route 使用 schema 定义请求体和响应体：

```python
@router.post("/analyze", response_model=CopyAnalysisResponse)
def analyze(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    ...
```

这里有两个作用：

- `payload: CopyAnalysisRequest`：FastAPI 会把 JSON 请求体解析成 Pydantic 对象。
- `response_model=CopyAnalysisResponse`：FastAPI 会校验并格式化响应。

### Service 层

Service 层直接接收 schema 对象，避免到处传散乱的 dict：

```python
def analyze_copy(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    ...
```

这样服务层可以明确知道输入输出结构。

### Workflow 层

Workflow 层也使用 schema 作为状态输入和输出。

例如生成流程后续接 LangGraph 时，`GenerateRequest` 可以作为初始输入，`GenerateResponse` 可以作为最终输出。

### Model 层

`app/models/` 是数据库 ORM 模型，负责落库。

`app/schemas/` 是 API 和业务传输模型，负责接口数据。

两者不要混用：

- 数据库存储字段变更，优先改 `models/` 和 Alembic migration。
- API 请求/响应字段变更，优先改 `schemas/`。

## 9. 后续建议

当前 schema 是首版可运行骨架，后续可以继续增强：

- 给 `RiskWarning.level` 改成枚举，避免传入任意字符串。
- 给 `platform`、`purpose`、`style` 增加枚举或字典表。
- 给 `metrics` 定义专门模型，例如 `likes`、`comments`、`favorites`、`shares`。
- 给 `GenerateResponse` 增加 `artifact_id`，方便反馈接口关联生成结果。
- 给 `TaskResponse.status` 增加枚举，统一任务状态。
- 给每个字段补充 `description`，让 FastAPI `/docs` 更清晰。
