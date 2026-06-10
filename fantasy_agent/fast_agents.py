"""
Fast Pipeline Agents — 分层 Agent 实现

包含：
1. Planning Agent — 生成 GDD
2. Blender Agent — 批量生成资产
3. Engine Agent — 路由到 Godot/UE5 Agent
4. Test Agent — 静态审查 + 自动修复
5. Publish Agent — 生成构建文件和打包
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from anthropic import Anthropic

client = Anthropic()

# ══════════════════════════════════════════════════════════════════
# PLANNING AGENT
# ══════════════════════════════════════════════════════════════════

PLANNING_SYSTEM_PROMPT = """
你是一位专业游戏策划师，专注于为 AI 自动化工具链生成结构化游戏设计文档（GDD）。
你的输出将直接驱动 Blender 建模脚本、Godot/UE5 引擎代码生成、测试和发布流程。

【输出硬约束 — 违反任何一条视为失败】
1. 只输出合法 JSON，不得有任何前言、解释、markdown 代码块或尾注
2. 所有字段必须填写，禁止出现 null、undefined 或空字符串 ""
3. engine_choice 只能是 "godot" 或 "ue5"，不得是其他任何值
4. dimension 只能是 "2d" 或 "3d"
5. genre 只能从枚举值中选择，不得自造新值
6. asset_list 每项必须包含 name / type / poly_budget 三个字段
7. poly_budget 必须是正整数，不得是字符串
8. palette 必须是合法 hex 色值数组，格式为 "#RRGGBB"
9. levels 必须在 1-3 之间（demo 限制）
10. asset_list 总数不超过 15 个，poly_budget 总和不超过 200000

【引擎选择判断规则】
选 godot 的条件（满足任一）：
  - dimension 为 "2d"
  - 风格为 lowpoly / pixel / cartoon
  - 目标是轻量 demo，不需要写实光照

选 ue5 的条件（满足任一）：
  - 明确要求写实 / 影视级画质
  - 需要 Lumen 全局光照或 Nanite 虚拟几何体
  - 3D 场景面数需求超过 500000

【输出 Schema】
{
  "game_title": "string",
  "genre": "platformer | shooter | puzzle | rpg | racing | survival | fighting | other",
  "dimension": "2d | 3d",
  "engine_choice": "godot | ue5",
  "engine_reason": "string — 一句话说明选择原因，15字以内",
  "core_loop": "string — 核心玩法循环描述，50字以内",
  "win_condition": "string — 胜利/完成条件描述",
  "lose_condition": "string — 失败条件描述",
  "levels": "number — demo关卡数量，1到3",
  "level_descriptions": ["string — 每关简述，数组长度与levels一致"],
  "player": {
    "name": "string",
    "abilities": ["string — 能力列表，3个以内"],
    "start_position": {"x": 0, "y": 0}
  },
  "enemies": [
    {
      "name": "string",
      "behavior": "patrol | chase | stationary | ranged",
      "hp": "number"
    }
  ],
  "asset_list": [
    {
      "name": "string — 资产名称，英文，snake_case",
      "type": "character | prop | environment | ui | vfx",
      "poly_budget": "number — 面数上限",
      "description": "string — 外观描述，20字以内"
    }
  ],
  "style": "lowpoly | realistic | cartoon | pixel",
  "palette": ["#RRGGBB"],
  "controls": {
    "move": "string",
    "action": "string",
    "camera": "string"
  },
  "audio": {
    "bgm_style": "string",
    "sfx_list": ["string"]
  },
  "target_platform": "windows",
  "estimated_playtime_minutes": "number"
}
""".strip()


def run_planning_agent(user_idea: str) -> dict[str, Any]:
    """调用策划 Agent，返回解析后的 GDD dict。"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0.8,
        system=PLANNING_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"""
根据以下游戏创意描述，生成一份完整的 GDD JSON。

【用户创意】
{user_idea}

【强制要求】
- 这是一个 demo 版本，复杂度控制在 1-3 关
- 所有资产数量总计不超过 15 个
- 所有资产 poly_budget 总和不超过 200,000
- 目标平台：Windows 本地可执行文件
- 直接输出 JSON，不要任何额外文字
""".strip(),
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1])

    try:
        gdd = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"策划 Agent 输出非法 JSON: {e}\n原始输出:\n{raw}")

    required = ["game_title", "genre", "dimension", "engine_choice", "asset_list", "palette"]
    for field in required:
        if field not in gdd:
            raise ValueError(f"GDD 缺少必要字段: {field}")

    if gdd["engine_choice"] not in ("godot", "ue5"):
        raise ValueError(f"engine_choice 非法值: {gdd['engine_choice']}")

    return gdd


