from __future__ import annotations

from fantasy_agent.contracts import GDDDocument, GameplaySpec, LocaleCode
from fantasy_agent.i18n import normalize_locales, translate_field


SECTION_TITLES: dict[str, dict[LocaleCode, str]] = {
    "summary": {"en": "Summary", "zh-CN": "概要"},
    "player_fantasy": {"en": "Player Fantasy", "zh-CN": "玩家幻想"},
    "target_session": {"en": "Target Session", "zh-CN": "目标时长"},
    "design_pillars": {"en": "Design Pillars", "zh-CN": "设计支柱"},
    "core_verbs": {"en": "Core Verbs", "zh-CN": "核心动词"},
    "core_loop": {"en": "Core Loop", "zh-CN": "核心循环"},
    "systems": {"en": "Systems", "zh-CN": "系统"},
    "progression": {"en": "Progression", "zh-CN": "进程"},
    "win_failure": {"en": "Win And Failure", "zh-CN": "胜利与失败"},
    "level_beats": {"en": "Level Beats", "zh-CN": "关卡节奏"},
    "asset_needs": {"en": "Asset Needs", "zh-CN": "资产需求"},
    "unreal_notes": {"en": "Unreal Notes", "zh-CN": "Unreal 说明"},
    "blender_notes": {"en": "Blender Notes", "zh-CN": "Blender 说明"},
    "comfyui_notes": {"en": "ComfyUI Notes", "zh-CN": "ComfyUI 说明"},
    "qa_focus": {"en": "QA Focus", "zh-CN": "QA 重点"},
}


def _title(key: str, locale: LocaleCode) -> str:
    return SECTION_TITLES[key][locale]


def _localized_list(spec: GameplaySpec, base_path: str, values: list[str], locale: LocaleCode) -> list[str]:
    return [
        translate_field(spec, f"{base_path}.{index}", value, locale)
        for index, value in enumerate(values)
    ]


