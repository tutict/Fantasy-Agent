from __future__ import annotations

import re

from fantasy_agent.contracts import GameplaySpec, I18nBundle, LocaleCode, PromptRequest


SUPPORTED_LOCALES: tuple[LocaleCode, ...] = ("en", "zh-CN")

AXIS_ZH = {
    "parkour": "\u8dd1\u9177",
    "stealth": "潜行",
    "survival": "生存",
    "puzzle": "解谜",
    "combat": "战斗",
    "mobility": "机动",
    "career": "自我路线选择",
    "systems": "系统互动",
}

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

    if axis == "career":
        add("title", spec.title, "雾外之路")
        add(
            "logline",
            spec.logline,
            f"一个 {spec.target_session_minutes} 分钟的 Godot 应聘作品原型，把迷雾、外部 plan "
            "和转职策划的经历转化为可玩的自我证明。",
        )
        add(
            "player_fantasy",
            spec.player_fantasy,
            "作为游戏策划应聘者，把个人经历转化成清晰机制，并在团队关键时刻发挥价值。",
        )
        design_pillars_zh = [
            "个人经历必须变成可玩的决策",
            "外部 plan 只有适合自己路线时才有帮助",
            "失败要澄清下一次自我选择",
            "补位价值比耀眼数值更重要",
        ]
    else:
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

    if axis == "career":
        loop_zh = [
            (
                "在记忆房间里辨认评价噪音",
                "继续靠近自己的路线标记，或跟随更响亮的外部评价标记。",
                "选择自己的路线会让迷雾变薄；跟随借来的评价会让视野变窄。",
            ),
            (
                "在外部 plan 和个人路线之间取舍",
                "拿取安全感更强的 plan 卡暂缓倒计时，或拒绝它来保留自我路线。",
                "plan 卡会显示短期收益，但过度使用会降低自我路线 meter。",
            ),
            (
                "把经历碎片编排到策划板上",
                "在面试倒计时结束前，把碎片放为机制、约束或情绪节拍。",
                "策划板会把经历转化为可玩的目标、风险和补位动作。",
            ),
            (
                "补位团队危机并打开应聘门",
                "把有限专注力用在团队最薄弱的位置，而不是追求最显眼的角色。",
                "最终评分显示表达清晰度、岗位匹配、补位时机和拒绝了哪些不合适 plan。",
            ),
        ]
    else:
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

    if axis == "career":
        systems_zh = [
            (
                "评价迷雾",
                "把他人的评价变成可读压力，同时避免玩家在空间里空转。",
                "过度跟随评价噪音会隐藏个人路线，并迫使玩家重开。",
            ),
            (
                "Plan 卡取舍",
                "让外部建议既有用又有风险，使选路成为真正的玩法决策。",
                "叠加不适合自己的 plan 会耗尽自我路线 meter，并锁住最终策划板。",
            ),
            (
                "策划板转译",
                "把个人经历碎片转化成机制、约束和团队补位动作。",
                "只把经历当装饰不会打开应聘门；它必须改变一个可玩的决策。",
            ),
        ]
    else:
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
        "player proximity": "玩家距离",
        "borrowed plan count": "已使用 plan 数量",
        "self-route meter": "自我路线 meter",
        "plan card type": "plan 卡类型",
        "interview timer": "面试倒计时",
        "player choice history": "玩家选择历史",
        "memory fragments": "经历碎片",
        "board slots": "策划板槽位",
        "team crisis needs": "团队危机需求",
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

    if axis == "career":
        add(
            "progression.first_minute",
            spec.progression.first_minute,
            "教学移动、迷雾可读性，以及第一次在评价标记和个人路线标记之间选择。",
        )
        add(
            "progression.midpoint_shift",
            spec.progression.midpoint_shift,
            "引入 plan 卡：它们能缓解时间压力，但不适合自己路线时会削弱自我路线 meter。",
        )
        add(
            "progression.final_minutes",
            spec.progression.final_minutes,
            "要求玩家用经历碎片组装策划板，并在应聘门关闭前补位团队危机。",
        )
        unlocks_zh = ["拒绝第一张不适合的 plan 后开放自我路线 meter", "收集三块经历碎片后开放策划板", "策划板形成完整提案后开放团队补位动作"]
    else:
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

    if axis == "career":
        add("win_state", spec.win_state, "完成一块逻辑清楚的策划板，解决一次关键团队需求，并打开应聘门。")
        failure_zh = ["不合适的 plan 过多，评价迷雾遮住个人路线", "面试倒计时结束时策划板仍不可执行", "只做装饰表达，忽略团队真正需要的补位"]
    else:
        add("win_state", spec.win_state, "在压力到达上限前完成主目标并抵达出口。")
        failure_zh = ["压力时钟到达最大值", "玩家生命或关键资源归零", "必要目标 Actor 被摧毁或放弃"]
    for index, failure in enumerate(spec.failure_states):
        add(f"failure_states.{index}", failure, failure_zh[index])

    if axis == "career":
        beats_zh = [
            ("评价迷雾", "教学玩家阅读评价噪音、个人路线标记和可恢复的错误转向。", "玩家在信心耗尽前抵达第一个清晰路线标记。"),
            ("借来的 Plan 十字路口", "选择、拒绝或改写 plan 卡，同时收集经历碎片放入策划板。", "玩家把碎片放成会改变机制的内容，而不是装饰文字。"),
            ("应聘门前补位", "用完成的策划板，在时间压力下支持团队最需要的位置。", "玩家解决一个关键团队需求，并用可读评分打开应聘门。"),
        ]
    else:
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

    asset_needs_zh = (
        [
            "迷雾走廊灰盒套件",
            "评价标记组",
            "个人路线标记组",
            "外部 plan 卡台",
            "经历碎片拾取物组",
            "策划板 UI proxy",
            "团队危机站点组",
            "应聘门",
            "匹配评分 UI proxy",
        ]
        if axis == "career"
        else ["灰盒场地套件", "目标道具组", "危险标记组", "可读出口门", "简易 UI 目标追踪器"]
    )
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

    comfyui_zh = (
        ["为迷雾、plan 卡、策划板和应聘门生成原创视觉隐喻，不复刻被引用游戏 IP。", "优先保证评价噪音、个人路线标记和补位提示像图标一样清楚。", "视觉参考只服务作品集气质；灰盒循环可读后再进入风格化。"]
        if axis == "career"
        else [
            "只在玩法可读性需求明确后生成视觉参考。",
            "优先表现目标、危险、路线、材质和 UI 清晰度，而不是风格探索。",
            "生成图像只能作为经评审的参考，不能证明原型已经可玩。",
        ]
    )
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
