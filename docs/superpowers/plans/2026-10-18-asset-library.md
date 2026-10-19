# 游戏资产库：管理界面 + 开源资产录入（2026-10-18）

> 决策记录 + 分阶段计划。本文只记规则与理由，**不写死计数**——要数的地方都给了可复算命令。

## 0. 要解决什么

灵构工坊的资产今天散在三个地方，没有一个界面能回答「我这个项目到底有哪些资产」：

1. **生成产物**：Blender 导出的 glb 在 `generated/assets/`，ComfyUI 参考图在 `generated/comfyui/`，唯一的权威记录是 `generated/asset-approval-manifest.yaml` 里的审批决策（approved / needs_revision / rejected / pending_user_review）——它已经是 ingest 闸门读的那份文件。
2. **审批状态**：只在流程控制台的 approval gate 阶段展示，跑完一次执行就翻不到原文。
3. **开源资产**：完全没有入口。game jam 里用 Kenney / OpenGameArt 的资产是常态，现在它们躺在用户的下载目录里，与工作台无关。

本方案交付：一个 `/assets` 整页面板，同屏管理这两类资产，并支持把本机开源资产文件录入库中、记录溯源信息（license / 作者 / 来源 URL / sha256）。

## 1. 两个岔路口与取舍（已与工程师确认）

### 1.1 录入走本地文件，不开网络出口

全应用的既定姿态是**本地优先**：Studio 只听 `127.0.0.1`，ComfyUI 的远程端点要显式授权（`allow_remote_endpoint` 默认 false），没有任何对外 MCP 端点。「粘贴 URL 后端下载」会新开一个网络出口，随之而来的是任意 URL 抓取、内容类型、体积、解压（zip-slip）一整面新风险——这些值得单独一轮带自己的确认门，不搭车。

**录入的输入是本机文件路径**（用户已经把资产下载到本机），后端校验后**复制**进库。原始文件不动，删库条目删的是我们那份副本。

### 1.2 开源 + 生成资产一起管

生成资产的权威记录（审批 manifest）已经存在且是 ingest 闸门在读的那份；复用它是「一个真相」，另建一份生成资产清单等于造第二个。所以总览 = 录入库条目 + manifest 决策，同屏两类，可分别筛选。

## 2. 数据模型

### 2.1 库文件：`generated/asset-library/library.yaml`

```yaml
source: studio.asset-library
schema_version: "0.1"
entries:
  - id: asset-1a2b3c4d5e6f        # assert_safe_path_segment 过的目录名
    name: Kenney Nature Pack       # 人看的名字，可重复
    kind: mesh | texture | audio | other   # 由扩展名推断，可手改
    source: open_source            # 录入来源；生成资产不走这个文件
    original_name: nature-pack.glb # 用户给的文件名，只作记录
    path: generated/asset-library/files/asset-1a2b3c4d5e6f/asset-1a2b3c4d5e6f.glb  # workspace 相对
    size_bytes: 1234567
    sha256: <64 hex>               # compute_artifact_identity，与审批 manifest 同一算法
    license: CC0                   # 自由文本；UI 给预设芯片
    author: Kenney
    source_url: https://kenney.nl/assets/nature-pack
    notes: ""
    tags: [nature, environment]
    ingested_at: "2026-10-18T06:00:00+00:00"
```

三条设计决定：

- **落盘走 `write_atomic`**。这个文件会被读回来做决策（列表、删除、总览计数），半截 YAML 的代价是静默的——与审批 manifest、`llm-api.json` 同一判据。
- **磁盘文件名用 `<id><ext>`，不用用户提供的文件名**。`Path(name).name` 防不住 Windows 尾点折叠（`victim.` 与 `victim` 是同一个文件，别名发生在文件系统内部，容错检查看不见），用户原名进 `original_name` 字段。
- **`schema_version` 不做迁移**，与仓库对版本不匹配的既定口径一致：拒绝，不迁移（`production_spec_runtime.py` 同款）。字段全部带默认值，旧文件配新模型读得进来。

### 2.2 大小与类型

- 单文件上限 256 MiB（`MAX_INGEST_BYTES`，模块常量）。超限在录入时明确报错，不是静默截断。
- **不支持压缩包**。zip-slip 是真实危害，要支持就得带专门的解压校验与测试，列为后续轮次，不塞进 v1。
- 扩展名 → `kind` 映射（glb/fbx/blend→mesh，png/jpg/webp→texture，wav/ogg/mp3→audio，其余 other）；`kind` 是记录不是闸门——用户可改。

## 3. 后端

### 3.1 `fantasy_agent/asset_library.py`（新模块）

纯函数 + 落盘，全部收口在 workspace 前缀内：

| 函数 | 行为 |
| --- | --- |
| `load_asset_library(workspace_root)` | 读 library.yaml；**文件不存在 = 空库**，不是错误（「文件不存在不算降级」纪律：不记 warning） |
| `save_asset_library(library, workspace_root)` | `write_atomic` 写回 |
| `ingest_asset(request, workspace_root)` | 解析源路径（绝对路径允许——这是用户显式指向的本机文件，同 `open_manual_correction_target` 的性质）→ 存在且是文件 → 大小上限 → 生成 id → 复制到 `files/<id><ext>` → 算 sha256 → 追加条目 → 原子写库 → 返回条目 |
| `remove_asset(asset_id, workspace_root)` | **条目文件的 resolved 路径必须在库目录内才删**（手改过的库文件若把 path 指到库外，删除必须拒绝而不是照做）→ 删文件 → 移除条目 → 原子写库 |
| `generated_asset_entries(workspace_root)` | 读审批 manifest 的 decisions，映射成与录入条目同形的展示记录（`source` 是生产者 `blender` / `comfyui`，`status` 即 decision） |
| `library_overview(workspace_root)` | 上面两者合成面板载荷 |

