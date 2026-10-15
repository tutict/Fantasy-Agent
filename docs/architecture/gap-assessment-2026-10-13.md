# 灵构工坊完成度评估：九维度现状与业界对照

日期：2026-10-13
范围：全仓库（HEAD `8b95fce`，单分支 `main`）
方法：三路只读探查子 agent（后端流水线 / 前端与契约 / 内容产出与工程基建）并行摸底，每条承重结论由我逐条独立 grep / read 复现后才采信；关键数字（playtest 报告）直接读盘读出
锚点：**让产出的东西真的可玩、可验证**（工程师 2026-10-13 选定）

## 结论摘要

**工程质量 8 分、产品闭环 3 分。**

738 个后端用例（`grep -rh "def test_" tests/*.py | wc -l`，写本文时 705）+ 306 个前端用例 + 变异守卫（条数以 harness 汇总行为准，写本文时 119，2026-10-15 为 131）+ 三层审批闸门 + 原子写——这套基建比绝大多数同类 AI 生成项目都强。但它**在写本文时从来没有机器证明过"产出的东西能玩"**：唯一能量化这一点的 `godot_playtest` 真实可用、本机已有 5 次真跑记录，却完全不在执行链上。（2026-10-15 更新：G-03 已把它接进执行链并升成硬门禁，本结论已被 `gap-backlog-2026-10-13.md` 的 G-02/G-03 完成块超越。）

最硬的一条实测证据（本项目此前没被当回事，本次读盘读出）：

`generated/playtest/20261002_153442` 与 `20261002_160815` 两份报告，共 5 次运行：

| 指标 | 实测 | 目标 |
| --- | --- | --- |
| `win_rate` | **0.0**（5/5 失败） | — |
| 失败原因 | 100% `Route timer expires before the extraction gate` | — |
| `session_seconds_p50` | **3.0s** | `goal_session_minutes = 10.0`（600s） |
| `progress` | **0**（每次都 0，尽管玩家移动了 25–82m） | — |
| `playable_rate` | 1.0 | — |
| 报告 `status` | **`"warning"`** | 应当是 failed |
| `frames` | 438 / 1164 / 1891 | 上限 `max_frames = 36000` |

两点判读：

1. **帧数远低于上限**，排除 probe 截断；结束是生成的游戏自己的 route timer 在 3 秒到期——比目标短 200 倍。根因未定位，见待查项。
2. **玩家跑了 82 米但 `progress` 恒为 0**，通关路径不可达，而系统只报 `warning`。

## 九维度打分

| 维度 | 分 | 判断 | 支撑证据（可复算） |
| --- | --- | --- | --- |
| 策划设计 | 7/10 | 设计表达力强，但设计意图无法全部落到产物 | `gameplay-schema.yaml`（`wc -l`，1297 行）+ `axis_templates.py` 1674 行 + 双语 GDD；扣分：schema 运行时不校验、三处漂移、无 audio / 性能字段 |
| 玩法系统 | 7/10 | 机制生成丰富，但"机制生成"≠"循环可通关" | `gameplay_codegen.py` 997 行 per-axis；扣分：实测 `win_rate=0`、`session p50=3.0s` vs 目标 600s |
| 技术架构 | 8/10 | 单进程 + 原子写 + 三层审批 + 契约守卫；扣分全在编排层两处断链 | `atomic_write.py` / `path_safety.py`；扣分：`orchestrator.py:570-575` 死结、`grep -n record_stage fantasy_agent/pipeline_state.py`（当时 67-70，本批后 70-75）Unreal 断链 |
| 内容产出 | 7/10 | Godot 全链路真跑通（难得），但缺"内容进了场景并被玩到"的闭环 | ComfyUI 真出图 → Blender 真出 glb/fbx（PBR/UV/碰撞/socket）→ 真 headless import；扣分：`grep -c playtest fantasy_agent/executor.py = 0` |
| 美术音效 | 4/10 | 美术有真实产出，音频是彻底的零 | 美术：Blender manifest 含材质/UV/socket；音频：源码搜 `audiostream`/`.ogg`/`.wav`/`.mp3`/`sfx` 仅 2 处中文散文，生成工程 0 个 `AudioStreamPlayer` |
| 性能优化 | 2/10 | 没有预算、没有度量、没有门禁；采样了但没人读 | 搜 `draw_call`/`poly_count`/`triangle_count`/`fps`/`LOD`/`memory_budget`/`load_time` = **0 命中**；`PlaytestSample.wall_msec`（`grep -n wall_msec fantasy_agent/contracts.py`，当时 1115，本批后 1164）无任何断言消费 |
| 测试验证 | 8/10 | 738+306 用例（写本文时 705+306）+ 变异守卫（harness 汇总行，写本文时 119，2026-10-15 为 131）是真长板；扣分在黄金样例无保护 | `scripts/mutation_check_all_guards.py`（含 NO RUN / SKIPPED 识别）；扣分：`.gitignore:26 generated/*`、`git ls-files generated/ = 1`、Unreal 全 mock |
| 发布运营 | 2/10 | 从未发布过，无版本归因 | `git tag -l \| wc -l = 0`、version 0.1.0、`release.yml` on `tags: v*` 从未触发 |
| 长期可扩展性 | 6/10 | 有 drift 检测 / 8 轴扩展面，但双契约 + 只报告不回写会持续累积债 | `corrections.py:55-60` 只有 4 个锚点、~50 常量无处可存；`contracts.py` 与 yaml 双向漂移 |

