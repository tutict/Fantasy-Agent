from __future__ import annotations

import re

from fantasy_agent.axis_templates import AXIS_TEMPLATES, verb_fields
from fantasy_agent.contracts import GameplaySpec, I18nBundle, LocaleCode, PromptRequest


SUPPORTED_LOCALES: tuple[LocaleCode, ...] = ("en", "zh-CN")

# Derived from the axis templates: one place knows what an axis is called.
AXIS_ZH = {key: template.zh_label for key, template in AXIS_TEMPLATES.items()}

VERB_ZH = {
    "sprint": "\u51b2\u523a",
    "vault": "\u7ffb\u8d8a",
    "wall-run": "\u5899\u8dd1",
    "slide": "\u6ed1\u94f2",
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
    "discern": "辨认",
    "choose": "选择",
    "compose": "编排",
    "support": "补位",
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

    def zh_at(values: list[str], index: int, fallback: str) -> str:
        return values[index] if index < len(values) else fallback

    def add(path: str, en: str, zh_cn: str) -> None:
        translations: dict[LocaleCode, str] = {}
        if "en" in locales:
            translations["en"] = en
        if "zh-CN" in locales:
            translations["zh-CN"] = zh_cn
        field_translations[path] = translations

    # The axis template owns both languages; `axis` always comes from
    # generation._detect_axis, so an unknown key is a real bug and a KeyError is
    # better than silently emitting generic Chinese.
    template = AXIS_TEMPLATES[axis]
    prompt = request.prompt.strip()
    zh_title = zh_title_from_prompt(prompt, spec.title)
    add("title", spec.title, zh_title)
    add(
        "logline",
        spec.logline,
        f"一个 {spec.target_session_minutes} 分钟的可玩原型，围绕「{prompt}」展开，"
        "重点是清晰决策、快速反馈和可完成目标。",
    )
    add("player_fantasy", spec.player_fantasy, template.narrative.zh_player_fantasy)

    if axis == "career":
        add("title", spec.title, "雾外之路")
        add(
            "logline",
            spec.logline,
            f"一个 {spec.target_session_minutes} 分钟的 Godot 应聘作品原型，把迷雾、外部 plan "
            "和转职策划的经历转化为可玩的自我证明。",
        )
    design_pillars_zh = template.narrative.zh_pillars
    for index, value in enumerate(spec.design_pillars):
        add(f"design_pillars.{index}", value, design_pillars_zh[index])

    for index, verb in enumerate(verbs):
        add(f"core_verbs.{index}", verb, VERB_ZH.get(verb, verb))

    verb_placeholders = verb_fields(verbs, [VERB_ZH.get(verb, verb) for verb in verbs])
    loop_zh = [
        (
            step.zh_action.format(**verb_placeholders),
            step.zh_decision.format(**verb_placeholders),
            step.zh_feedback.format(**verb_placeholders),
        )
        for step in template.loop
    ]
    for index, step in enumerate(spec.core_loop):
        action, decision, feedback = loop_zh[index]
        add(f"core_loop.{index}.action", step.action, action)
        add(f"core_loop.{index}.player_decision", step.player_decision, decision)
        add(f"core_loop.{index}.feedback", step.feedback, feedback)

    systems_zh = [
        (system.zh_name, system.zh_purpose, system.zh_failure)
        for system in template.systems
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
        "player proximity": "玩家距离",
        "borrowed plan count": "已使用 plan 数量",
        "self-route meter": "自我路线 meter",
        "plan card type": "plan 卡类型",
        "interview timer": "面试倒计时",
        "player choice history": "玩家选择历史",
        "memory fragments": "经历碎片",
        "board slots": "策划板槽位",
        "team crisis needs": "团队危机需求",
        "active gate": "当前门",
        "affordance color": "可用性配色",
        "alert decay": "警戒衰减",
        "arena control": "场地控制",
        "attack cost": "攻击消耗",
        "attempt count": "尝试次数",
        "available actions": "可用动作",
        "boost charge": "加速充能",
        "boost stock": "加速存量",
        "carry capacity": "负重上限",
        "catch-up marker": "追赶标记",
        "checkpoint overlaps": "检查点触发",
        "combined state": "组合后状态",
        "combo multiplier": "连段倍率",
        "consumed element": "已消耗元素",
        "corner marker": "弯道标记",
        "depletion state": "枯竭状态",
        "detection state": "发现状态",
        "dodge timing": "闪避时机",
        "drain rate": "消耗速率",
        "element state": "元素状态",
        "element stock": "元素存量",
        "enemy attack state": "敌人攻击状态",
        "exhausted state": "力竭状态",
        "exposure meter": "暴露 meter",
        "failure feedback": "失败反馈",
        "final grade": "最终评级",
        "forecast window": "预报窗口",
        "gap change": "差距变化",
        "gap timer": "差距计时",
        "gate streaks": "连续门数",
        "grip feedback": "抓地反馈",
        "guard displacement": "守卫位移",
        "hazard proximity": "危险物距离",
        "hint budget": "提示预算",
        "hit streak": "连续命中",
        "last known position": "最后已知位置",
        "missed gates": "错过的门",
        "movement penalty": "移动惩罚",
        "node richness": "资源点丰度",
        "noisemaker count": "噪音道具数量",
        "nudged affordance": "被提示的可用物",
        "objective distance": "目标距离",
        "opening state": "破绽状态",
        "partial rule": "部分规则",
        "patrol route": "巡逻路线",
        "patrol waypoints": "巡逻路径点",
        "player approach angle": "玩家接近角度",
        "player noise": "玩家噪音",
        "player velocity": "玩家速度",
        "posture damage": "架势伤害",
        "punish window": "惩罚窗口",
        "recommended line": "建议路线",
        "recovery rate": "恢复速率",
        "regen rate": "回复速率",
        "resource cost": "资源消耗",
        "resource gain": "资源获得",
        "resource stock": "资源存量",
        "restart point": "重开点",
        "route grade": "路线评级",
        "route opening": "路线开启",
        "route unlock": "路线解锁",
        "rule hint": "规则提示",
        "search behaviour": "搜索行为",
        "shadow feedback": "暗影反馈",
        "shelter stock": "庇护所库存",
        "shelter value": "庇护所价值",
        "slide windows": "滑铲窗口",
        "slot state": "槽位状态",
        "solve confidence": "解谜信心",
        "speed burst": "速度爆发",
        "speed feedback": "速度反馈",
        "stagger damage": "破防伤害",
        "stagger meter": "架势 meter",
        "stamina pool": "体力池",
        "state feedback": "状态反馈",
        "stock cost": "库存消耗",
        "surface tags": "表面标签",
        "target split": "目标分段",
        "threshold buffer": "阈值缓冲",
        "threshold warning": "阈值警告",
        "valid combination": "有效组合",
        "valid-move prompts": "有效动作提示",
        "vault timing": "翻越时机",
        "wall-run duration": "蹬墙时长",
        "weather state": "天气状态",
        "wind-up telegraph": "起手预兆",

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
        "fog density": "迷雾浓度",
        "objective clarity": "目标清晰度",
        "confidence feedback": "信心反馈",
        "time relief": "时间缓冲",
        "agency cost": "自我路线代价",
        "route branch": "路线分支",
        "prototype pitch score": "原型提案评分",
        "support action": "补位动作",
        "interview gate state": "应聘门状态",
        "active gate": "当前门",
        "affordance color": "可用性配色",
        "alert decay": "警戒衰减",
        "arena control": "场地控制",
        "attack cost": "攻击消耗",
        "attempt count": "尝试次数",
        "available actions": "可用动作",
        "boost charge": "加速充能",
        "boost stock": "加速存量",
        "carry capacity": "负重上限",
        "catch-up marker": "追赶标记",
        "checkpoint overlaps": "检查点触发",
        "combined state": "组合后状态",
        "combo multiplier": "连段倍率",
        "consumed element": "已消耗元素",
        "corner marker": "弯道标记",
        "depletion state": "枯竭状态",
        "detection state": "发现状态",
        "dodge timing": "闪避时机",
        "drain rate": "消耗速率",
        "element state": "元素状态",
        "element stock": "元素存量",
        "enemy attack state": "敌人攻击状态",
        "exhausted state": "力竭状态",
        "exposure meter": "暴露 meter",
        "failure feedback": "失败反馈",
        "final grade": "最终评级",
        "forecast window": "预报窗口",
        "gap change": "差距变化",
        "gap timer": "差距计时",
        "gate streaks": "连续门数",
        "grip feedback": "抓地反馈",
        "guard displacement": "守卫位移",
        "hazard proximity": "危险物距离",
        "hint budget": "提示预算",
        "hit streak": "连续命中",
        "last known position": "最后已知位置",
        "missed gates": "错过的门",
        "movement penalty": "移动惩罚",
        "node richness": "资源点丰度",
        "noisemaker count": "噪音道具数量",
        "nudged affordance": "被提示的可用物",
        "objective distance": "目标距离",
        "opening state": "破绽状态",
        "partial rule": "部分规则",
        "patrol route": "巡逻路线",
        "patrol waypoints": "巡逻路径点",
        "player approach angle": "玩家接近角度",
        "player noise": "玩家噪音",
        "player velocity": "玩家速度",
        "posture damage": "架势伤害",
        "punish window": "惩罚窗口",
        "recommended line": "建议路线",
        "recovery rate": "恢复速率",
        "regen rate": "回复速率",
        "resource cost": "资源消耗",
        "resource gain": "资源获得",
        "resource stock": "资源存量",
        "restart point": "重开点",
        "route grade": "路线评级",
        "route opening": "路线开启",
        "route unlock": "路线解锁",
        "rule hint": "规则提示",
        "search behaviour": "搜索行为",
        "shadow feedback": "暗影反馈",
        "shelter stock": "庇护所库存",
        "shelter value": "庇护所价值",
        "slide windows": "滑铲窗口",
        "slot state": "槽位状态",
        "solve confidence": "解谜信心",
        "speed burst": "速度爆发",
        "speed feedback": "速度反馈",
        "stagger damage": "破防伤害",
        "stagger meter": "架势 meter",
        "stamina pool": "体力池",
        "state feedback": "状态反馈",
        "stock cost": "库存消耗",
        "surface tags": "表面标签",
        "target split": "目标分段",
        "threshold buffer": "阈值缓冲",
        "threshold warning": "阈值警告",
        "valid combination": "有效组合",
        "valid-move prompts": "有效动作提示",
        "vault timing": "翻越时机",
        "wall-run duration": "蹬墙时长",
        "weather state": "天气状态",
        "wind-up telegraph": "起手预兆",

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
        template.progression.zh_first_minute,
    )
    add(
        "progression.midpoint_shift",
        spec.progression.midpoint_shift,
        template.progression.zh_midpoint_shift,
    )
    add(
        "progression.final_minutes",
        spec.progression.final_minutes,
        template.progression.zh_final_minutes,
    )
    unlocks_zh = template.progression.zh_unlocks
    for index, unlock in enumerate(spec.progression.unlocks):
        add(f"progression.unlocks.{index}", unlock, unlocks_zh[index])

    add("win_state", spec.win_state, template.narrative.zh_win_state)
    failure_zh = template.narrative.zh_failure_states
    for index, failure in enumerate(spec.failure_states):
        add(f"failure_states.{index}", failure, failure_zh[index])

    beats_zh = [
        (beat.zh_name, beat.zh_focus, beat.zh_success) for beat in template.beats
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
        "fog corridor": "迷雾走廊",
        "judgment marker": "评价标记",
        "self-route marker": "个人路线标记",
        "confidence UI": "信心 UI",
        "plan card kiosks": "plan 卡台",
        "memory fragment props": "经历碎片道具",
        "design board": "策划板",
        "timer UI": "倒计时 UI",
        "team crisis stations": "团队危机站点",
        "support action prompt": "补位动作提示",
        "interview gate": "应聘门",
        "fit score UI": "匹配评分 UI",
          "alert countdown UI": "警戒倒计时 UI",
        "alert level UI": "警戒等级 UI",
        "arena floor marker": "竞技场地板标记",
        "attempt counter UI": "尝试次数 UI",
        "boost gauge UI": "加速槽 UI",
        "boost pad": "加速板",
        "boost pickup": "加速拾取物",
        "boss arena marker": "首领场地标记",
        "central pedestal": "中央基座",
        "chained trigger set": "串联触发器组",
        "checkpoint gate": "检查点门",
        "combination feedback prop": "组合反馈道具",
        "corner marker set": "弯道标记组",
        "cover block set": "掩体方块组",
        "cover pillar set": "掩体柱组",
        "crafting bench prop": "制作台道具",
        "drain meter UI": "消耗 meter UI",
        "element pickup set": "元素拾取物组",
        "extraction gate": "撤离门",
        "extraction vent": "撤离通风口",
        "fall hazard markers": "坠落危险标记",
        "final gap ramp": "最终缺口坡道",
        "final straight marker": "最后直道标记",
        "finish gate": "终点门",
        "forecast board prop": "预报板道具",
        "hazard edge marker": "危险边缘标记",
        "hazard floor marker": "危险地面标记",
        "hazard zone marker": "危险区标记",
        "lap grade UI": "圈速评级 UI",
        "lit hall floor marker": "明亮中庭地面标记",
        "locked side door": "上锁的侧门",
        "low vault blockers": "低矮翻越障碍",
        "mixed corner set": "混合弯道组",
        "noisemaker pickup": "噪音道具拾取物",
        "objective cache prop": "目标补给道具",
        "objective vault prop": "目标密库道具",
        "optional room door": "可选房门",
        "overlapping patrol markers": "交叠巡逻标记",
        "patrol path ribbon": "巡逻路径带",
        "pressure timer UI": "压力计时 UI",
        "recovery pickup": "恢复拾取物",
        "resource node set": "资源点组",
        "rule plate prop": "规则铭牌道具",
        "second spawn marker": "第二刷怪标记",
        "shadow volume marker": "暗影体积标记",
        "shelter door trigger": "庇护所门触发器",
        "shelter marker": "庇护所标记",
        "shortcut ramp": "捷径坡道",
        "single slot pedestal": "单槽位基座",
        "slide barriers": "滑铲障碍",
        "soft timer UI": "软计时 UI",
        "solve grade trigger": "解谜评级触发器",
        "split timer UI": "分段计时 UI",
        "stagger break trigger": "破防触发器",
        "stagger meter UI": "架势 meter UI",
        "stamina UI": "体力 UI",
        "start gate": "起点门",
        "state highlight marker": "状态高亮标记",
        "survival grade UI": "生存评级 UI",
        "tell telegraph marker": "预兆提示标记",
        "tight gate set": "紧密门组",
        "track floor marker": "赛道路面标记",
        "training dummy prop": "训练假人道具",
        "two side room doors": "两侧房间门",
        "victory gate": "胜利之门",
        "vision cone marker": "视线锥标记",
        "wall-run panels": "蹬墙面板",
        "warmth pickup": "御寒拾取物",
        "weather state UI": "天气状态 UI",
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

    asset_needs_zh = template.zh_assets
    for index, asset in enumerate(spec.asset_needs):
        add(f"asset_needs.{index}", asset, zh_at(asset_needs_zh, index, asset))

    qa_zh = (
        [
            "新玩家能否在一到三次尝试内理解“拒绝不合适 plan”的价值？",
            "每个失败状态是否清楚说明玩家下一次该如何选择？",
            "策划板是否真的改变玩法目标，而不是只展示文字？",
        ]
        if axis == "career"
        else [
            "新玩家能否在一到三次尝试内完成？",
            "每个失败状态是否解释了原因？",
            "循环能否不重启编辑器直接重玩？",
        ]
    )
    for index, item in enumerate(spec.qa_focus):
        add(f"qa_focus.{index}", item, qa_zh[index])

    unreal_zh = [
        "第一版切片优先使用蓝图实现。",
        "把机制放在独立 Actor 中，并使用明确事件连接。",
        "暴露压力、冷却和目标计时等可调参数。",
    ]
    for index, note in enumerate(spec.notes_for_unreal):
        add(f"notes_for_unreal.{index}", note, unreal_zh[index])

    blender_zh = (
        ["先生成迷雾走廊、plan 卡台、策划板和应聘门的比例正确灰盒。", "优先保证标记、路径和交互站点的轮廓可读。", "按玩法角色命名导出物，例如 self_route_marker、plan_card_kiosk。"]
        if axis == "career"
        else [
            "在风格化资产前先生成比例正确的灰盒网格。",
            "优先使用轮廓清楚、适合碰撞的模块化道具。",
            "按玩法角色命名导出物，而不是按视觉主题命名。",
        ]
    )
    for index, note in enumerate(spec.notes_for_blender):
        add(f"notes_for_blender.{index}", note, blender_zh[index])

    comfyui_zh = template.narrative.zh_notes_for_comfyui
    for index, note in enumerate(spec.notes_for_comfyui):
        add(f"notes_for_comfyui.{index}", note, comfyui_zh[index])

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
