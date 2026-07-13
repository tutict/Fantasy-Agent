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


## M7 Agent 可执行生产 Spec

`ProductionSpecBundle` 是 M7 的执行权威，`GameplaySpec` 是兼容视图。Bundle 的字段必须能追踪到配置、运行时 handoff、引擎 adapter 或 QA 断言。

| Spec | 执行职责 | 主要产物 |
| --- | --- | --- |
| `CombatSpec` | encounter、enemy role、damage、telegraph、counterplay | Godot enemy handoff、Unreal encounter DataTable |
| `LevelSpec` | 教学段、中段、最终测试、spawn/safe zone、objective gate | Godot 路线与 gate、Unreal DataAsset |
| `NumericTuningSpec` | 玩家数值、压力时钟、敌人倍率、调参边界 | Godot runtime、QA metrics |
| `NarrativeSpec` | objective copy、HUD、失败反馈 | Godot HUD/game manager、Unreal DataAsset |
| `ConfigTableSpec` | 主键、行、格式和安全导出路径 | YAML、JSON、CSV-ready、DataTable adapter |
| `ResourcePipelineSpec` | source、role、approval、destination、blocked reason | approval-gated ingest、资源追踪 |

执行规则：

1. `load_production_spec_bundle()` 只接受 workspace 内的 YAML/JSON 和受支持的 schema version。
2. `validate_production_spec_bundle()` 检查跨 Spec 引用、时长、counterplay、调参边界、表主键、导出路径和审批一致性。
3. 错误级 issue 在 create 阶段前阻断；warning 可继续但必须显式呈现。
4. 编译器输出 `SpecCompileResult.artifacts` 与 `traces`，每个 trace 记录 `spec_field -> artifact_path -> consumer`。
5. Creative Review manifest 写入后同步资源审批状态；只有 approved 资产可 ingest。
6. Unreal 机器 QA 输出结构化 assertion/result，error 失败会阻断，warning 标记 degraded。

CLI：`python -m fantasy_agent --spec-file <bundle.yaml|bundle.json> --format specs`。执行时可继续组合 `--engine`、`--execute`、`--yes`、`--with-gameplay` 与审批参数。