## 已经跑通的部分（别动）

- **Godot 确定性链真跑通**：spec_validation → preflight → ComfyUI（真出图）→ Blender（真出 glb/fbx，含 PBR 材质、UV、碰撞体、socket）→ approval manifest 过滤 → gameplay codegen → 建工程 → 静态 validate → 真 headless import；LLM 脚本坏了能自动回退确定性模板重导。
- **Godot headless bot playtest** 真实可用，探针跑在工程外面不污染产物，时长读 `game_manager._elapsed` 而非帧数（避开了自研 bot 的经典坑），统计用 p50/p95/win_rate 分布而非单次。
- **三层审批闸门干净**：executor 总闸 + bridge 每工具闸 + ToolRegistry 权限档；`confirmed_side_effects` 无任何写死 true（前端 api.ts 三处 true 全部是两段式第二段的独立导出函数，且被 `FlowConsole.approval.test.tsx` / `OrchestrationBoard.test.tsx` 反向钉住）。
- **跨端契约守卫**：45 条路由 / 13 条 `KNOWN_WITHOUT_UI` 条条带原因 / 11 个工具名三处一一对应，我用守卫同款正则复算过差集，精确吻合、反向差集为空。
- **8 个设计轴**（parkour / stealth / combat / survival / puzzle / mobility / career / systems）带 verbs + 中文文案 + 关卡 beat + 资产清单，且 per-axis 机制生成有回归守护。
- **打包工程自觉**：未签名状态被 code note + README + release notes 三重钉住，`BUILD-INFO.json` 写 `"signed": false`，`tests/test_packaging.py` 把"描述为已签名"当缺陷。

## 业界实践对照

### 符合主流做法的（长板）

| 本项目做法 | 业界对应 |
| --- | --- |
| ROADMAP 明确"灰盒需求经过审阅后再引入 ComfyUI 视觉参考" | 垂直切片纪律（greybox over polish）。很多 AI 生成项目一上来堆美术，本项目刻意反着来 |
| 确定性模板回退 | LLM 产物不可信时的降级路径，务实 |
| 两段式副作用确认 + 三层闸门 | dangerous-operation gate，比大多数 agent 框架做得好 |
| validate 先于 import | fail-fast build health |
| playtest 用引擎内部时间，明确拒绝帧数 | automated playtest 的经典坑（帧数当时长）已避开 |
| 用分布而非单次 | 统计显著性 |
| 变异守卫（条数以 harness 汇总行为准，写本文时 119，2026-10-15 为 131）+ NO RUN / SKIPPED 识别 | test the tests，远超业界平均 |

### 违背主流做法的（按严重度）

| # | 违背点 | 业界做法 | 本项目的具体问题 |
| --- | --- | --- | --- |
| 1 | **playtest 不在 build 环里** | 每次产出后强制跑 bot smoke playtest（"every build is playtested"） | 做成独立 REST + 人工触发 = 测试存在但不跑。**最大的违背** |
| 2 | **exit gate 全是散文** | 垂直切片的 DoD 必须可判定 | 21 条 `quality_gates` 不可执行 = 没有闸门；`exit_checks` 消费者写好了但生产侧从不填 |
| 3 | **win_path 不可达只报 warning** | "first playable" 里通关路径可达是硬门槛 | `build_findings` 的理由（"bot 不能代替玩家判断好不好玩"）**对"好不好玩"成立，对"能不能通关"不成立**——概念混淆 |
| 4 | **黄金样例不入库** | golden master / known good build 必须版本化 | `generated/*` 全 ignore，每次都从零证明 |
| 5 | **性能预算后置** | asset budget / LOD 策略在 pre-production 就定 | 零预算 + Blender 已在真出 PBR 资产 = 面数/体积无声膨胀 |
| 6 | **音频"后置"被误用** | BGM / 配音确实后置 | 但**程序化反馈音是玩法反馈，不是音频生产**（Game Feel 的即时反馈维度）。本项目连失败反馈都没有，bot 报告里的失败原因是散文，人类玩家收不到信号 |
| 7 | **第二条引擎路线长期 mock** | 双引擎工作台至少要有 nightly 真机验证 | UE 测试全 mock = 声明了一个不存在的产能 |
| 8 | **双契约无守卫** | single source of truth | 已有跨端契约守卫机制，却没用在自己的 DSL 上——**机制闲置** |

