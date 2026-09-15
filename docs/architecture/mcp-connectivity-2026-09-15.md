# Studio MCP 连接状态：一次实测与修复

日期：2026-09-15
范围：`apps/studio/app/main.py` 的 `/api/tool-status`（Studio 面板的 MCP 连接状态）

## 结论

应用层的 MCP 连接探测**曾经把装好的 Unreal 报成 `unavailable`**。原因是"引擎装在哪"这件事被实现了两遍：执行器走 `local_tools._find_unreal()`（认 Epic Launcher 清单，能找到自定义安装根），而状态面板自带一份只 glob `Program Files` 的副本。上一轮把库内那份修好，面板这份没跟着动，于是**面板和它要启动的进程各说各话**。

已修：面板改为接受一个 resolver，直接引用 `local_tools` 的解析函数，不再自带第二份搜索。

## 实测（修复前 / 修复后）

同一台机器，`GET /api/tool-status?engine=UE5`：

| | 修复前 | 修复后 |
|---|---|---|
| `unreal` 状态 | `unavailable` | `ready` |
| `unreal` target | `UnrealEditor-Cmd.exe, UnrealEditor.exe, UNREAL_EDITOR, UE_EDITOR`（命令名，不是路径） | `C:\ue\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe` |
| `required_ready` | 1 / 3 | 2 / 3 |
| 整体 `status` | `degraded` | `degraded`（仅剩 ComfyUI，服务未启动） |

库内探测在同一时刻一直返回 `C:\ue\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe` —— 两份实现的落差就在这里。

服务级实测（真实 uvicorn 进程，`127.0.0.1:7871`，验证后已停止）：

```
health -> {'status': 'ok', 'agent': 'fantasy-agent-studio', 'mode': 'standalone'}

[engine=UE5] status=degraded required_ready=2/3 kind=unreal
   * comfyui   unavailable  http://127.0.0.1:8188, ...
   * blender   ready        C:/Program Files/Blender Foundation\Blender 5.2\blender.exe
   * unreal    ready        C:\ue\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe
     godot     ready        C:/Users\tutic\Downloads\Godot_v4.6.3-stable_win64\...console.exe
     github    ready        C:\Program Files\GitHub CLI\gh.EXE

MCP tool contracts -> 17 个
按 server 分布 -> {'unreal-mcp': 8, 'blender-mcp': 2, 'godot-mcp': 3, 'comfyui-mcp': 3, 'github-mcp': 1}
```

`comfyui` 的 `unavailable` 是正确结果——这次没有服务在监听，它的链路已在此前用真实服务验证过。

## 改动

| 文件 | 改动 |
|---|---|
| `apps/studio/app/main.py` | 删掉复制的 `_candidate_paths` / `_existing_env_path` / `_find_executable` / `_godot_candidate_key` / `_find_godot_executable`；`_probe_executable` 改为接受 `resolver`；新增 `_probe_unreal`，target 解析到真正会启动的 `-Cmd` 二进制；Blender / Godot / Unreal 全部改走 `local_tools` |
| `tests/test_studio_app.py` | 原 `test_studio_detects_downloaded_godot_install` 打桩已删的函数，改写为"打桩 resolver、断言面板跟随"；新增 Unreal `-Cmd` 显示与"引擎缺失仍报 unavailable"两条守卫 |
| `generated/mutation_check_all_guards.py` | 新增 S1（面板不再询问共享 resolver）、S2（面板报编辑器而非 `-Cmd`） |
| `AGENTS.md` | 在"引擎装在哪由 `local_tools` 解析"下补"状态面板也走这套解析" |

`unreal` target 现在显示 `-Cmd` 版，因为 headless commandlet 走的是它；只报 `UnrealEditor.exe` 会让"面板 ready"和"实际启动的进程"继续不一致。

## 验证

| 项 | 结果 |
|---|---|
| 后端测试 | 537 passed / 0 failed / 0 skipped（+2） |
| ruff | `check fantasy_agent tests apps scripts` 全过（与 CI 一致） |
| mutation 守卫 | **17/17 全红**，源文件字节级还原（新增 S1 / S2） |
| 服务级实测 | 4 个端点全部返回：`/health`、`/api/tool-status`×2、`/api/tool-contracts` |
| 前端 | 未改动前端文件，三道门未重跑 |

## 没做的

- **前端三道门没重跑**：本次只改后端与文档，前端源码与 API 字段形状都未变。
- **ComfyUI 未在本次复验**：其 `unavailable` 是"服务没起"的正确报告，链路此前已用真实服务验证。
- **`ruff format` 未执行**：该文件在 HEAD 上就有三处不符合 format（与本次改动无关），CI 只跑 `ruff check`，所以没有顺手 reformat 以免污染 diff。
