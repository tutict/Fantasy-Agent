# i18n 策略

当前文档先统一为中文；代码、路径、类名、Blueprint 名、MCP tool 名和 metric key 仍保持英文。需要面向多语言输出时，Fantasy Agent 通过 `i18n` bundle 维护字段级翻译。

## 原则

- 英文仍是自动化标识语言，用于代码、路径、类名、Blueprint 名、MCP tool 名和 metric key。
- 简体中文是一等支持语言，用于设计评审、GDD 输出、智能体说明、界面文案和玩家文本规划。
- 核心 DSL 保持简单字符串，方便 UE、Blender、Godot 和 MCP 工具直接消费。
- 翻译与 spec 同级保存于 `i18n.field_translations` 和 `i18n.term_translations`。

## 字段路径

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

## 运行时行为

- `PromptRequest.output_locales` 决定生成哪些语言。
- `GameplaySpec.i18n` 携带字段级本地化文本。
- `GDDDocument.markdown_by_locale` 保存各语言独立文档。
- 同时请求中英时，`GDDDocument.markdown` 可以合并输出双语文档。
- Studio 页面使用前端 i18n 字典渲染用户可见文案。
- MCP 状态接口返回稳定 key 与参数，前端按当前语言渲染说明。

## 后续工作

- 增加面向 LLM 生成的多语言 prompt 模板。
- 在 CI 中校验翻译覆盖率。
- 导出 Unreal `String Table` 资产用于玩家可见文本。
- 增加 Blender 与 Godot 命名规则，区分内部 ID 与显示名。
