# Godot 试玩反馈进化首版

用户已授权按本次可行性建议修改代码。范围是 Godot 灰盒的受控数值返工、对照复测、人工采用和经验复用。

## 闭环与边界

Studio 直接调用 `fantasy_agent/evolution/`，不增加服务或 MCP 入口。实验固定使用确定性玩法生成、无 Blender/ComfyUI 的 Godot 灰盒；基线和每个候选使用独立 session。最多三个候选，默认总预算 600 秒，支持取消。预算包含基线、导入和试玩；底层进程 timeout 不得超过剩余预算。用户先预览操作清单，再明确确认整个有限实验。确认不写入经验或恢复记录；恢复后的未完成实验标为中断，不自动启动。

修改只进入 `ProductionSpecBundle.numeric` 的白名单：`player_move_speed`、`pressure_clock_seconds`、`enemy_pressure.enemy_count_multiplier`、`enemy_pressure.move_speed_multiplier`、`enemy_pressure.detection_radius_multiplier`。所有修改必须通过严格模型和 `validate_production_spec_bundle`；不修改胜负规则、bot、评测器、生成器源码或审批清单。不可用工具、脚本/路线/输入缺陷返回具体人工返工建议，不假装数值能修复。

基线和候选均实际执行、实际试玩。报告必须有完整样本、可读结果、相同机制轴及输入策略；重新从 samples 计算 aggregate，不信任摘要分数。候选必须无 blocking finding，核心动作交付、移动距离和已有机制作用不得退化；只在胜利次数提高或阻塞消失且没有退化时标为改进。单纯把胜率推向 100% 不构成通用乐趣评价，保留人工试玩反馈。

实验结束只生成候选和比较报告。用户点击采用后才返回更新后的完整计划并保存经验；前端通过既有 handoff 更新 bundle，后续执行仍走原有确认。经验按机制轴、引擎和白名单字段检索，应用候选仍经过当前计划的范围校验。经验不会自动替换工作台当前计划。

## 模块接口

`contracts.py` 定义严格模型：

- `EvolutionRequest(plan, confirmed=False, max_iterations=3 [1..3], max_wall_seconds=600 [30..1800], use_experience=True)`。
- `NumericChange(field, before, after, reason)`。
- `EvolutionIteration(index, session_id, plan, report: PlaytestReport | None, changes=[], eligible=False, improved=False, notes=[])`。
- `EvolutionReport(source, schema_version='0.1', experiment_id, status, original_plan, iterations=[], best_iteration=None, adopted_iteration=None, notes=[], elapsed_seconds=0)`。
- `EvolutionExperience(id, experiment_id, axis, engine='Godot 4', changes, feedback='', created_at='')`。

`evaluation.py` 提供 `compare_reports(baseline, candidate) -> tuple[bool, list[str]]`，只用固定规则。

`candidates.py` 提供 `plan_fingerprint(plan) -> str`、`apply_changes(plan, changes) -> DirectorBuildPlan`、`propose_changes(plan, report) -> list[NumericChange]`，以及 `changes_from_experience(plan, experience) -> list[NumericChange]`。

`library.py` 提供 `save_report`、`load_report`、`list_experiences`、`save_experience`，以 `workspace_root` 为关键字参数；决策记录全部 `write_atomic`，索引读改写共用工作区锁，缺失为空、损坏报错，路径段必须验证。

`controller.py` 提供 `run_evolution(request, *, experiment_id, workspace_root, run_iteration=None, clock=None)`；`run_iteration(plan, session_id, remaining_seconds) -> PlaytestReport` 是实际引擎边界，可用于模拟测试。实际 runner 由 `runtime.py` 提供，走现有 executor 与 process_runner。

## Studio 契约

- `POST /api/evolution/run`：未确认只预览；确认后进入现有单 worker 执行池，返回 `job_id`、`experiment_id`。
- `GET /api/evolution/{experiment_id}`：返回 `status`、`report`、可选 `error`；运行中读已落盘进度，重启后返回中断记录。
- `POST /api/evolution/{experiment_id}/cancel`：使用既有 job cancel scope。
- `POST /api/evolution/{experiment_id}/adopt`：body 为 `{plan, feedback}`，先验证当前计划与基线一致，再验证获胜候选，保存经验并返回 `{status:'adopted', plan, experience}`。
- `GET /api/evolution/experiences`：返回 `{experiences}`。
- `POST /api/evolution/suggest`：body 为 `{plan}`，只读返回 `{plan, changes, experience_id, notes}`，由用户采用建议。

界面加到流程控制台“质量”步骤，复用已有确认对话框、token、主题、语言和保留挂载机制。显示预算、操作清单、每轮指标、候选差异、停止原因、人工采用和经验建议。确认只由按钮动作产生；加载、切换计划和恢复不运行实验。

## 验收

测试先证明未确认零写盘零执行、预算与取消止住新工作、候选独立 session、缺失测量拒绝、退化拒绝、人工采用才保存经验、重启可回读、损坏不伪装空库、经验在新任务实际消费。后端用 `scripts/run_tests.py`，前端完成 typecheck/test/build，新增审批守卫进入现有变异脚本。测试模拟实际引擎边界；未经用户明确批准不启动真实引擎开展实验。
