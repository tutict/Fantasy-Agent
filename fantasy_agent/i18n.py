from __future__ import annotations

import re

from fantasy_agent.contracts import GameplaySpec, I18nBundle, LocaleCode, PromptRequest


SUPPORTED_LOCALES: tuple[LocaleCode, ...] = ("en", "zh-CN")

AXIS_ZH = {
    "stealth": "潜行",
    "survival": "生存",
    "puzzle": "解谜",
    "combat": "战斗",
    "mobility": "机动",
    "systems": "系统互动",
}

VERB_ZH = {
    "scout": "侦察",
    "hide": "隐藏",
    "distract": "干扰",
    "extract": "撤离",
    "gather": "收集",
    "craft": "制作",
    "route": "规划路线",
    "endure": "坚持生存",
    "observe": "观察",
    "combine": "组合",
    "trigger": "触发",
    "solve": "解开",
    "position": "站位",
    "attack": "攻击",
    "evade": "闪避",
    "recover": "恢复",
    "dash": "冲刺",
    "steer": "操控",
    "boost": "加速",
    "risk": "冒险",
    "explore": "探索",
    "interact": "互动",
    "adapt": "适应",
    "complete": "完成",
}


def normalize_locales(locales: list[LocaleCode] | None) -> list[LocaleCode]:
    requested = locales or ["en", "zh-CN"]
    normalized: list[LocaleCode] = []
    for locale in requested:
        if locale in SUPPORTED_LOCALES and locale not in normalized:
            normalized.append(locale)
    return normalized or ["en"]


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def zh_title_from_prompt(prompt: str, fallback_title: str) -> str:
    compact = re.sub(r"\s+", "", prompt.strip())
    if contains_cjk(compact):
        return compact[:18] or fallback_title
    return f"{fallback_title} 原型"


