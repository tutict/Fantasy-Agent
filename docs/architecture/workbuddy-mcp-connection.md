# WorkBuddy 接入灵构工坊 Studio MCP

> 2026-11-05 本机实测记录。面向人的说明用简体中文；实现标识（`mcpServers`、`/mcp`、`job_id`）保持英文。
> 服务端实现见 `apps/studio/app/mcp_server.py` 与 `mcp_connection.py`；Codex 侧的整体计划见
> `docs/superpowers/plans/2026-11-05-studio-mcp-workflow.md`。

## 结论

WorkBuddy 的自定义 MCP 配置支持 `type: "http"` + `url` + `headers`，可直连 Studio 同进程、同端口的
Streamable HTTP `/mcp`。凭据走 `${FANTASY_STUDIO_MCP_TOKEN}` 环境变量，不写进配置文件。配置写入后
**不会自动生效**：环境变量要重启客户端才可见，自定义 server 还要在连接器管理页手动信任。

`/mcp` 默认关闭，只监听 `127.0.0.1`，且校验 loopback peer、Host、Origin 与 Bearer Token。

## 配置片段

`~/.workbuddy/mcp.json`（已存在其它 server 时合并 `mcpServers`，不要覆盖整份文件）：

```json
{
  "mcpServers": {
    "fantasy-studio": {
      "type": "http",
      "url": "http://127.0.0.1:7860/mcp",
      "headers": {
        "Authorization": "Bearer ${FANTASY_STUDIO_MCP_TOKEN}"
      }
    }
  }
}
```

上面是形状示例，**权威片段取服务端返回值**（`url` 按实际服务端口生成，端口变化时别手抄示例）：

```bash
curl -s http://127.0.0.1:7860/api/mcp/connection/config
```

把返回里的 `workbuddy_json` 合并进 `~/.workbuddy/mcp.json`；`toml` 字段是 Codex 的片段，两者互不影响。

## 启用顺序

1. 启动 Studio（README 默认 `127.0.0.1:7860`），在「Codex 连接」的智能体连接面板开启连接并点「复制连接密钥」。
2. 把 Token 设为环境变量后重启 WorkBuddy：`setx FANTASY_STUDIO_MCP_TOKEN "<复制的 Token>"`。
   `setx` 不影响已运行的进程；未设置时配置里的占位符会保留并报 WARNING，鉴权必然失败。
3. 连接器管理页右上角「自定义连接器」入口，对 `fantasy-studio` 点 Trust。
4. 用 `/mcp` 看配置与诊断，确认工具列表出现 `fantasy-studio` 下的工具。
5. 轮换 Token 后必须同步更新环境变量并重启；旧 Token 立即失效。

## 实测证据（2026-11-05）

真实 Studio 进程 + `mcp==2.3.0` 官方 SDK 客户端，Token 只经显式复制端点取得、只存在内存中：

| 检查 | 结果 |
|---|---|
| 连接关闭时 `/mcp` | `503` |
| 无 Bearer / 错误 Bearer | `401` / `401` |
| `initialize` | 协议 `2025-11-25`，server `fantasy-studio 0.1.0`，instructions 自包含且短于服务端约定的上限（长度由守卫复核） |
| `tools/list` | 返回当前 `ToolRegistry` 的全部工具；数量以运行时输出为准，下方脚本会打印，不在此写死 |
| `call_tool list_projects` | `is_error=false`，中文 envelope 五字段齐全 |
| `~/.workbuddy/mcp.json` 形状验证 | 读回配置、按官方规则展开 `${...}`、连真实服务成功 |

可复算命令（连接已开启）：

```bash
set FANTASY_STUDIO_MCP_TOKEN=<连接面板复制的 Token>
.venv\Scripts\python.exe scripts\studio_mcp_smoke.py
```

脚本只做鉴权探针与 SDK 往返，不打印 Token、不写盘、不启动 Studio、不改动连接开关。

## 已知差异与未解决风险

| 风险 | 现状 / 处理 |
|---|---|
| MCP elicitation | 计划要求生产授权、资产审阅、候选采纳必须由用户原生表单确认。WorkBuddy CLI 中存在 `SdkElicitationClient`、`elicitation/create` 等基础设施，**但自定义 MCP server 的 form elicitation 是否生效未实测**。若客户端不声明该能力，这些操作会停在「待授权」，服务端不会自动批准。这是本次接入最需要真实客户端复验的一项。 |
| 机器级 HTTP 代理 | 本机 `HTTP_PROXY` 会劫持 `127.0.0.1` 请求，直连探测得到过 `502` 假象。SDK 客户端必须 `trust_env=False`；WorkBuddy 自定义 MCP 客户端是否同样绕过代理需在真实客户端复验。 |
| SDK 版本形态 | `mcp==2.3.0` 使用 `streamable_http_client` 与 `httpx2`（不是 v1 的 `streamablehttp_client`/`httpx`），结果字段全是 snake_case（`protocol_version`、`server_info`）。用旧字段名会让 `ClientSession` 的 task group 崩，并在服务端留下 `anyio.ClosedResourceError` 的误导性日志。 |
| 真实客户端验收边界 | 上述证据是「官方 SDK 客户端 + 真实 Studio 进程」，不是 WorkBuddy 对话内的真实调用。计划 Task 6 明确要求区分两者；本次不把 SDK 冒烟表述为 WorkBuddy 客户端验收。 |
| 进程常驻 | 冒烟用的是临时 Studio 进程，用完即停；长期使用时 Studio 必须自行常驻。 |
| 凭据 | Token 不进入仓库、不进入普通状态 DOM、不写进 `mcp.json`；轮换由用户主动触发。 |

## 不做的事

不自动修改 WorkBuddy 或 Codex 的全局安全策略，不默认开启 `/mcp`，不替用户批准任何生产动作。
