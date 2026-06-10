#!/usr/bin/env python3
"""
Fast Pipeline 快速开始脚本

这个脚本帮助用户快速配置和验证 Fast Pipeline 环境。
"""

import json
import subprocess
import sys
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    if sys.version_info < (3, 9):
        print("❌ Python 版本太低，需要 3.9+，当前版本:", sys.version)
        return False
    print("✅ Python 版本检查通过:", sys.version.split()[0])
    return True


def check_anthropic_api():
    """检查 Anthropic API 密钥"""
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 环境变量未设置")
        return False
    if not api_key.startswith("sk-"):
        print("⚠️  ANTHROPIC_API_KEY 格式异常（通常以 sk- 开头）")
        return False
    print("✅ ANTHROPIC_API_KEY 检查通过")
    return True


def check_dependencies():
    """检查必要的 Python 包"""
    required = ["anthropic", "pydantic"]
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
            print(f"✅ {pkg} 已安装")
        except ImportError:
            print(f"❌ {pkg} 未安装")
            missing.append(pkg)

    if missing:
        print(f"\n💡 安装缺失的包：")
        print(f"   pip install {' '.join(missing)}")
        return False

    return True


def check_engines():
    """检查游戏引擎可用性"""
    import shutil

    engines = {
        "blender": "Blender 3D 建模工具",
        "godot": "Godot 游戏引擎",
    }

    results = {}
    for engine, desc in engines.items():
        path = shutil.which(engine)
        if path:
            print(f"✅ {engine} ({desc}) 已安装：{path}")
            results[engine] = path
        else:
            print(f"⚠️  {engine} ({desc}) 未在 PATH 中找到")
            results[engine] = None

    return results


def setup_config():
    """交互式设置配置文件"""
    print("\n" + "=" * 60)
    print("📝 Fast Pipeline 配置设置")
    print("=" * 60)

    config = {}

    # Blender 路径
    print("\n1️⃣  Blender 路径")
    print("   (留空则使用系统 PATH 中的 blender)")
    blender_path = input("   输入 Blender 可执行文件路径 (或留空): ").strip()
    config["blender_path"] = blender_path or "blender"

    # Godot 路径
    print("\n2️⃣  Godot 路径")
    print("   (留空则使用系统 PATH 中的 godot)")
    godot_path = input("   输入 Godot 可执行文件路径 (或留空): ").strip()
    config["godot_path"] = godot_path or "godot"

    # UE5 路径（可选）
    print("\n3️⃣  UE5 路径 (可选)")
    ue5_path = input("   输入 UE5 可执行文件路径 (或留空): ").strip()
    config["ue5_path"] = ue5_path or ""

    # 输出目录
    print("\n4️⃣  输出目录")
    print("   (生成的 demo 会保存在这个目录)")
    output_root = input("   输入输出目录 (默认 ./output): ").strip()
    config["output_root"] = output_root or "./output"

    # 超时设置
    print("\n5️⃣  超时设置 (高级)")
    print("   Blender 建模超时时间 (秒，默认 300)")
    blender_timeout = input("   输入或留空: ").strip()
    config["blender_timeout"] = int(blender_timeout) if blender_timeout else 300

    print("   Godot 导出超时时间 (秒，默认 600)")
    godot_timeout = input("   输入或留空: ").strip()
    config["godot_export_timeout"] = int(godot_timeout) if godot_timeout else 600

    # 保存配置
    config_path = Path.home() / ".fast_pipeline.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    print(f"\n✅ 配置已保存到：{config_path}")

    return config


def test_planning_agent():
    """快速测试 Planning Agent"""
    print("\n" + "=" * 60)
    print("🧪 测试 Planning Agent")
    print("=" * 60)

    try:
        from fantasy_agent.fast_agents import run_planning_agent

        print("\n生成简单 GDD (这可能需要 10-30 秒)...")
        gdd = run_planning_agent("一个简单的点击小游戏")

        print("\n✅ Planning Agent 测试通过！")
        print(f"   游戏标题：{gdd['game_title']}")
        print(f"   引擎选择：{gdd['engine_choice']}")
        print(f"   资产数量：{len(gdd['asset_list'])}")
        return True

    except Exception as e:
        print(f"\n❌ Planning Agent 测试失败：{e}")
        return False


