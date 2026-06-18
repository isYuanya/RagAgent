# 强化草稿视频 JSON 输出规则

## Goal

强化草稿工作台“视频处理 JSON”生成规则，让 `title`、`title_break`、`description`、`script`、`tts_script`、`hashtags` 更适合后续视频发布和配音流程，同时主动规避金融/营销高风险表达。

## Requirements

* `title` 必须是 2-16 字以内，像发布标题，不写成长句。
* `title` 尽量不用冒号、问号、感叹号等复杂标点。
* `title`、`title_break`、`description` 必须主动避开高风险营销词，包括但不限于：白户、黑户、包过、包下、秒批、必下、强开、无视征信、洗白征信、包装资料、刷流水、百分百、100%。
* 如果选题原文包含高风险词，必须改成更稳的中性表达：
  * 白户 -> 征信空白 / 信用记录少
  * 黑户 -> 严重逾期记录
  * 秒批 / 必下 -> 审批更快 / 匹配度更高
* `description` 必须存在，10-100 字，用汇总性语言简化说明视频核心内容，不能照搬完整口播文案。
* `title_break` 用于视频画面最上方的醒目标题字幕，不用于发布标题。
* `title_break` 必须与 `title` 表达同一个意思，可以更适合视觉呈现，但不能新增承诺、额度保证或改变核心含义。
* `title_break` 最多两行，只允许一个换行符 `\n`；短标题可以不换行。
* `title_break` 换行必须按语义自然切分，不按字数机械平分；不要拆开单个词、数字单位、专有名词。
* `title_break` 每行建议 6-12 个中文字符。
* `script` 必须是一段完整可直接口播的正文，已经包含开头钩子和自然结尾。
* 后端不会再拼接 hook 或 ending；`script` 不能依赖外部 hook/ending 才完整。
* `script` 内不要重复同一句开头或结尾。
* `script` 结尾不得包含评论、留言、私信、加好友、打关键词、说出自己情况等互动指令。
* `script` 严禁出现任何读音标注、拼音标注或方括号拼音，例如 `[háng]`、`[huán]`、`[xíng]`。
* `script` 只能写给观众看的正常中文字幕和口播正文。
* `script` 和 `tts_script` 的文字内容必须保持一致。
* `tts_script` 只能额外添加必要的多音字拼音标注，不得为了配音另行改写、增删或替换词语。
* `script` 本身应优先使用自然口语表达，避免 TTS 容易误断句的书面搭配。
* `hashtags` 不需要 `#` 号；直接返回话题文本数组，前端展示或后续流程可以用逗号分隔。

## Acceptance Criteria

* [ ] 后端 prompt 明确包含上述输出规则和风险词替换规则。
* [ ] 后端校验拒绝 `title` 超长、缺少 `description`、`description` 超长或过短。
* [ ] 后端校验拒绝 `title`、`title_break`、`description` 中的高风险营销词。
* [ ] 后端校验拒绝 `script` 中的方括号拼音标注。
* [ ] 后端校验拒绝 `script` 结尾互动指令。
* [ ] 后端校验保证 `title_break` 最多一个换行符。
* [ ] 后端不再自动给 `hashtags` 添加 `#`。
* [ ] 测试覆盖成功、风险词失败、`title_break` 过多换行、`script` 拼音标注、互动结尾失败。

## Definition of Done

* `python -m ruff check app tests alembic` passes.
* `python -m pytest tests` passes.
* `npm run build` passes if frontend is touched.
* Specs updated if public contract changes.

## Technical Approach

* 主要修改 `app/schemas/draft.py` 的 `DraftVideoExportPayload` 校验。
* 修改 `app/services/draft_video_export.py` 的 prompt，明确输出规则。
* 修改前端展示 hashtags 的方式，必要时用逗号分隔，而不是显示成带 `#` 标签。
* 增加 `tests/test_drafts_api.py` 覆盖新规则。

## Out of Scope

* 本次不新增视频剪辑、TTS 或字幕渲染接口。
* 本次不做行业可配置词库 UI。
* 本次不对旧历史记录批量重写。

## Technical Notes

* 当前视频 JSON 功能提交：`88f24b8 实现草稿视频 JSON 导出`。
* 现有无关 dirty 文件：`doc/RESTART_SERVICES.md`、`.idea/ai_debugger.xml`，不要纳入本任务。