id 形状 `asset-<uuid4 hex[:12]>`，过 `assert_safe_path_segment`（它就是目录名）。manifest 缺失时 `generated_asset_entries` 返空列表——没有审阅过的项目就是没有生成资产记录，这不是错误。

### 3.2 端点（`apps/studio/app/main.py`）

| 端点 | 形态 |
| --- | --- |
| `GET /api/assets` | 总览：`{entries, generated, library_path, counts}` |
| `POST /api/assets` | 录入，同步（本地复制，秒级）；400 带中文 detail（源不存在 / 超限 / 路径不可读） |
| `DELETE /api/assets/{asset_id}` | 移除；条目不存在 404 |
| `GET /assets` | 前端路由，`_frontend_index_or()`，与 `/web-console` 同形态 |

请求/响应模型按本文件既有惯例用 `StrictModel` 就地定义（`ManualCorrectionOpenRequest` 那一族）。删除用的 `asset_id` 只做字符串精确匹配、**不拼进任何路径**——要删的文件路径是重新解析条目自己记录的 `path` 字段得来的，所以这里没有 `session_id` 那样的段安全问题；未知 id 答 404 而非 400（请求合法，东西不在）。

## 4. 前端

### 4.1 新整页面板 `assets`

- 路由 `/assets`（`PANEL_ROUTES`、`panelFromPathname`、后端 `GET /assets` 三处同步）。
- `StudioShell` 加 panel key、导航组（journey 六步之外的单条目组「资产」——它跨旅程，不属于任何一步，也不属于设置）、`panelEndpoint`、`visitedPanels` 帧 + `ErrorBoundary`。
- 组件 `assets/AssetLibrary.tsx` + `assets/parts.tsx`（按 §5 拆分判据：≥50 行、自带 `as-*` 前缀 → 独立文件 + 独立样式表）。
- 样式 `styles/assets.css`，前缀 `as-*`；约束全走既有守卫：token 阶梯、4 档断点、焦点环唯一来源 `ui.css`、无裸值。
- i18n：`studioI18n` 双语 key（字典一致性测试抓单边缺失）；中文模式不出现硬编码 `Fantasy Agent`（`test_product_name.py`）。

### 4.2 交互

- **两类分栏 + 筛选**：录入库（license / kind / tag 筛选）与生成资产（decision 状态徽标）。sha256 显示前 12 位，全值在 title。
- **录入表单**：文件路径（必填）、名字、license（预设芯片 + 自由文本）、作者、来源 URL、备注、标签。提交前展示将复制的源与目标——录入是写盘动作，但它是用户显式发起的单文件复制，不需要两段式确认门（那是引擎执行那类「起进程/烧时间」动作的礼节）。
- **删除**：`ConfirmDialog` 确认，文案写明「只删除库内副本，不动你下载的原始文件」。
- 错误渲染走 `errorMessageFromPayload` 同款解包（后端 detail 是中文直词或 422 列表）。

### 4.3 端点覆盖

`tests/test_frontend_endpoint_coverage.py`：三个 `/api/assets*` 端点被前端引用即合规，不进 `KNOWN_WITHOUT_UI`。

## 5. 分阶段与验证

| 阶段 | 内容 | 验证 |
| --- | --- | --- |
| P0 | `asset_library.py` + 合约 + `tests/test_asset_library.py` | `python scripts/run_tests.py tests/test_asset_library.py -q` |
| P1 | 端点 + `GET /assets` 路由 | `run_tests.py tests/test_studio_app.py tests/test_frontend_endpoint_coverage.py` |
| P2 | 前端面板 + 样式 + i18n | `npm run frontend:typecheck && frontend:test && frontend:build` |
| P3 | 守卫 + 变异用例（后端 harness 加 case；前端 harness 按需） | 两套 harness；每条新守卫先变异验证承重 |
| P4 | AGENTS.md「资产库」节、`docs/ui/architecture.md` 面板表、README | 全量四层 + CI |

**每条守卫的承重判据不变**：把守卫声称要拦的行为删掉，它必须红。没红过的守卫等于没有。

**执行结果（2026-10-18）**：P0–P4 全部完成。与计划的两处偏差已在上文就地改正：删除用的 `asset_id` 最终按字符串精确匹配、不拼路径（§3.2），`GeneratedAssetRecord.source` 最终取生产者而非 `generated`（§3.1）。落地的守卫与变异用例：后端 `tests/test_asset_library.py` 14 条 + `tests/test_studio_app.py` 4 条，变异用例 AL1–AL7；前端 `assets/AssetLibrary.test.tsx` 9 条 + `studio/StudioShell.test.tsx` 4 条，变异用例 FE11-1–FE11-5。

## 6. 明确不做（v1 范围外）

- URL 下载 / 压缩包解压（见 §1.1、§2.2）。
- 资产的引擎导入联动（把库条目直接喂给 Godot/Unreal ingest）——那是审批链的下一轮。
- 库条目的编辑（改 license / tags）——删除后重新录入是可接受的代价；要编辑就得给每条字段设计校验，单独一轮。
- 跨 workspace 的资产共享库。