def build_i18n_bundle(
    request: PromptRequest,
    spec: GameplaySpec,
    axis: str,
    verbs: list[str],
) -> I18nBundle:
    locales = normalize_locales(request.output_locales)
    field_translations: dict[str, dict[LocaleCode, str]] = {}

    def add(path: str, en: str, zh_cn: str) -> None:
        translations: dict[LocaleCode, str] = {}
        if "en" in locales:
            translations["en"] = en
        if "zh-CN" in locales:
            translations["zh-CN"] = zh_cn
        field_translations[path] = translations

    prompt = request.prompt.strip()
    zh_title = zh_title_from_prompt(prompt, spec.title)
    add("title", spec.title, zh_title)
    add(
        "logline",
        spec.logline,
        f"一个 {spec.target_session_minutes} 分钟的可玩原型，围绕「{prompt}」展开，"
        "重点是清晰决策、快速反馈和可完成目标。",
    )
    add(
        "player_fantasy",
        spec.player_fantasy,
        f"通过可重复练习掌握一个紧凑的{AXIS_ZH.get(axis, axis)}挑战。",
    )

    design_pillars_zh = [
        "任何时刻都只有一个清晰目标",
        "每个机制都必须改变玩家决策",
        "失败要教会下一次尝试",
        "资产用于解释玩法空间",
    ]
    for index, value in enumerate(spec.design_pillars):
        add(f"design_pillars.{index}", value, design_pillars_zh[index])

    for index, verb in enumerate(verbs):
        add(f"core_verbs.{index}", verb, VERB_ZH.get(verb, verb))

    loop_zh = [
        (
            f"{VERB_ZH.get(verbs[0], verbs[0])}当前空间",
            "在压力升级前选择路线、目标或互动方式。",
            "镜头、UI 标记和音效确认可用选择。",
        ),
        (
            f"通过{VERB_ZH.get(verbs[1], verbs[1])}创造机会",
            "投入时间或有限资源来改善下一步。",
            "关卡状态变化会被目标追踪器和场景反馈清楚呈现。",
        ),
        (
            f"在压力下{VERB_ZH.get(verbs[2], verbs[2])}",
            "选择冒险推进，或回到更安全的位置重新组织。",
            "敌人、计时器、危险物或资源条会快速显示后果。",
        ),
        (
            f"{VERB_ZH.get(verbs[3], verbs[3])}目标并结算进度",
            "带着基础成果撤离，或继续争取更高完成评价。",
            "结算界面显示时间、失败原因、可选目标和重开入口。",
        ),
    ]
    for index, step in enumerate(spec.core_loop):
        action, decision, feedback = loop_zh[index]
        add(f"core_loop.{index}.action", step.action, action)
        add(f"core_loop.{index}.player_decision", step.player_decision, decision)
        add(f"core_loop.{index}.feedback", step.feedback, feedback)

    systems_zh = [
        (
            "目标状态",
            "保证原型可完成，避免玩家在空间里迷失。",
            "如果主目标变得不可达，玩家失败。",
        ),
        (
            "压力时钟",
            "在短垂直切片里制造紧迫感。",
            "压力到达上限后会强制撤离、失败或重开。",
        ),
        (
            "可读互动层",
            "让每个有用物体足够清楚，适合快速迭代。",
            "错误阅读会消耗时间或资源，而不是隐藏进度。",
        ),
    ]
    input_terms = {
        "player location": "玩家位置",
        "interaction events": "互动事件",
        "objective triggers": "目标触发器",
        "elapsed time": "经过时间",
        "alert level": "警戒等级",
        "mistake count": "失误次数",
        "overlap events": "重叠事件",
        "line traces": "射线检测",
        "player inventory": "玩家库存",
    }
    output_terms = {
        "active objective": "当前目标",
        "completion state": "完成状态",
        "restart state": "重开状态",
        "hazard intensity": "危险强度",
        "enemy aggression": "敌人进攻性",
        "score modifier": "分数修正",
        "interaction prompts": "互动提示",
        "state changes": "状态变化",
        "audio/visual feedback": "音画反馈",
    }
    for index, system in enumerate(spec.systems):
        name, purpose, failure = systems_zh[index]
        add(f"systems.{index}.name", system.name, name)
        add(f"systems.{index}.purpose", system.purpose, purpose)
        add(f"systems.{index}.failure_pressure", system.failure_pressure, failure)
        for input_index, value in enumerate(system.inputs):
            add(f"systems.{index}.inputs.{input_index}", value, input_terms.get(value, value))
        for output_index, value in enumerate(system.outputs):
            add(f"systems.{index}.outputs.{output_index}", value, output_terms.get(value, value))

    add(
        "progression.first_minute",
        spec.progression.first_minute,
        "在没有惩罚的情况下教学移动、镜头和第一个目标。",
    )
    add(
        "progression.midpoint_shift",
        spec.progression.midpoint_shift,
        "把主要动词与压力结合，让玩家必须提前计划。",
    )
    add(
        "progression.final_minutes",
        spec.progression.final_minutes,
        "要求玩家用完整循环完成一次明确的胜负结算。",
    )
    unlocks_zh = ["第一个目标后开放可选捷径", "中段后开放第二种互动", "完成后开放结算评分"]
    for index, unlock in enumerate(spec.progression.unlocks):
        add(f"progression.unlocks.{index}", unlock, unlocks_zh[index])

    add("win_state", spec.win_state, "在压力到达上限前完成主目标并抵达出口。")
    failure_zh = ["压力时钟到达最大值", "玩家生命或关键资源归零", "必要目标 Actor 被摧毁或放弃"]
    for index, failure in enumerate(spec.failure_states):
        add(f"failure_states.{index}", failure, failure_zh[index])

    beats_zh = [
        ("教学口袋区", "学习控制并识别目标语言。", "玩家完成第一次低风险互动。"),
        ("系统混合区", "在压力改变路线时使用核心动词。", "玩家完成中心目标链。"),
        ("最终推进", "用胜负压力解决完整循环。", "玩家抵达出口并获得表现反馈。"),
    ]
    asset_terms = {
        "start marker": "起点标记",
        "objective prop": "目标道具",
        "interaction prompt": "互动提示",
        "arena blockers": "场地阻挡件",
        "hazard markers": "危险标记",
        "feedback props": "反馈道具",
        "exit gate": "出口门",
        "final hazard": "最终危险物",
        "score trigger": "评分触发器",
    }
    for index, beat in enumerate(spec.level_beats):
        name, focus, success = beats_zh[index]
        add(f"level_beats.{index}.name", beat.name, name)
        add(f"level_beats.{index}.gameplay_focus", beat.gameplay_focus, focus)
        add(f"level_beats.{index}.success_condition", beat.success_condition, success)
        for asset_index, asset in enumerate(beat.required_assets):
            add(
                f"level_beats.{index}.required_assets.{asset_index}",
                asset,
                asset_terms.get(asset, asset),
            )

    asset_needs_zh = ["灰盒场地套件", "目标道具组", "危险标记组", "可读出口门", "简易 UI 目标追踪器"]
    for index, asset in enumerate(spec.asset_needs):
        add(f"asset_needs.{index}", asset, asset_needs_zh[index])

    qa_zh = [
        "新玩家能否在一到三次尝试内完成？",
        "每个失败状态是否解释了原因？",
        "循环能否不重启编辑器直接重玩？",
    ]
    for index, item in enumerate(spec.qa_focus):
        add(f"qa_focus.{index}", item, qa_zh[index])

    unreal_zh = [
        "第一版切片优先使用蓝图实现。",
        "把机制放在独立 Actor 中，并使用明确事件连接。",
        "暴露压力、冷却和目标计时等可调参数。",
    ]
    for index, note in enumerate(spec.notes_for_unreal):
        add(f"notes_for_unreal.{index}", note, unreal_zh[index])

    blender_zh = [
        "在风格化资产前先生成比例正确的灰盒网格。",
        "优先使用轮廓清楚、适合碰撞的模块化道具。",
        "按玩法角色命名导出物，而不是按视觉主题命名。",
    ]
    for index, note in enumerate(spec.notes_for_blender):
        add(f"notes_for_blender.{index}", note, blender_zh[index])

    term_translations = {
        "gameplay-first": {"en": "gameplay-first", "zh-CN": "玩法优先"},
        "vertical slice": {"en": "vertical slice", "zh-CN": "垂直切片"},
        "greybox": {"en": "greybox", "zh-CN": "灰盒"},
        "MCP": {"en": "MCP", "zh-CN": "MCP 工具协议"},
    }

    return I18nBundle(
        source_locale=request.source_locale,
        output_locales=locales,
        field_translations=field_translations,
        term_translations=term_translations,
    )


def translate_field(spec: GameplaySpec, path: str, fallback: str, locale: LocaleCode) -> str:
    if locale == "en" or spec.i18n is None:
        return fallback
    return spec.i18n.field_translations.get(path, {}).get(locale, fallback)
