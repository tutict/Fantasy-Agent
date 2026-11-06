# Studio 本机 MCP 实测验收（2026-11-06）

本次验收使用 `scripts/studio_mcp_e2e.py`，只在 OS 临时根目录创建独立项目与数据。
Studio 和 `/mcp` 共用一个 Python 进程与 `127.0.0.1` 端口；前端使用当前工作树的
`apps/frontend/dist/`。不修改主工作区数据、Codex 全局配置或全局批准策略。

## 可复现运行

运行会真正启动 Godot console 的无窗口导入、质量检查与 bot 试玩。必须已经获得相应授权，
并显式传入 `--authorized`。默认进化预算为 600 秒、最多三个候选，整轮授权为 1800 秒。

```powershell
& 'C:/Users/tutic/IdeaProjects/Fantasy-Agent/.venv/Scripts/python.exe' `
  scripts/studio_mcp_e2e.py --authorized --challenging-baseline `
  --adopt-candidate --codex-cli --keep-alive
```

Godot 默认复用 `local_tools._find_godot()` 的本机探测，可用 `GODOT_EXECUTABLE`
或 `--godot '<console 可执行文件>'` 指定安装位置。

脚本在启动时输出临时工作区、URL 和 PID；不输出连接 Token。`acceptance/report.json`
保存结构化工具结果、job、表单内容和测量。`acceptance/resources/` 保存经 MCP 读取的
项目资源。工程、阶段状态、原始引擎日志和进化报告均保留在该临时工作区。

SDK 表单回调是**开发验收客户端**。它核对项目、版本、完整工具清单、空资产路径清单和有限预算，
随后响应原生 SDK 表单请求；这证明协议往返及服务端闸门，不能表述为真实 Codex 用户点击。
`--adopt-candidate` 是独立的开发验收许可，仅在真实报告为 `improved` 时响应采纳表单。
若报告为 `unchanged` / `manual_rework` / `budget_exhausted`，脚本不会伪造优胜候选或采纳。
`--challenging-baseline` 仅把已保存计划的追击速度改为 schema 允许的 3 倍，以增加数值改进
出现的机会；不修改评分标准、运行时代码或测量报告。

已关闭后可重启同一临时数据根供浏览器验收；重启只恢复状态，不自动重新执行任务：

```powershell
& 'C:/Users/tutic/IdeaProjects/Fantasy-Agent/.venv/Scripts/python.exe' `
  scripts/studio_mcp_e2e.py --authorized --serve-only --workspace '<先前临时目录>'
```

## 真实 Codex 连接的边界

`--codex-cli` 另起一次真实 `codex exec`，使用 `--ephemeral`、`--ignore-user-config`、
`--sandbox read-only` 和一次性 `--config`。Token 只通过子进程环境变量传递，CLI 的工具白名单
仅包含项目列表、快照、工作流状态与项目资源读取。其输出在写入
`acceptance/codex-cli.json` 前替换实际 Token。此检查不请求生产授权或采纳，因此不能证明
Codex 原生生产表单曾展示。

在 Codex 桌面中验收真实授权对话，需在 Studio「Codex 连接」的智能体连接面板开启服务，复制页面生成
的 HTTP MCP 配置和连接密钥环境变量说明，按客户端设置重新连接；已有聊天未热接入时需 Restart。
配置示例使用 `bearer_token_env_var`，不能把 Token 写入普通配置片段。
客户端还必须允许 `approval_policy.granular.mcp_elicitations`；由用户修改该策略，验收脚本
不会自动放开。随后创建/读取项目、请求明确动作和预算的授权，检查原生表单中的项目、版本、
工具与预算，再由用户回复。资产审阅与候选采纳需分别验证，不能复用生产批准。

参考：[Codex MCP](https://developers.openai.com/codex/mcp)、
[配置参考](https://developers.openai.com/codex/config-reference)。

## 实测记录

Studio 与 `/mcp` 在同进程、同端口运行，连接默认关闭。官方 `mcp==2.3.0` 客户端实际验证了工具、资源、项目版本、原生确认协议及生产闸门。缺失/错误 Bearer、错误 Host/Origin 和伪造确认均被拒绝；没有放宽服务闸门。

真实执行使用 Godot 4.6.3 console。两个独立场景为屋顶跑酷和潜行撤离，均完成生成、独立试玩、原节点返工和反馈实验。每轮分别登记 15 个生成资源、2 个独立试玩资源、15 个返工资源、18 个实验资源。返工复用原 `session_id`，重复生产请求返回原任务。

两轮进化基线均为五次通关，报告为 `unchanged`，没有优胜候选，**未发生实际候选采纳**。候选采纳的原生协议、内容摘要绑定、计划 CAS、不可变报告、提交失败及重启恢复由明确的合成测量测试验证；这些测试不能说成真实游戏改善。

SDK elicitation 回调是开发验收客户端。它核对项目、版本、动作、素材和预算后回复，证明协议往返及服务端权限校验；它不是 Codex 中的真人点击。

真实 Codex CLI 0.160.0 已按一次性只读配置多次核对，但模型认证返回 HTTP 401，未完成对话工具调用。已核对既有模型 provider，并排除宿主临时认证；没有修改 Codex 全局配置或批准策略。**Codex 真人授权、资产审阅及采纳弹窗尚未观察到。** 客户端模型地址中的 userinfo、任何 query 及 fragment 在构造 argv 前被拒绝，密钥只进入子进程环境并从证据清理；认证命令和 OAuth 登录不重放。

已按原临时目录和端口实际重启 Studio。计划第 2 版、4 个已完成任务、50 个资源引用、节点状态和真实批准均与重启前一致，没有启动新的生产任务。

中文面板在项目加载完成后验收：项目资产库与工作区共用库切换正确，真实任务可见；1360×1000 与 390×844、明暗主题均无横向溢出、页面错误或 HTTP 400+。Browser plugin 不可用，使用已安装的 Playwright Chromium，没有增加浏览器依赖。

前端最终 46 个文件、438 项测试通过，类型检查和生产构建通过。后端通过 `scripts/run_tests.py` 收集 1303 项：1301 项通过、2 项跳过、无失败；ruff 与 UI metrics 检查通过。MCP 31 项及前端 FE21 18 项变异均被捕获，源码逐字节恢复。四轴结论见 [四轴复核记录](studio-mcp-four-axis-review-2026-11-06.md)。

运行证据保留在系统临时目录 `fa-mcp-4qwsbek4/acceptance/`、`fa-mcp-7mn61e5o/acceptance/`；截图和重启前后签名保留在本任务的 Codex visualizations 目录，均未加入仓库。

首轮 Git 发布、游戏打包及 Unreal 节点续跑仍明确未支持。本轮没有启动 Unreal 生产。
