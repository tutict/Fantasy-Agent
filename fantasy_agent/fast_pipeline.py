"""
Fast Pipeline — 快速游戏 Demo 生成（5-15分钟垂直切片）

与主工作流的区别：
- 跳过复杂的 Director 编排
- 直接通过分层 Agent pipeline：策划 → 建模 → 引擎 → 测试 → 发布
- 目标是快速可玩验证，不是完整生产流程
- 用户可在关键节点插入人工审查

使用：
  python -m fantasy_agent.fast_pipeline --idea "游戏创意描述" [--auto]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

from .contracts import PromptRequest
from .fast_agents import (
    run_planning_agent,
    run_blender_batch,
    run_engine_agent,
    run_test_pipeline,
    run_publish_agent,
    build_and_package,
)

client = Anthropic()


def human_review(
    title: str,
    content: any,
    prompt: str = "输入 y 继续，n 终止，或输入修改意见",
) -> tuple[bool, str]:
    """
    暂停 pipeline，展示内容给用户审查。
    返回 (通过, 修改意见)。
    """
    print(f"\n{'='*60}")
    print(f"🔍 审查节点：{title}")
    print("=" * 60)

    if isinstance(content, dict):
        print(json.dumps(content, ensure_ascii=False, indent=2))
    elif isinstance(content, list):
        for i, item in enumerate(content):
            print(f"  [{i+1}] {json.dumps(item, ensure_ascii=False)}")
    else:
        print(content)

    print(f"\n{prompt}")
    print("  y = 通过继续  |  n = 终止  |  其他输入 = 提供修改意见后重新生成")

    user_input = input(">>> ").strip()

    if user_input.lower() == "y":
        return True, ""
    elif user_input.lower() == "n":
        print("Pipeline 已终止。")
        sys.exit(0)
    else:
        return False, user_input


def run_pipeline(user_idea: str, skip_reviews: bool = False, output_root: str = "./output"):
    """
    完整 pipeline 主入口。
    skip_reviews=True 时跳过所有人工审查节点（用于自动化测试）。
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(output_root) / f"session_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = session_dir / "assets"
    project_dir = session_dir / "project"
    output_dir = session_dir / "output"

    print(f"\n🎮 开始生成游戏 Demo")
    print(f"   创意：{user_idea}")
    print(f"   会话目录：{session_dir}\n")

    # ──────────────────────────────────────────────────────────────
    # Stage 1：策划 Agent
    # ──────────────────────────────────────────────────────────────
    print("【Stage 1】策划 Agent 生成 GDD...")
    gdd = None
    idea = user_idea

    while True:
        gdd = run_planning_agent(idea)
        (session_dir / "gdd.json").write_text(
            json.dumps(gdd, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  ✅ GDD 生成完成：{gdd['game_title']} ({gdd['engine_choice'].upper()})")

        if skip_reviews:
            break

        approved, feedback = human_review(
            title="策划审查 — GDD 确认",
            content={
                "游戏标题": gdd["game_title"],
                "类型": gdd["genre"],
                "维度": gdd["dimension"],
                "引擎": f"{gdd['engine_choice']} ({gdd['engine_reason']})",
                "核心玩法": gdd["core_loop"],
                "资产数量": len(gdd["asset_list"]),
                "关卡数": gdd["levels"],
                "风格": gdd["style"],
            },
            prompt="确认以上策划方向是否正确？",
        )

        if approved:
            break
        else:
            idea = f"{user_idea}\n\n【修改要求】{feedback}"
            print(f"  🔄 根据反馈重新生成 GDD...")

    # ──────────────────────────────────────────────────────────────
    # Stage 2：建模 Agent
    # ──────────────────────────────────────────────────────────────
    print(f"\n【Stage 2】建模 Agent 生成 {len(gdd['asset_list'])} 个资产...")
    assets_dir.mkdir(parents=True, exist_ok=True)

    blender_results = run_blender_batch(
        gdd=gdd,
        output_dir=str(assets_dir),
    )

    success_assets = [r for r in blender_results if r["ok"]]
    asset_paths = [r["glb_path"] for r in success_assets]

    print(f"  ✅ 建模完成：{len(success_assets)}/{len(blender_results)} 个资产成功")

    if not skip_reviews:
        approved, feedback = human_review(
            title="建模审查 — 资产确认",
            content=[
                {
                    "资产": r["asset_name"],
                    "状态": "✅ 成功" if r["ok"] else f"❌ 失败",
                    "路径": r.get("glb_path", ""),
                }
                for r in blender_results
            ],
            prompt="以上资产是否满足要求？（如需重做某个资产请说明）",
        )

    # ──────────────────────────────────────────────────────────────
    # Stage 3：引擎 Agent
    # ──────────────────────────────────────────────────────────────
    print(f"\n【Stage 3】引擎 Agent 生成 {gdd['engine_choice'].upper()} 项目...")
    project_dir.mkdir(parents=True, exist_ok=True)

    engine_result = run_engine_agent(
        gdd=gdd,
        asset_paths=asset_paths,
        project_dir=str(project_dir),
    )

    if not engine_result["ok"]:
        print(f"  ❌ 引擎 Agent 失败：{engine_result['error']}")
        sys.exit(1)

    print(f"  ✅ 项目文件生成完成，共 {len(engine_result['files'])} 个文件")

    # ──────────────────────────────────────────────────────────────
    # Stage 4：测试 Agent（自动循环）
    # ──────────────────────────────────────────────────────────────
    print(f"\n【Stage 4】测试 Agent 静态审查 + 自动修复...")
    test_result = run_test_pipeline(
        project_files=engine_result["files"],
        gdd=gdd,
        project_dir=str(project_dir),
        max_iterations=2,
    )

    if test_result["remaining_critical"]:
        print(
            f"  ⚠️ 仍有 {len(test_result['remaining_critical'])} 个 critical 问题未解决"
        )
        for issue in test_result["remaining_critical"]:
            print(
                f"     - [{issue['file']}:{issue['line']}] {issue['description']}"
            )
    else:
        print(f"  ✅ 所有 critical 问题已解决")

    if not skip_reviews:
        approved, _ = human_review(
            title="游戏审查 — 手动试玩验证",
            content=f"项目目录：{project_dir}\n请手动打开 Godot 试玩，确认核心玩法可以运行。",
            prompt="试玩后是否满意？（如有问题请描述）",
        )

    # ──────────────────────────────────────────────────────────────
    # Stage 5：发布 Agent
    # ──────────────────────────────────────────────────────────────
    print(f"\n【Stage 5】发布 Agent 生成构建文件...")
    output_dir.mkdir(parents=True, exist_ok=True)

    publish_result = run_publish_agent(
        gdd=gdd,
        engine=engine_result["engine"],
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )

    if not publish_result["ok"]:
        print(f"  ❌ 发布 Agent 失败：{publish_result['error']}")
        sys.exit(1)

    # 执行实际构建
    if engine_result["engine"] == "godot":
        print(f"\n[build] 执行 Godot headless 导出...")
        build_result = build_and_package(
            project_dir=str(project_dir),
            output_dir=str(output_dir),
            engine="godot",
            final_zip_name=f"{gdd['game_title'].replace(' ', '_')}_demo.zip",
        )
        if build_result["ok"]:
            print(f"\n🎉 完成！")
            print(f"   可执行文件：{build_result.get('exe_path', '无')}")
            print(f"   压缩包：{build_result['zip_path']}")
        else:
            print(
                f"\n⚠️ 构建失败（项目文件已生成，可手动导出）：{build_result['error']}"
            )

    print(f"\n   会话目录：{session_dir}")
    print(f"   GDD 文件：{session_dir}/gdd.json")

    return {
        "ok": True,
        "session_dir": str(session_dir),
        "gdd": gdd,
        "engine": engine_result["engine"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="游戏 Demo AI 生成 Pipeline")
    parser.add_argument("--idea", type=str, required=True, help="游戏创意描述")
    parser.add_argument("--auto", action="store_true", help="跳过所有人工审查节点（自动模式）")
    parser.add_argument("--output", type=str, default="./output", help="输出根目录")
    args = parser.parse_args()

    run_pipeline(user_idea=args.idea, skip_reviews=args.auto, output_root=args.output)
