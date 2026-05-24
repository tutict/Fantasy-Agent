# i18n Strategy / 国际化策略

Fantasy Agent uses a bilingual-by-default model for human-facing production artifacts.

Fantasy Agent 对面向人的生产产物默认采用中英双语模型。

## Principles / 原则

- English is the canonical automation language for code, paths, class names, Blueprint names, MCP tool names, and metric keys.
- Simplified Chinese is first-class for design review, GDD output, agent instructions, and player-facing text planning.
- The core DSL remains simple strings so UE, Blender, and MCP tools can consume it without custom localization parsing.
- Translations live beside the spec in `i18n.field_translations` and `i18n.term_translations`.

- 英文作为代码、路径、类名、蓝图名、MCP 工具名和指标名的自动化主语言。
- 简体中文是一等支持语言，用于设计评审、GDD 输出、智能体说明和面向玩家文本规划。
- 核心 DSL 保持简单字符串，方便 UE、Blender 和 MCP 工具直接消费。
- 翻译与 spec 同级保存于 `i18n.field_translations` 和 `i18n.term_translations`。

## Field Paths / 字段路径

Translations use stable field paths:

翻译使用稳定字段路径：

```yaml
i18n:
  source_locale: en
  output_locales:
    - en
    - zh-CN
  field_translations:
    core_loop.0.action:
      en: "Scout the immediate play space"
      zh-CN: "侦察当前空间"
```

## Runtime Behavior / 运行时行为

- `PromptRequest.output_locales` decides which languages are generated.
- `GameplaySpec.i18n` carries localized field text.
- `GDDDocument.markdown_by_locale` contains separate localized documents.
- `GDDDocument.markdown` combines English and Simplified Chinese when both are requested.

- `PromptRequest.output_locales` 决定生成哪些语言。
- `GameplaySpec.i18n` 携带字段级本地化文本。
- `GDDDocument.markdown_by_locale` 保存各语言独立文档。
- 同时请求中英时，`GDDDocument.markdown` 合并输出双语文档。

## Future Work / 后续工作

- Add locale-specific prompt templates for LLM-backed generation.
- Validate translation coverage in CI.
- Export Unreal `String Table` assets for player-facing text.
- Add Blender asset naming rules that separate internal IDs from display names.

- 增加面向 LLM 生成的多语言 prompt 模板。
- 在 CI 中校验翻译覆盖率。
- 导出 Unreal `String Table` 资产用于玩家可见文本。
- 增加 Blender 命名规则，区分内部 ID 与显示名。
