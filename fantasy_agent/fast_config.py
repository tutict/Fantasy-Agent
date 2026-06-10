"""
Fast Pipeline 配置文件

包含引擎路径、输出目录、超时设置等
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FastPipelineConfig:
    """Fast Pipeline 全局配置"""

    # 引擎路径
    blender_path: str = "blender"
    godot_path: str = "godot"
    ue5_path: str = ""

    # 输出目录
    output_root: str = "./output"

    # 超时设置（秒）
    blender_timeout: int = 300
    godot_export_timeout: int = 600

    # AI 模型配置
    planning_model: str = "claude-sonnet-4-20250514"
    blender_model: str = "claude-sonnet-4-20250514"
    engine_model: str = "claude-sonnet-4-20250514"
    review_model: str = "claude-sonnet-4-20250514"
    publish_model: str = "claude-sonnet-4-20250514"

    # 温度参数
    planning_temperature: float = 0.8  # 创意需要发散
    blender_temperature: float = 0.2  # 代码需要精确
    engine_temperature: float = 0.2
    review_temperature: float = 0.0  # 审查必须严格
    publish_temperature: float = 0.1

    # 最大重试次数
    blender_max_retries: int = 2
    engine_max_retries: int = 2
    publish_max_retries: int = 1

    @classmethod
    def from_env(cls) -> "FastPipelineConfig":
        """从环境变量加载配置"""
        import os

        return cls(
            blender_path=os.getenv("BLENDER_PATH", "blender"),
            godot_path=os.getenv("GODOT_PATH", "godot"),
            ue5_path=os.getenv("UE5_PATH", ""),
            output_root=os.getenv("FAST_PIPELINE_OUTPUT", "./output"),
        )

    def save_to_json(self, path: str) -> None:
        """保存配置到 JSON 文件"""
        import json

        config_dict = {
            "blender_path": self.blender_path,
            "godot_path": self.godot_path,
            "ue5_path": self.ue5_path,
            "output_root": self.output_root,
            "blender_timeout": self.blender_timeout,
            "godot_export_timeout": self.godot_export_timeout,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(config_dict, indent=2, ensure_ascii=False))

    @classmethod
    def load_from_json(cls, path: str) -> "FastPipelineConfig":
        """从 JSON 文件加载配置"""
        import json

        config_dict = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**config_dict)
