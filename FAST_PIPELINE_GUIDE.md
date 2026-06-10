# Fast Pipeline 集成指南

## 概述

Fast Pipeline 是 Fantasy Agent 的一条快速路径，用于快速生成 5-15 分钟的游戏 Demo 垂直切片。它绕过复杂的 Director 编排，直接通过分层 Agent pipeline 串联所有生产步骤。

## 架构

```
用户创意
   ↓
[Stage 1] 策划 Agent → GDD JSON
   ↓ (可选人工审查)
[Stage 2] Blender Agent → 资产批量生成 (.glb)
   ↓ (可选人工审查)
[Stage 3] 引擎 Agent → 路由 Godot/UE5，生成项目文件
   ↓ (自动)
[Stage 4] 测试 Agent → 静态审查 + 自动修复循环
   ↓ (可选人工审查)
[Stage 5] 发布 Agent → 生成 build.bat、README、game_info.json
   ↓
构建与打包 → game.exe + game_demo.zip
```

## 快速开始

### 1. 环境配置

首先配置引擎路径。创建 `~/.fast_pipeline.json`：

```json
{
  "blender_path": "C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe",
  "godot_path": "C:\\Users\\YourUser\\AppData\\Local\\Programs\\Godot\\Godot_v4.2.exe",
  "ue5_path": "C:\\Program Files\\Epic Games\\UE_5.3\\Engine\\Binaries\\Win64\\UnrealEditor.exe",
  "output_root": "./output"
}
```

或通过环境变量：

```bash
export BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"
export GODOT_PATH="C:\Users\YourUser\AppData\Local\Programs\Godot\Godot_v4.2.exe"
export FAST_PIPELINE_OUTPUT="./output"
```

### 2. 快速生成（自动模式）

```bash
python -m fantasy_agent.fast_pipeline \
  --idea "一个2D横版跳跃游戏，玩家控制小猫收集鱼干" \
  --auto
```

### 3. 交互生成（带人工审查）

```bash
python -m fantasy_agent.fast_pipeline \
  --idea "一个2D横版跳跃游戏，玩家控制小猫收集鱼干"
```

在每个关键节点（GDD 审查、资产审查、游戏试玩审查）暂停，等待用户输入：
- `y` — 通过继续
- `n` — 终止 pipeline
- 其他输入 — 作为修改意见，重新生成当前阶段

## 核心 Agent 说明

### Stage 1：Planning Agent

**职责**：将用户游戏创意转换为结构化 GDD JSON。

**输入**：用户创意描述（自然语言）

**输出**：
- `game_title`: 游戏标题
- `engine_choice`: godot 或 ue5（自动判断）
- `asset_list`: 资产清单，15个以内
- `levels`: 关卡数，1-3
- `palette`: 主色调（用于 Blender）
- 其他：玩法循环、胜利/失败条件、操作方式等

**硬约束**：
- 所有字段必须填写，禁止 null/空字符串
- asset_list 总面数不超过 200,000
- 直接输出 JSON，无前言/注释/markdown

### Stage 2：Blender Agent

**职责**：为每个资产生成 Blender Python 脚本，批量导出 .glb 格式。

**输入**：
- `asset`: {name, type, poly_budget, description}
- `palette`: 从 GDD 读取的主色调

**输出**：.glb 文件

**执行方式**：
```bash
blender --background --python script.py
```

**硬约束**：
- headless 环境，无 GUI 依赖
- 脚本首行：`# ASSET: name | TYPE: type | POLY_BUDGET: budget`
- 脚本末尾导出到 `OUTPUT_PATH` 变量
- 禁止调用 `bpy.ops.render.render()`（headless 不支持）

### Stage 3：Engine Agent

**职责**：根据 engine_choice 生成完整的 Godot/UE5 项目文件。

**输入**：
- `gdd`: 完整 GDD JSON
- `asset_paths`: Blender 导出的 .glb 文件路表

**输出**：完整项目目录结构
- Godot: `project.godot`, `scenes/`, `src/`, `export_presets.cfg`
- UE5: `setup.py`, `DefaultGame.ini`, `build.bat`

**文件格式**：
```
===FILE: res://project.godot===
[gd_resource type="ProjectSettings" format=3]
...
===END===
===FILE: res://src/player.gd===
extends CharacterBody2D
...
===END===
```

**硬约束**：
- 必须输出所有必要文件，缺一不可
- 所有数值参数加 `# [PARAM_NAME]` 锚点注释
- Godot 项目必须可直接 headless export

### Stage 4：Test Agent

**职责**：静态审查生成的代码，发现 critical/warning 问题，驱动自动修复。

