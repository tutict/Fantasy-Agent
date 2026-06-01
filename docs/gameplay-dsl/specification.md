# Gameplay DSL 规格

Gameplay DSL 是一个 YAML 文档，由 `gameplay-schema.yaml` 校验。

## 必填字段

- `schema_version`
- `title`
- `logline`
- `target_session_minutes`
- `player_fantasy`
- `design_pillars`
- `core_verbs`
- `core_loop`
- `systems`
- `progression`
- `win_state`
- `failure_states`
- `level_beats`
- `asset_needs`
- `qa_focus`
- `notes_for_unreal`
- `notes_for_blender`
- `notes_for_comfyui`

可选国际化字段：

- `i18n.source_locale`
- `i18n.output_locales`
- `i18n.field_translations`
- `i18n.term_translations`

## 设计规则

- `target_session_minutes` 必须在 5 到 15 之间。
- `core_loop` 至少包含三个步骤。
- `systems` 至少包含三个互相作用的系统。
- `level_beats` 必须包含教学和结算。
- `asset_needs` 必须映射到可玩互动或可读性。
- `notes_for_comfyui` 必须说明视觉生成如何服务玩法可读性。

## i18n 规则

- 英文字段仍是自动化主来源。
- 简体中文翻译使用字段路径保存在 `i18n.field_translations` 中，例如 `core_loop.0.action`。
- 可复用术语放在 `i18n.term_translations` 中。
- 面向引擎的标识不应本地化，除非它会展示给玩家。

## 产物流

```text
gameplay-spec.yaml
  -> gdd.md
  -> blender-asset-plan.yaml
  -> comfyui-visual-plan.yaml
  -> unreal-project-plan.yaml
  -> godot-project-plan.yaml
  -> qa-plan.yaml
```

DSL 是事实来源。下游智能体不能静默添加 spec 中不存在的机制。