## 模式性弱点（值得单独点名）

本项目三段式结构（**声明层 / 消费层 / 生产层**）里**总有一段没人填**。

`pipeline_state.py` 的注释坦白 stage order 漂移过一次，已用 `test_unreal_stage_order_*` 修掉。现在 `exit_checks` 正在重演同一个坑：声明层有字段（`grep -n exit_checks fantasy_agent/contracts.py`，当时 1022，本批后 1071）、消费层写好了（`grep -n _run_exit_checks fantasy_agent/orchestrator.py`，683-705，含"未注册工具即判 FAILED"的正确处理）、**生产层不填**（`workflows._pipeline_stage` 没有该形参）。**（2026-10-14：本条已被 G-02 修掉，三处现在都通；留档 because 它是「同一个坑踩两次」的标本。）**

推论：给 G-02 补的守卫要测**"门槛存在性"**（exit_checks 非空），而不只是"guard 会不会变红"。变异守卫测不了前者——`optimization_testing` 这个 vacuous gate 就是这么逃过去的。

## 即将踩的坑

1. **资产体积 / 面数无声膨胀**：无预算 + Blender 真出带 PBR/UV/碰撞的资产 + ComfyUI 真出图，三者叠加。第 5 批之前不会爆，之后如果还没预算就会。
2. **无版本归因**：基线与 playtest 报告无法归因到 spec 版本，改了什么导致退化说不清。
3. **schema 漂移加剧**：补音频要往 schema 加字段，若不先做双向守卫会再加一处漂移。
4. **打通编排后的第一次真相**：死结修好、第一次真跑到 `optimization_testing` 时，很可能发现前 5 个 stage 的产物拼起来根本不是可玩场景——因为从来没人验证过它们拼起来的结果。**这不是回归，是从未验证过**，别把它当成修死结做错了。

## 明确否决（带代价）

| 否决项 | 代价 | 替代 |
| --- | --- | --- |
| 实现 `publish_prototype_branch`（GitHub PR） | 引入 token / 网络依赖，**直接破坏"单进程本地自闭环、不对外暴露端点"的非目标**（`ROADMAP.md` 非目标段） | **删契约**（`mcp.py` + `unimplemented_contracts()` 例外分支），或降级为本地 `export_bundle` |
| 现在完整打通 Unreal（含 PIE 指标） | UE 冷启动 + 单次 commandlet 数十分钟，而 Godot 路线的 5–15 分钟切片验证是**秒级**。在"可玩可验证"锚点下投入产出严重倒挂 | 只做 `record_stage` + resume + 一条 opt-in 真机 commandlet |
| 音频全面补齐（BGM / 配音 / 空间音频 / 中间件） | 无素材源、无许可证、无验收口径；对 5–15 分钟切片可玩性贡献 ≈0 | 只做**程序化反馈音**，零素材依赖 |
| 前端大改版（响应式 / 视觉重做） | `orchestration.css` 零断点是**有意**的（本地工作台、固定大屏）；锚点不是表现力 | 只补与"验证"直接相关的面板 |
| 加遥测 / 崩溃上报 | 与"本地自闭环"非目标冲突，引入隐私与网络依赖 | 本地日志 + 可选"导出诊断包" |
| 现在做 corrections 采纳回写 | playtest findings 能真正触发重跑之前，回写没有驱动力；先做等于为 4 个字段建一整套机制 | 放到第 6 批 |

## 待查项（不臆断）

- **`session_seconds` 恒为 3.0s 的根因未定位。** 帧数 438–1891 远低于 `max_frames = 36000`，排除 probe 截断；怀疑是生成的 `game_manager` 的 route timer 与 `pressure_clock_seconds`（`target_session_minutes * 60` = 600s）不同源，或 M1 模板默认 `pressure_limit` 覆盖了 spec 值。**这是门禁落地后第一个会被抓住的真问题**，落地时按实测修，不按猜测改。

缺口清单与推进顺序见 `gap-backlog-2026-10-13.md`。
