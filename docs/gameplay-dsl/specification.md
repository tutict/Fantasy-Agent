# Gameplay DSL Specification

The gameplay DSL is a YAML document validated by `gameplay-schema.yaml`.

Gameplay DSL 是一个 YAML 文档，由 `gameplay-schema.yaml` 校验。

## Required Sections

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

Optional i18n section:

- `i18n.source_locale`
- `i18n.output_locales`
- `i18n.field_translations`
- `i18n.term_translations`

可选国际化字段：

- `i18n.source_locale`
- `i18n.output_locales`
- `i18n.field_translations`
- `i18n.term_translations`

## Design Rules

## 设计规则

- `target_session_minutes` must be between 5 and 15.
- `core_loop` must include at least three steps.
- `systems` must include at least three interacting systems.
- `level_beats` must include onboarding and resolution.
- `asset_needs` must map to playable interactions or readability.

- `target_session_minutes` 必须在 5 到 15 之间。
- `core_loop` 至少包含三个步骤。
- `systems` 至少包含三个互相作用的系统。
- `level_beats` 必须包含教学和结算。
- `asset_needs` 必须映射到可玩互动或可读性。

## i18n Rules

## 国际化规则

- The English fields are the canonical automation source.
- Simplified Chinese is stored in `i18n.field_translations` using field paths such as `core_loop.0.action`.
- Reusable vocabulary belongs in `i18n.term_translations`.
- Engine-facing identifiers should not be localized unless they are displayed to players.

- 英文字段是自动化的主来源。
- 简体中文翻译使用字段路径保存在 `i18n.field_translations` 中，例如 `core_loop.0.action`。
- 可复用术语放在 `i18n.term_translations` 中。
- 面向引擎的标识不应本地化，除非它会展示给玩家。

## Artifact Flow

## 产物流

```text
gameplay-spec.yaml
  -> gdd.md
  -> blender-asset-plan.yaml
  -> unreal-project-plan.yaml
  -> qa-plan.yaml
```

The DSL is the source of truth. Downstream agents should not silently add mechanics that are not represented in the spec.