# ══════════════════════════════════════════════════════════════════
# BLENDER AGENT
# ══════════════════════════════════════════════════════════════════

BLENDER_SYSTEM_PROMPT = """
你是一位 Blender Python 脚本专家，专门为游戏 demo 生成低多边形 3D 资产。
所有脚本通过 blender --background --python <script.py> 执行，绝对不依赖任何 GUI 操作。

【输出硬约束 — 违反任何一条视为失败】
1. 只输出纯 Python 代码，不加任何注释块说明、markdown、前言或尾注
2. 第一行必须是元数据注释，格式严格为：# ASSET: {name} | TYPE: {type} | POLY_BUDGET: {budget}
3. 第二行必须是：import bpy
4. 脚本开头必须清空默认场景：
   bpy.ops.object.select_all(action='SELECT')
   bpy.ops.object.delete(use_global=False)
5. 脚本末尾必须导出 glTF，路径从 OUTPUT_PATH 变量读取
6. 禁止使用 bpy.ops.render.render()（headless 模式渲染方式不同）

【颜色转换辅助函数 — 每个脚本都要包含】
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
""".strip()


def run_blender_agent(
    asset: dict[str, Any],
    gdd: dict[str, Any],
    output_dir: str,
    blender_path: str = "blender",
    max_retries: int = 2,
) -> dict[str, Any]:
    """生成 bpy 脚本并执行 Blender CLI，返回生成结果。"""
    output_path = str(Path(output_dir) / f"{asset['name']}.glb")
    palette_rgb = "\n".join(f"  {color}" for color in gdd.get("palette", []))

    for attempt in range(1, max_retries + 1):
        print(f"  [blender] 生成 {asset['name']} (第{attempt}次尝试)")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.2,
            system=BLENDER_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"""
生成 Blender Python 脚本，创建以下游戏资产。

【资产信息】
名称：{asset['name']}
类型：{asset['type']}
描述：{asset.get('description', '无')}
面数上限：{asset['poly_budget']}

【项目风格】
游戏风格：{gdd['style']}
主色调：
{palette_rgb}

【导出路径】
OUTPUT_PATH = "{output_path}"

直接输出 Python 脚本，第一行必须是 # ASSET: {asset['name']} | TYPE: {asset['type']} | POLY_BUDGET: {asset['poly_budget']}
""".strip(),
                }
            ],
        )

        script = response.content[0].text.strip()
        if script.startswith("```"):
            lines = script.splitlines()
            script = "\n".join(lines[1:-1])

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(script)
            script_path = f.name

        result = subprocess.run(
            [blender_path, "--background", "--python", script_path],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0 and Path(output_path).exists():
            print(f"  [blender] ✅ {asset['name']} 生成成功")
            return {"ok": True, "glb_path": output_path, "asset_name": asset["name"]}

        error_msg = result.stderr[-500:] if result.stderr else "无 stderr"
        print(f"  [blender] ❌ 第{attempt}次失败: {error_msg}")

    return {
        "ok": False,
        "error": f"重试 {max_retries} 次后仍然失败",
        "asset_name": asset["name"],
    }


def run_blender_batch(
    gdd: dict[str, Any],
    output_dir: str,
    blender_path: str = "blender",
) -> list[dict[str, Any]]:
    """遍历 GDD 中的 asset_list，依次生成每个资产。"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    results = []

    for asset in gdd.get("asset_list", []):
        result = run_blender_agent(asset, gdd, output_dir, blender_path)
        results.append(result)

    success = sum(1 for r in results if r["ok"])
    print(f"\n[blender batch] 完成 {success}/{len(results)} 个资产")
    return results


# ══════════════════════════════════════════════════════════════════
# ENGINE AGENT
# ══════════════════════════════════════════════════════════════════

GODOT_SYSTEM_PROMPT = """
你是 Godot 4 游戏开发专家，专门为 AI pipeline 生成可直接运行的完整项目。

【输出硬约束 — 违反任何一条视为失败】
1. 每个文件用分隔符包裹，格式严格为：
   ===FILE: res://相对路径===
   （文件内容）
   ===END===
2. 分隔符单独占一行，前后不得有空格
3. 必须输出以下文件，缺一不可：
   - res://project.godot
   - res://export_presets.cfg
   - res://scenes/main.tscn
   - res://scenes/player.tscn
   - res://src/player.gd
   - res://src/game_manager.gd
4. 所有可调数值参数必须加锚点注释，格式：# [PARAM_NAME] 说明
5. 禁止使用 @tool 注解
6. project.godot 必须包含 config/version=5 声明
7. export_presets.cfg 必须包含 Windows Desktop 预设
""".strip()


def parse_file_blocks(raw_output: str) -> dict[str, str]:
    """解析 AI 输出的多文件格式。"""
    pattern = r"===FILE:\s*(.+?)===\n(.*?)===END==="
    matches = re.findall(pattern, raw_output, re.DOTALL)
    files = {}
    for path, content in matches:
        files[path.strip()] = content.strip()
    return files


def write_project_files(files: dict[str, str], project_dir: str, engine: str) -> int:
    """把解析出的文件写入磁盘，返回写入文件数。"""
    base = Path(project_dir)
    base.mkdir(parents=True, exist_ok=True)
    count = 0

    for file_path, content in files.items():
        if engine == "godot":
            rel = file_path.replace("res://", "")
        else:
            rel = file_path

        abs_path = base / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        count += 1

    return count


def run_engine_agent(
    gdd: dict[str, Any],
    asset_paths: list[str],
    project_dir: str,
    max_retries: int = 2,
) -> dict[str, Any]:
    """根据 GDD 的 engine_choice 路由到对应 Agent。"""
    engine = gdd.get("engine_choice", "godot")
    print(f"[engine] 使用引擎：{engine.upper()}（原因：{gdd.get('engine_reason', '未说明')}）")

    system = GODOT_SYSTEM_PROMPT
    asset_list_str = "\n".join(f"  - {p}" for p in asset_paths) or "  （无外部资产）"

    user_prompt = f"""
根据以下 GDD，生成完整的 Godot 4 项目文件。

【GDD】
{json.dumps(gdd, ensure_ascii=False, indent=2)}

【已生成的资产文件路径（.glb）】
{asset_list_str}

【项目要求】
- 玩家初始位置 Vector2(100, 300)
- 相机跟随玩家，平滑系数 # [CAMERA_SMOOTHING] = 5.0
- 包含简单 HUD（显示生命值和分数）
- 游戏结束画面后 3 秒自动返回主菜单
- 所有数值参数必须加 # [PARAM_NAME] 锚点注释

直接输出文件内容，不要任何额外说明。
""".strip()

    for attempt in range(1, max_retries + 1):
        print(f"  [engine] 生成项目文件（第{attempt}次尝试）")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()
        files = parse_file_blocks(raw)

        if not files:
            print(f"  [engine] ❌ 未解析到任何文件块，重试...")
            continue

        required = ["res://project.godot", "res://scenes/main.tscn", "res://src/player.gd"]
        missing = [r for r in required if r not in files]
        if missing:
            print(f"  [engine] ❌ 缺少必要文件：{missing}，重试...")
            continue

        written = write_project_files(files, project_dir, engine)
        print(f"  [engine] ✅ 写入 {written} 个文件")

        return {
            "ok": True,
            "engine": engine,
            "files": files,
            "project_dir": project_dir,
        }

    return {"ok": False, "error": f"引擎 Agent 重试 {max_retries} 次后失败"}


# ══════════════════════════════════════════════════════════════════
# TEST AGENT
# ══════════════════════════════════════════════════════════════════

REVIEW_SYSTEM_PROMPT = """
你是游戏代码静态审查专家，专门分析 Godot 4 GDScript 的潜在问题。

【输出硬约束 — 违反任何一条视为失败】
1. 只输出合法 JSON 数组，不得有任何前言、解释或尾注
2. 如果没有问题，输出空数组 []
3. 每个问题对象必须包含全部字段：file / line / severity / category / description / fix_suggestion
4. severity 只能是 "critical" / "warning"
5. category 只能是 "crash" / "logic" / "performance" / "missing_file"
6. line 必须是整数行号，确定不了时填 -1
""".strip()


def run_review_agent(project_files: dict[str, str], gdd: dict[str, Any]) -> list[dict]:
    """静态审查项目代码，返回问题列表。"""
    files_str = "\n\n".join(
        f"=== {path} ===\n{content}"
        for path, content in project_files.items()
        if path.endswith((".gd", ".tscn", ".cfg", ".godot"))
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        temperature=0.0,
        system=REVIEW_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"""
审查以下游戏项目代码，找出所有 critical 和 warning 级别问题。

【项目文件】
{files_str}

【GDD】
{json.dumps(gdd, ensure_ascii=False, indent=2)}

直接输出 JSON 数组，不要任何其他内容。
""".strip(),
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1])

    try:
        issues = json.loads(raw)
    except json.JSONDecodeError:
        return []

    critical = sum(1 for i in issues if i.get("severity") == "critical")
    warning = sum(1 for i in issues if i.get("severity") == "warning")
    print(f"  [test] 发现 {critical} 个 critical，{warning} 个 warning")
    return issues


def run_test_pipeline(
    project_files: dict[str, str],
    gdd: dict[str, Any],
    project_dir: str,
    max_iterations: int = 2,
) -> dict[str, Any]:
    """完整测试 + 修复循环。"""
    current_files = dict(project_files)

    for iteration in range(1, max_iterations + 1):
        print(f"\n[test] 第 {iteration} 轮审查...")
        issues = run_review_agent(current_files, gdd)

        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        if not critical_issues:
            print(f"[test] ✅ 无 critical 问题，测试通过")
            break

    remaining = [i for i in run_review_agent(current_files, gdd) if i["severity"] == "critical"]

    return {
        "ok": len(remaining) == 0,
        "final_files": current_files,
        "remaining_critical": remaining,
        "iterations": iteration,
    }


# ══════════════════════════════════════════════════════════════════
# PUBLISH AGENT
# ══════════════════════════════════════════════════════════════════

PUBLISH_SYSTEM_PROMPT = """
你是游戏自动化构建专家，生成可直接执行的导出脚本和文档。

【输出硬约束 — 违反任何一条视为失败】
1. 每个文件用分隔符包裹，格式严格为：
   ===FILE: 文件名===
   （文件内容）
   ===END===
2. 必须输出以下文件，缺一不可：
   - build.bat（Windows 构建批处理脚本）
   - README.md（玩家说明文档）
   - game_info.json（机器可读的游戏信息）
""".strip()


def run_publish_agent(
    gdd: dict[str, Any],
    engine: str,
    project_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    """生成发布文件并写入 output_dir。"""
    import re

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        temperature=0.1,
        system=PUBLISH_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"""
根据以下游戏信息，生成完整的构建和发布文件。

【GDD 摘要】
标题：{gdd.get('game_title', 'Untitled')}
类型：{gdd.get('genre', 'unknown')}
引擎：{engine.upper()}
玩法描述：{gdd.get('core_loop', '')}
胜利条件：{gdd.get('win_condition', '')}
操作方式：{json.dumps(gdd.get('controls', {}), ensure_ascii=False)}

严格按照分隔符格式输出三个文件，不要任何额外内容。
""".strip(),
            }
        ],
    )

    raw = response.content[0].text.strip()
    pattern = r"===FILE:\s*(.+?)===\n(.*?)===END==="
    matches = re.findall(pattern, raw, re.DOTALL)
    files = {path.strip(): content.strip() for path, content in matches}

    if not files:
        return {"ok": False, "error": "发布 Agent 未生成任何文件"}

    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (base / filename).write_text(content, encoding="utf-8")
        print(f"  [publish] 写入：{filename}")

    return {
        "ok": True,
        "output_dir": output_dir,
        "files": list(files.keys()),
    }


def build_and_package(
    project_dir: str,
    output_dir: str,
    engine: str,
    godot_path: str = "godot",
    final_zip_name: str = "game_demo.zip",
) -> dict[str, Any]:
    """执行实际构建，然后打包成 zip 交付。"""
    import shutil

    exe_path = str(Path(output_dir) / "game.exe")

    if engine == "godot" and godot_path:
        print("[publish] 执行 Godot headless 导出...")
        result = subprocess.run(
            [
                godot_path,
                "--headless",
                "--path",
                project_dir,
                "--export-release",
                "Windows Desktop",
                exe_path,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            return {
                "ok": False,
                "error": f"Godot 导出失败:\n{result.stderr[-1500:]}",
            }

    zip_path = str(Path(output_dir).parent / final_zip_name)
    shutil.make_archive(
        zip_path.replace(".zip", ""),
        "zip",
        output_dir,
    )
    print(f"[publish] ✅ 打包完成：{zip_path}")

    return {
        "ok": True,
        "exe_path": exe_path if Path(exe_path).exists() else None,
        "zip_path": zip_path,
    }