def _render_locale(spec: GameplaySpec, locale: LocaleCode) -> str:
    title = translate_field(spec, "title", spec.title, locale)
    loop_lines = "\n".join(
        f"{step.order}. "
        f"{translate_field(spec, f'core_loop.{index}.action', step.action, locale)}: "
        f"{translate_field(spec, f'core_loop.{index}.player_decision', step.player_decision, locale)} "
        f"{'Feedback' if locale == 'en' else '反馈'}: "
        f"{translate_field(spec, f'core_loop.{index}.feedback', step.feedback, locale)}"
        for index, step in enumerate(spec.core_loop)
    )
    systems = "\n".join(
        f"- {translate_field(spec, f'systems.{index}.name', system.name, locale)}: "
        f"{translate_field(spec, f'systems.{index}.purpose', system.purpose, locale)} "
        f"{'Inputs' if locale == 'en' else '输入'}: "
        f"{', '.join(_localized_list(spec, f'systems.{index}.inputs', system.inputs, locale))}. "
        f"{'Outputs' if locale == 'en' else '输出'}: "
        f"{', '.join(_localized_list(spec, f'systems.{index}.outputs', system.outputs, locale))}. "
        f"{'Failure pressure' if locale == 'en' else '失败压力'}: "
        f"{translate_field(spec, f'systems.{index}.failure_pressure', system.failure_pressure, locale)}"
        for index, system in enumerate(spec.systems)
    )
    beats = "\n".join(
        f"- {translate_field(spec, f'level_beats.{index}.name', beat.name, locale)} "
        f"({beat.duration_minutes} {'min' if locale == 'en' else '分钟'}): "
        f"{translate_field(spec, f'level_beats.{index}.gameplay_focus', beat.gameplay_focus, locale)} "
        f"{'Success' if locale == 'en' else '成功条件'}: "
        f"{translate_field(spec, f'level_beats.{index}.success_condition', beat.success_condition, locale)}"
        for index, beat in enumerate(spec.level_beats)
    )
    minutes_label = "minutes" if locale == "en" else "分钟"
    win_label = "Win" if locale == "en" else "胜利"
    failure_label = "Failure states" if locale == "en" else "失败状态"
    unlocks_label = "Unlocks" if locale == "en" else "解锁"

    markdown = f"""# {spec.title}

## {_title("summary", locale)}
{translate_field(spec, "logline", spec.logline, locale)}

## {_title("player_fantasy", locale)}
{translate_field(spec, "player_fantasy", spec.player_fantasy, locale)}

## {_title("target_session", locale)}
{spec.target_session_minutes} {minutes_label}

## {_title("design_pillars", locale)}
{chr(10).join(f"- {pillar}" for pillar in _localized_list(spec, "design_pillars", spec.design_pillars, locale))}

## {_title("core_verbs", locale)}
{", ".join(_localized_list(spec, "core_verbs", spec.core_verbs, locale))}

## {_title("core_loop", locale)}
{loop_lines}

## {_title("systems", locale)}
{systems}

## {_title("progression", locale)}
- {_title("target_session", locale)}: {spec.target_session_minutes} {minutes_label}
- {'First minute' if locale == 'en' else '第一分钟'}: {translate_field(spec, "progression.first_minute", spec.progression.first_minute, locale)}
- {'Midpoint shift' if locale == 'en' else '中段变化'}: {translate_field(spec, "progression.midpoint_shift", spec.progression.midpoint_shift, locale)}
- {'Final minutes' if locale == 'en' else '最后阶段'}: {translate_field(spec, "progression.final_minutes", spec.progression.final_minutes, locale)}
- {unlocks_label}: {", ".join(_localized_list(spec, "progression.unlocks", spec.progression.unlocks, locale))}

## {_title("win_failure", locale)}
{win_label}: {translate_field(spec, "win_state", spec.win_state, locale)}

{failure_label}:
{chr(10).join(f"- {state}" for state in _localized_list(spec, "failure_states", spec.failure_states, locale))}

## {_title("level_beats", locale)}
{beats}

## {_title("asset_needs", locale)}
{chr(10).join(f"- {asset}" for asset in _localized_list(spec, "asset_needs", spec.asset_needs, locale))}

## {_title("unreal_notes", locale)}
{chr(10).join(f"- {note}" for note in _localized_list(spec, "notes_for_unreal", spec.notes_for_unreal, locale))}

## {_title("blender_notes", locale)}
{chr(10).join(f"- {note}" for note in _localized_list(spec, "notes_for_blender", spec.notes_for_blender, locale))}

## {_title("comfyui_notes", locale)}
{chr(10).join(f"- {note}" for note in _localized_list(spec, "notes_for_comfyui", spec.notes_for_comfyui, locale))}

## {_title("qa_focus", locale)}
{chr(10).join(f"- {item}" for item in _localized_list(spec, "qa_focus", spec.qa_focus, locale))}
"""
    if locale != "en":
        markdown = markdown.replace(f"# {spec.title}", f"# {title}")
    return markdown


def render_gdd(spec: GameplaySpec) -> GDDDocument:
    locales = normalize_locales(spec.i18n.output_locales if spec.i18n else ["en"])
    markdown_by_locale = {locale: _render_locale(spec, locale) for locale in locales}
    if "en" in markdown_by_locale and "zh-CN" in markdown_by_locale:
        markdown = (
            f"{markdown_by_locale['en']}\n"
            "---\n\n"
            f"{markdown_by_locale['zh-CN']}"
        )
    else:
        markdown = next(iter(markdown_by_locale.values()))
    return GDDDocument(
        title=spec.title,
        markdown=markdown,
        source_schema_version=spec.schema_version,
        primary_locale="en" if "en" in locales else locales[0],
        available_locales=locales,
        markdown_by_locale=markdown_by_locale,
    )