def run_full_demo():
    """运行完整 demo"""
    print("\n" + "=" * 60)
    print("🎮 运行完整 Fast Pipeline Demo")
    print("=" * 60)

    idea = input("\n输入你的游戏创意 (或按 Enter 使用默认): ").strip()
    if not idea:
        idea = "一个 2D 横版跳跃游戏，玩家控制小猫收集鱼干，躲避乌鸦"

    print(f"\n创意：{idea}")
    print("\n启动 Fast Pipeline... (这将需要 5-15 分钟)")

    try:
        from fantasy_agent.fast_pipeline import run_pipeline

        result = run_pipeline(user_idea=idea, skip_reviews=True)

        print(f"\n🎉 成功！")
        print(f"   会话目录：{result['session_dir']}")
        print(f"   游戏标题：{result['gdd']['game_title']}")
        print(f"   引擎：{result['engine']}")

        return True

    except Exception as e:
        print(f"\n❌ Demo 失败：{e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主程序"""
    print("\n" + "=" * 60)
    print("🚀 Fantasy Agent Fast Pipeline 快速开始")
    print("=" * 60)

    # 检查清单
    checks = [
        ("Python 版本", check_python_version),
        ("Anthropic API", check_anthropic_api),
        ("依赖包", check_dependencies),
    ]

    all_passed = True
    for name, check_fn in checks:
        print(f"\n🔍 {name} 检查...")
        try:
            if not check_fn():
                all_passed = False
        except Exception as e:
            print(f"❌ 检查失败：{e}")
            all_passed = False

    # 检查引擎
    print(f"\n🔍 游戏引擎检查...")
    engines = check_engines()

    if not all_passed:
        print("\n❌ 某些必要条件未满足，请按照上述提示进行安装")
        return 1

    # 设置配置
    print("\n❓ 需要设置配置吗？")
    setup_choice = input("   (y)设置 / (s)跳过 / (q)退出: ").strip().lower()

    if setup_choice == "q":
        return 0

    config = None
    if setup_choice == "y":
        config = setup_config()

    # 选择下一步
    print("\n" + "=" * 60)
    print("✨ 配置完成！选择下一步操作")
    print("=" * 60)
    print("\n选项：")
    print("  1. 测试 Planning Agent")
    print("  2. 运行完整 Demo")
    print("  3. 显示使用说明")
    print("  4. 退出")

    choice = input("\n选择 (1-4): ").strip()

    if choice == "1":
        return 0 if test_planning_agent() else 1

    elif choice == "2":
        return 0 if run_full_demo() else 1

    elif choice == "3":
        print("\n" + "=" * 60)
        print("📖 使用说明")
        print("=" * 60)
        print("""
【自动模式 - 一键生成】
  python -m fantasy_agent.fast_pipeline \\
    --idea "你的游戏创意" \\
    --auto

【交互模式 - 人工审查】
  python -m fantasy_agent.fast_pipeline \\
    --idea "你的游戏创意"

【配置文件】
  ~/.fast_pipeline.json

【输出目录】
  ./output/session_YYYYMMDD_HHMMSS/
    ├── gdd.json           # 生成的设计文档
    ├── assets/            # 3D 模型文件
    ├── project/           # Godot 项目文件
    └── output/            # 最终可执行文件和文档

【文档】
  FAST_PIPELINE_GUIDE.md   # 完整用户指南
  UPGRADE_SUMMARY.md       # 升级说明

【示例】
  # 简单的点击游戏
  python -m fantasy_agent.fast_pipeline \\
    --idea "一个简单的点击小游戏" \\
    --auto

  # 2D 横版过关游戏
  python -m fantasy_agent.fast_pipeline \\
    --idea "一个 2D 横版过关游戏，玩家控制忍者跳跃躲避陷阱" \\
    --auto

  # 3D 冒险游戏
  python -m fantasy_agent.fast_pipeline \\
    --idea "一个 3D 第一人称冒险游戏，探索神秘遗迹" \\
    --auto
        """)
        return 0

    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