**检查项**：
- **crash**: @onready 引用、get_node() 路径、null 检查
- **logic**: 物理运算错位、速度未清零、碰撞配置、胜利/失败条件
- **performance**: 每帧频繁调用、对象泄漏
- **missing_file**: 引用的资源路径不存在

**输出**：问题列表 JSON
```json
[
  {
    "file": "res://src/player.gd",
    "line": 42,
    "severity": "critical",
    "category": "crash",
    "description": "get_node('Player') 调用但节点不存在",
    "fix_suggestion": "改用 @onready var player = $Player"
  }
]
```

### Stage 5：Publish Agent

**职责**：生成构建脚本、玩家文档、游戏信息文件。

**输出**：
- `build.bat`: Windows 构建批处理脚本
- `README.md`: 玩家说明文档
- `game_info.json`: 机器可读的游戏元数据

## 集成到现有项目

### 1. 作为独立命令行工具

```bash
python -m fantasy_agent.fast_pipeline --idea "你的创意"
```

### 2. 作为 Python 库

```python
from fantasy_agent.fast_pipeline import run_pipeline

result = run_pipeline(
    user_idea="一个2D横版跳跃游戏",
    skip_reviews=True,  # 自动模式
    output_root="./output"
)

print(f"成功！GDD: {result['gdd']['game_title']}")
print(f"引擎：{result['engine']}")
print(f"输出目录：{result['session_dir']}")
```

### 3. 作为 ChatGPT Apps 后端

在现有 `chatgpt_app.py` 中集成：

```python
from fantasy_agent.fast_pipeline import run_pipeline

@app.route("/api/fast-pipeline", methods=["POST"])
def fast_pipeline_api():
    """Fast Pipeline API 端点"""
    data = request.json
    user_idea = data.get("idea", "")
    auto_mode = data.get("auto", False)
    
    result = run_pipeline(user_idea, skip_reviews=auto_mode)
    return jsonify(result)
```

## 配置选项

通过 `FastPipelineConfig` 自定义行为：

```python
from fantasy_agent.fast_config import FastPipelineConfig
from fantasy_agent.fast_agents import run_planning_agent

config = FastPipelineConfig(
    blender_path="/usr/bin/blender",
    godot_path="/usr/local/bin/godot",
    planning_temperature=0.7,  # 降低策划的发散度
    blender_max_retries=3,     # 增加 Blender 重试次数
)

# 在 Agent 中使用
gdd = run_planning_agent(user_idea, config=config)
```

## 输出结构

```
output/
├── session_20240610_143022/
│   ├── gdd.json                    # 生成的 GDD 文档
│   ├── assets/
│   │   ├── player_character.glb
│   │   ├── ground_tile.glb
│   │   └── ...
│   ├── project/                    # Godot 项目文件
│   │   ├── project.godot
│   │   ├── export_presets.cfg
│   │   ├── scenes/
│   │   │   ├── main.tscn
│   │   │   └── player.tscn
│   │   └── src/
│   │       ├── player.gd
│   │       └── game_manager.gd
│   └── output/
│       ├── build.bat
│       ├── README.md
│       ├── game_info.json
│       ├── game.exe               # 可执行文件（如导出成功）
│       └── game_demo.zip          # 打包交付物
```

## 故障排除

### Blender 脚本执行失败

```
[blender] ❌ 第1次失败: ModuleNotFoundError: No module named 'bpy'
```

确保使用 Blender 自带的 Python 环境或正确配置 `BLENDER_PATH`。

### Godot headless export 超时

```
[publish] Godot 导出失败: timeout
```

增加超时时间：

```python
config = FastPipelineConfig(godot_export_timeout=1200)
```

### AI API 超时

```
anthropic.APIError: Request timed out
```

检查网络连接或 ANTHROPIC_API_KEY 配置。

## 与现有 Agent 架构的关系

| 特性 | Fast Pipeline | Director 编排 |
|------|---|---|
| 目标 | 快速 demo (5-15min) | 完整生产 (1-2h) |
| 路由 | 直接 pipeline | 多层 Director |
| 人工审查 | 3 个关键节点 | 每个 Agent 前 |
| 可配置性 | 低 | 高 |
| 初次运行时间 | 10-30 分钟 | 1-2 小时 |
| 适用场景 | 创意探索、快速验证 | 正式生产 |

Fast Pipeline 和 Director 编排可以共存：
- 快速验证 demo → Fast Pipeline
- 细化和生产级开发 → Director 编排

## 下一步

1. **视觉内容生成**：集成 ComfyUI Worker 为 UI/环境生成参考图
2. **性能优化**：并行执行多个 Blender 资产生成
3. **打包扩展**：支持 WebGL/移动端导出
4. **反馈循环**：基于 QA 结果自动调整玩法参数

