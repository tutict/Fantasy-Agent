"""Per-axis design templates for the deterministic gameplay generator.

Each mechanic axis owns one :class:`AxisTemplate`: the verbs, the core loop, the
systems, the progression curve, the level beats, the asset needs and the
narrative framing (fantasy, pillars, win/fail states, ComfyUI notes).

Why the templates carry both languages
--------------------------------------

``i18n.build_i18n_bundle`` pairs each English field with a zh-CN string by
*position*. Before this module existed, only the ``career`` axis had real zh-CN
copy — every other axis fell back to one generic set ("教学口袋区" /
"系统混合区"). That meant a parkour design documented its beats in English as
"Warmup Rooftop" while the Chinese GDD said "教学口袋区".

Specialising the English without moving the Chinese would have made things
worse: the document would look detailed while describing nothing. So the zh-CN
copy lives next to the English in the same record. The two cannot drift apart,
and adding an axis is a single edit in one place.

Adding an axis
--------------

1. Add the entry to :data:`AXIS_TEMPLATES`.
2. Make ``generation._detect_axis`` able to return the key.
3. Run ``tests/test_generation_axis.py`` — it asserts every axis in
   ``AXIS_TEMPLATES`` is reachable, that each has zh-CN copy, and that no two
   axes share a beat name, so a copy-pasted template fails immediately.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AxisLoopStep:
    """One step of the core loop, with its zh-CN rendering."""

    action: str
    player_decision: str
    feedback: str
    zh_action: str
    zh_decision: str
    zh_feedback: str


@dataclass(frozen=True)
class AxisSystem:
    """A system spec plus zh-CN copy for its player-facing fields.

    ``inputs`` / ``outputs`` are engine-facing term lists; they are translated
    through ``i18n.input_terms`` / ``i18n.output_terms`` instead of being
    carried here, so every axis can reuse the same vocabulary.
    """

    name: str
    purpose: str
    inputs: list[str]
    outputs: list[str]
    failure_pressure: str
    zh_name: str
    zh_purpose: str
    zh_failure: str


@dataclass(frozen=True)
class AxisProgression:
    """The three-part difficulty curve and its unlocks."""

    first_minute: str
    midpoint_shift: str
    final_minutes: str
    unlocks: list[str]
    zh_first_minute: str
    zh_midpoint_shift: str
    zh_final_minutes: str
    zh_unlocks: list[str]


@dataclass(frozen=True)
class AxisBeat:
    """A level beat. Durations come from ``generation._beat_durations``."""

    name: str
    gameplay_focus: str
    required_assets: list[str]
    success_condition: str
    zh_name: str
    zh_focus: str
    zh_success: str


@dataclass(frozen=True)
class AxisNarrative:
    """Framing copy: fantasy, pillars, win/fail states, ComfyUI guidance."""

    player_fantasy: str
    design_pillars: list[str]
    win_state: str
    failure_states: list[str]
    notes_for_comfyui: list[str]
    zh_player_fantasy: str
    zh_pillars: list[str]
    zh_win_state: str
    zh_failure_states: list[str]
    zh_notes_for_comfyui: list[str]


@dataclass(frozen=True)
class AxisTemplate:
    """Everything that makes one mechanic axis feel like itself."""

    verbs: list[str]
    loop: list[AxisLoopStep]
    systems: list[AxisSystem]
    progression: AxisProgression
    beats: list[AxisBeat]
    assets: list[str]
    zh_assets: list[str]
    narrative: AxisNarrative
    #: zh-CN name of the axis, used in generated prose ("紧凑的潜行挑战").
    zh_label: str
    #: Default enemy roster as (name, behavior, hp, count). Empty means none.
    enemies: list[tuple[str, str, int, int]] = field(default_factory=list)


_PARKOUR = AxisTemplate(
    zh_label="跑酷",
    verbs=["sprint", "vault", "wall-run", "slide"],
    loop=[
        AxisLoopStep(
            action="Sprint toward the next checkpoint gate",
            player_decision="Choose the fast exposed lane or the safer recovery lane before momentum drops.",
            feedback="Speed lines, footstep cadence, and checkpoint color show whether momentum is active.",
            zh_action="朝下一个检查点门冲刺",
            zh_decision="在动量衰减前选择暴露但更快的路线，还是更安全的恢复路线。",
            zh_feedback="速度线、脚步节奏和检查点颜色会显示动量是否仍在。",
        ),
        AxisLoopStep(
            action="Vault low blockers to keep the chain alive",
            player_decision="Commit to a vault timing window or slow down and route around the obstacle.",
            feedback="A clean vault extends the combo meter; a late vault costs time but keeps the run recoverable.",
            zh_action="翻越低矮障碍，保持连段不断",
            zh_decision="卡准翻越时机，还是减速绕开障碍。",
            zh_feedback="干净的翻越会延长连段 meter；过晚翻越损失时间，但这次跑图仍可救回。",
        ),
        AxisLoopStep(
            action="Wall-run across marked panels under timer pressure",
            player_decision="Spend boost for a risky wall-run shortcut or stay on the longer rooftop path.",
            feedback="Wall panels glow while valid, and the pressure timer pulses when the shortcut is missed.",
            zh_action="在计时压力下蹬墙跑过标记面板",
            zh_decision="消耗加速走高风险的蹬墙捷径，还是留在更长的屋顶路线。",
            zh_feedback="墙面在可用时发光；错过捷径时压力计会脉冲提示。",
        ),
        AxisLoopStep(
            action="Slide under hazards and exit through the final gate",
            player_decision="Preserve enough momentum for the final slide or take a checkpoint reset.",
            feedback="The finish gate reports time, broken chain count, best route, and restart affordance.",
            zh_action="滑铲穿过危险区并从终点门撤离",
            zh_decision="为最后的滑铲保留足够动量，还是回检查点重来。",
            zh_feedback="终点门会报告用时、断链次数、最佳路线和重开入口。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Momentum Chain",
            purpose="Rewards clean traversal while keeping failed routes recoverable.",
            inputs=["player velocity", "vault timing", "wall-run duration", "slide windows"],
            outputs=["combo multiplier", "boost charge", "speed feedback"],
            failure_pressure="Dropped momentum costs time and closes optional shortcuts.",
            zh_name="动量连段",
            zh_purpose="奖励干净的跑动衔接，同时保证失败的路线仍可救回。",
            zh_failure="动量中断会损失时间并关闭可选捷径。",
        ),
        AxisSystem(
            name="Checkpoint Route Timer",
            purpose="Keeps the rooftop loop short, readable, and replayable.",
            inputs=["checkpoint overlaps", "elapsed time", "missed gates"],
            outputs=["active gate", "route grade", "restart point"],
            failure_pressure="Missing too many gates forces a checkpoint reset instead of aimless wandering.",
            zh_name="检查点路线计时",
            zh_purpose="让屋顶循环短、可读、可重复挑战。",
            zh_failure="错过太多门会强制回检查点，而不是让玩家在空间里空转。",
        ),
        AxisSystem(
            name="Traversal Readability Layer",
            purpose="Makes usable ledges, walls, ramps, hazards, and exits legible at speed.",
            inputs=["surface tags", "player approach angle", "hazard proximity"],
            outputs=["affordance color", "valid-move prompts", "failure feedback"],
            failure_pressure="Unreadable surfaces slow the player and break the score chain.",
            zh_name="跑动可读性层",
            zh_purpose="让可用的边缘、墙面、坡道、危险物和出口在高速下依然清楚。",
            zh_failure="读不懂的表面会拖慢玩家并打断计分连段。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach sprint, vault, and checkpoint gates on a flat rooftop with no lethal failure.",
        midpoint_shift="Combine wall-run panels, slide barriers, and optional boost shortcuts.",
        final_minutes="Ask the player to chain sprint, vault, wall-run, slide, and extraction under one timer.",
        unlocks=[
            "Boost shortcut after the first clean checkpoint chain",
            "Wall-run route after the first vault section",
            "End-state route grade after reaching the extraction gate",
        ],
        zh_first_minute="在平坦屋顶上教学冲刺、翻越和检查点门，不设置致命失败。",
        zh_midpoint_shift="组合蹬墙面板、滑铲障碍和可选的加速捷径。",
        zh_final_minutes="要求玩家在一个计时器下串起冲刺、翻越、蹬墙、滑铲和撤离。",
        zh_unlocks=[
            "第一次干净的检查点连段后开放加速捷径",
            "第一个翻越段落后开放蹬墙路线",
            "抵达撤离门后开放结算路线评级",
        ],
    ),
    beats=[
        AxisBeat(
            name="Warmup Rooftop",
            gameplay_focus="Teach sprinting, vault timing, and checkpoint gate language.",
            required_assets=["start marker", "checkpoint gate", "low vault blockers"],
            success_condition="Player reaches the second gate without losing the route.",
            zh_name="热身屋顶",
            zh_focus="教学冲刺、翻越时机和检查点门的视觉语言。",
            zh_success="玩家在不丢失路线的前提下抵达第二道门。",
        ),
        AxisBeat(
            name="Momentum Mix",
            gameplay_focus="Chain vaults, wall-runs, slides, and one boost shortcut.",
            required_assets=[
                "wall-run panels",
                "slide barriers",
                "boost pad",
                "fall hazard markers",
            ],
            success_condition="Player keeps enough momentum to open the final rooftop line.",
            zh_name="动量混合段",
            zh_focus="串联翻越、蹬墙、滑铲和一处加速捷径。",
            zh_success="玩家保留足够动量，打开最后的屋顶线路。",
        ),
        AxisBeat(
            name="Extraction Sprint",
            gameplay_focus="Run the full chain under pressure and choose speed versus recovery.",
            required_assets=["final gap ramp", "pressure timer UI", "extraction gate"],
            success_condition="Player exits before the timer expires and receives a route grade.",
            zh_name="撤离冲刺",
            zh_focus="在压力下跑完完整连段，并在速度与安全之间取舍。",
            zh_success="玩家在计时结束前撤离，并获得路线评级。",
        ),
    ],
    assets=[
        "Modular rooftop floor kit",
        "Low vault blocker set",
        "Wall-run panel set",
        "Slide barrier set",
        "Boost pad marker",
        "Checkpoint gate",
        "Fall hazard marker set",
        "Extraction gate",
        "Route timer UI proxy",
    ],
    zh_assets=[
        "模块化屋顶地板套件",
        "低矮翻越障碍组",
        "蹬墙面板组",
        "滑铲障碍组",
        "加速板标记",
        "检查点门",
        "坠落危险标记组",
        "撤离门",
        "路线计时 UI proxy"
    ],
    narrative=AxisNarrative(
        player_fantasy="Read a rooftop at speed and turn a collapsing route into one clean line.",
        design_pillars=[
            "Momentum is the score",
            "Every surface states whether it is usable",
            "Failure costs time, never the run",
            "The route is readable before it is fast",
        ],
        win_state="Reach the extraction gate before the route timer expires with a graded line.",
        failure_states=[
            "Route timer expires before the extraction gate",
            "Too many chained failures reset the player to the last checkpoint",
            "Player leaves the rooftop boundary and loses the active route",
        ],
        notes_for_comfyui=[
            "Generate rooftop mood boards only after the greybox chain proves readable.",
            "Prioritize silhouette separation between usable ledges and background geometry.",
            "Keep hazard edges high-contrast; the player reads them at full sprint speed.",
        ],
    zh_notes_for_comfyui=[
        "屋顶气质图只在灰盒连段被证明可读之后生成。",
        "优先保证可用边缘与背景几何的轮廓分离。",
        "危险边缘必须高对比：玩家在全速下读取它。"
    ],
        zh_player_fantasy="在高速下读懂屋顶，把一条正在崩解的路线跑成一条干净的线。",
        zh_pillars=[
            "动量就是分数",
            "每个表面都要说明自己能不能用",
            "失败只损失时间，不损失整局",
            "路线先可读，再谈速度",
        ],
        zh_win_state="在路线计时结束前抵达撤离门，并取得一次有评级的完整跑图。",
        zh_failure_states=[
            "路线计时在撤离门前耗尽",
            "连续失败过多，玩家被送回上一个检查点",
            "玩家离开屋顶边界，丢失当前路线",
        ],
    ),
    enemies=[("Pursuer Drone", "chase", 2, 1)],
)


_CAREER = AxisTemplate(
    zh_label="自我路线选择",
    verbs=["discern", "choose", "compose", "support"],
    loop=[
        AxisLoopStep(
            action="Discern evaluation noise inside a memory room",
            player_decision="Keep moving toward a clear self-owned goal or follow a loud external judgment marker.",
            feedback="Fog thins around self-owned choices and thickens around borrowed evaluation routes.",
            zh_action="在记忆房间里辨认评价噪音",
            zh_decision="继续靠近自己的路线标记，还是跟随更响亮的外部评价标记。",
            zh_feedback="选择自己的路线会让迷雾变薄；跟随借来的评价会让视野变窄。",
        ),
        AxisLoopStep(
            action="Choose between borrowed plans and a personal route",
            player_decision="Take a safe-looking plan card for short-term time relief or reject it to preserve agency.",
            feedback="Plan cards show immediate comfort but reduce the self-route meter when overused.",
            zh_action="在外部 plan 和个人路线之间取舍",
            zh_decision="拿取安全感更强的 plan 卡暂缓倒计时，还是拒绝它来保留自我路线。",
            zh_feedback="plan 卡会显示短期收益，但过度使用会降低自我路线 meter。",
        ),
        AxisLoopStep(
            action="Compose experience fragments into a design board",
            player_decision="Place fragments as mechanics, constraints, or emotional beats before the interview timer ends.",
            feedback="The board converts lived moments into playable objectives, hazards, and support actions.",
            zh_action="把经历碎片编排到策划板上",
            zh_decision="在面试倒计时结束前，把碎片放为机制、约束或情绪节拍。",
            zh_feedback="策划板会把经历转化为可玩的目标、风险和补位动作。",
        ),
        AxisLoopStep(
            action="Support the team crisis and open the interview gate",
            player_decision="Spend limited focus to patch the weakest team need instead of chasing the flashiest role.",
            feedback="A final score reports clarity, fit, support timing, and which borrowed plans were rejected.",
            zh_action="补位团队危机并打开应聘门",
            zh_decision="把有限专注力用在团队最薄弱的位置，还是去追最显眼的角色。",
            zh_feedback="最终评分显示表达清晰度、岗位匹配、补位时机，以及拒绝了哪些 plan。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Evaluation Fog",
            purpose="Turns other people's judgments into readable pressure without making the space aimless.",
            inputs=["player proximity", "borrowed plan count", "self-route meter"],
            outputs=["fog density", "objective clarity", "confidence feedback"],
            failure_pressure="Following too much evaluation noise hides the personal route and forces a restart.",
            zh_name="评价迷雾",
            zh_purpose="把他人的评价变成可读压力，同时避免玩家在空间里空转。",
            zh_failure="过度跟随评价噪音会隐藏个人路线，并迫使玩家重开。",
        ),
        AxisSystem(
            name="Plan Card Tradeoff",
            purpose="Makes external advice useful but risky, so choosing a path is an actual gameplay decision.",
            inputs=["plan card type", "interview timer", "player choice history"],
            outputs=["time relief", "agency cost", "route branch"],
            failure_pressure="Stacking mismatched plans drains agency and locks the applicant out of the final board.",
            zh_name="Plan 卡取舍",
            zh_purpose="让外部建议既有用又有风险，使选路成为真正的玩法决策。",
            zh_failure="叠加不适合自己的 plan 会耗尽自我路线 meter，并锁住最终策划板。",
        ),
        AxisSystem(
            name="Design Board Translation",
            purpose="Converts personal experience fragments into mechanics, constraints, and team support actions.",
            inputs=["memory fragments", "board slots", "team crisis needs"],
            outputs=["prototype pitch score", "support action", "interview gate state"],
            failure_pressure="Fragments placed as decoration do not open the gate; they must change a playable decision.",
            zh_name="策划板转译",
            zh_purpose="把个人经历碎片转化成机制、约束和团队补位动作。",
            zh_failure="只把经历当装饰不会打开应聘门；它必须改变一个可玩的决策。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach movement, fog readability, and the first choice between a judgment marker and a self-route marker.",
        midpoint_shift="Introduce plan cards that reduce the timer but weaken agency if they do not fit the player's route.",
        final_minutes="Ask the player to assemble a design board from memory fragments and support a team crisis before the interview gate closes.",
        unlocks=[
            "Self-route meter after rejecting the first mismatched plan",
            "Design board after collecting three experience fragments",
            "Team support action after the board forms a coherent prototype pitch",
        ],
        zh_first_minute="教学移动、迷雾可读性，以及第一次在评价标记和个人路线标记之间选择。",
        zh_midpoint_shift="引入 plan 卡：它们能缓解时间压力，但不适合自己路线时会削弱自我路线 meter。",
        zh_final_minutes="要求玩家用经历碎片组装策划板，并在应聘门关闭前补位团队危机。",
        zh_unlocks=[
            "拒绝第一张不适合的 plan 后开放自我路线 meter",
            "收集三块经历碎片后开放策划板",
            "策划板形成完整提案后开放团队补位动作",
        ],
    ),
    beats=[
        AxisBeat(
            name="Fog of Evaluation",
            gameplay_focus="Teach the player to read judgment noise, self-route markers, and recoverable wrong turns.",
            required_assets=[
                "fog corridor",
                "judgment marker",
                "self-route marker",
                "confidence UI",
            ],
            success_condition="Player reaches the first clear route marker without losing all confidence.",
            zh_name="评价迷雾",
            zh_focus="教学玩家阅读评价噪音、个人路线标记，以及可恢复的错误转向。",
            zh_success="玩家在信心耗尽前抵达第一个清晰的路线标记。",
        ),
        AxisBeat(
            name="Borrowed Plan Crossroads",
            gameplay_focus="Choose, reject, or revise plan cards while collecting experience fragments for the design board.",
            required_assets=[
                "plan card kiosks",
                "memory fragment props",
                "design board",
                "timer UI",
            ],
            success_condition="Player fills the board with fragments that change mechanics instead of decoration.",
            zh_name="借来的 Plan 十字路口",
            zh_focus="选择、拒绝或改写 plan 卡，同时收集经历碎片放入策划板。",
            zh_success="玩家把碎片放成会改变机制的内容，而不是装饰文字。",
        ),
        AxisBeat(
            name="Interview Gate Triage",
            gameplay_focus="Use the completed design board to support the team need that matters most under time pressure.",
            required_assets=[
                "team crisis stations",
                "support action prompt",
                "interview gate",
                "fit score UI",
            ],
            success_condition="Player resolves one critical team need and opens the interview gate with a readable score.",
            zh_name="应聘门前补位",
            zh_focus="用完成的策划板，在时间压力下支持团队最需要的位置。",
            zh_success="玩家解决一个关键团队需求，并用可读评分打开应聘门。",
        ),
    ],
    assets=[
        "Fog corridor greybox kit",
        "Judgment marker set",
        "Self-route marker set",
        "Borrowed plan card kiosk",
        "Memory fragment pickup set",
        "Design board UI proxy",
        "Team crisis station set",
        "Interview gate",
        "Fit score UI proxy",
    ],
    zh_assets=[
        "迷雾走廊灰盒套件",
        "评价标记组",
        "个人路线标记组",
        "外部 plan 卡台",
        "经历碎片拾取物组",
        "策划板 UI proxy",
        "团队危机站点组",
        "应聘门",
        "匹配评分 UI proxy"
    ],
    narrative=AxisNarrative(
        player_fantasy="Prove value as a game design applicant by transforming personal experience into clear mechanics and supporting a team at the right moment.",
        design_pillars=[
            "Personal history becomes playable decisions",
            "Borrowed plans help only when they fit the player's route",
            "Failure clarifies the next self-owned choice",
            "Support actions matter more than flashy power",
        ],
        win_state="Open the interview gate by building a coherent design board and resolving one critical team need.",
        failure_states=[
            "Evaluation fog hides the self-route after too many mismatched plans",
            "Interview timer expires before the design board becomes actionable",
            "Team crisis is ignored in favor of decorative or unfocused choices",
        ],
        notes_for_comfyui=[
            "Generate original visual metaphors for fog, plan cards, design boards, and interview gates; do not copy named game IP.",
            "Prioritize icon-like readability for judgment noise, self-route markers, and support prompts.",
            "Use references as portfolio mood boards only after the greybox loop proves readable.",
        ],
    zh_notes_for_comfyui=[
        "为迷雾、plan 卡、策划板和应聘门生成原创视觉隐喻，不复刻被引用游戏 IP。",
        "优先保证评价噪音、个人路线标记和补位提示像图标一样清楚。",
        "视觉参考只服务作品集气质；灰盒循环可读后再进入风格化。"
    ],
        zh_player_fantasy="作为游戏策划应聘者，把个人经历转化成清晰机制，并在团队关键时刻发挥价值。",
        zh_pillars=[
            "个人经历必须变成可玩的决策",
            "外部 plan 只有适合自己路线时才有帮助",
            "失败要澄清下一次自我选择",
            "补位价值比耀眼数值更重要",
        ],
        zh_win_state="完成一块逻辑清楚的策划板，解决一次关键团队需求，并打开应聘门。",
        zh_failure_states=[
            "不合适的 plan 过多，评价迷雾遮住个人路线",
            "面试倒计时结束时策划板仍不可执行",
            "只做装饰表达，忽略团队真正需要的补位",
        ],
    ),
)


_STEALTH = AxisTemplate(
    zh_label="潜行",
    verbs=["scout", "hide", "distract", "extract"],
    loop=[
        AxisLoopStep(
            action="Scout the patrol pattern from a safe pocket",
            player_decision="Watch one more cycle for a wider window or move now on a tighter one.",
            feedback="Vision cones, patrol ribbons, and light meters show what is currently observable.",
            zh_action="在安全角落侦察巡逻规律",
            zh_decision="再多观察一轮换取更宽的窗口，还是趁窄窗口立刻行动。",
            zh_feedback="视线锥、巡逻轨迹带和光照 meter 会显示此刻什么会被看见。",
        ),
        AxisLoopStep(
            action="Move between shadow pockets and cover",
            player_decision="Take the short lit route or the longer shadow route before the patrol turns.",
            feedback="Exposure meter rises in lit ground and falls in shadow; audio sting marks near-misses.",
            zh_action="在暗影区和掩体之间转移",
            zh_decision="在巡逻转身前，走近而明亮的路线，还是长而黑暗的路线。",
            zh_feedback="暴露 meter 在亮处上升、在暗处下降；擦身而过时会有音效提示。",
        ),
        AxisLoopStep(
            action="Distract a guard to open the objective path",
            player_decision="Spend a limited noisemaker to pull a guard off post, or wait for the route to clear itself.",
            feedback="Guards show a visible search state, so the player can read exactly what the distraction bought.",
            zh_action="制造干扰，打开通往目标的路径",
            zh_decision="消耗一个有限的噪音道具把守卫调离岗位，还是等路线自己清空。",
            zh_feedback="守卫会显示可见的搜索状态，玩家能清楚读出这次干扰换来了什么。",
        ),
        AxisLoopStep(
            action="Extract with the objective before the alert escalates",
            player_decision="Leave with partial progress at low alert or push deeper for the full objective.",
            feedback="Extraction report shows alert peak, unseen time, noise used, and restart affordance.",
            zh_action="在警戒升级前带着目标撤离",
            zh_decision="在低警戒下带着部分成果撤离，还是深入拿完整目标。",
            zh_feedback="撤离报告显示警戒峰值、未被发现时长、道具消耗和重开入口。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Sight And Sound Exposure",
            purpose="Turns visibility and noise into one readable meter so stealth decisions are legible.",
            inputs=["player proximity", "alert level", "line traces", "player noise"],
            outputs=["exposure meter", "detection state", "shadow feedback"],
            failure_pressure="Exposure above the threshold triggers a search, not an instant loss, so a mistake stays recoverable.",
            zh_name="视听暴露度",
            zh_purpose="把可见度和噪音合成一个可读 meter，让潜行决策清楚可判断。",
            zh_failure="暴露度超过阈值会触发搜索而不是立刻失败，所以失误仍可救回。",
        ),
        AxisSystem(
            name="Patrol And Search Escalation",
            purpose="Makes guards predictable enough to plan against but reactive enough to punish carelessness.",
            inputs=["patrol waypoints", "alert level", "last known position"],
            outputs=["patrol route", "search behaviour", "alert decay"],
            failure_pressure="Ignoring patrol rhythm escalates the alert until the objective becomes unreachable.",
            zh_name="巡逻与搜索升级",
            zh_purpose="让守卫既有规律可供计划，又有反应足以惩罚大意。",
            zh_failure="无视巡逻节奏会让警戒持续升级，直到目标变得不可达。",
        ),
        AxisSystem(
            name="Distraction Economy",
            purpose="Forces the player to spend a scarce tool instead of waiting out every patrol.",
            inputs=["noisemaker count", "player proximity", "objective distance"],
            outputs=["guard displacement", "route opening", "resource cost"],
            failure_pressure="Wasting noisemakers leaves the final room with no way to split a pair of guards.",
            zh_name="干扰道具经济",
            zh_purpose="迫使玩家消耗稀缺工具，而不是把每个巡逻都干等过去。",
            zh_failure="浪费干扰道具会让最终房间无法分开成对守卫。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach vision cones, shadow pockets, and one slow patrol with no alert escalation.",
        midpoint_shift="Overlap two patrols and add a locked door that needs a distraction to pass.",
        final_minutes="Ask the player to cross a lit hall, take the objective, and extract under a rising alert.",
        unlocks=[
            "Second noisemaker after the first successful distraction",
            "Faster crouch-walk after clearing the first patrol untouched",
            "Extraction shortcut after recovering from one full alert",
        ],
        zh_first_minute="教学视线锥、暗影区和一条不会升级警戒的慢速巡逻。",
        zh_midpoint_shift="叠加两条巡逻，并加入一扇必须用干扰才能通过的锁门。",
        zh_final_minutes="要求玩家穿过明亮的中庭、取得目标，并在持续升级的警戒下撤离。",
        zh_unlocks=[
            "第一次成功干扰后开放第二个噪音道具",
            "第一次无触碰通过巡逻后开放更快的蹲行",
            "从一次完整警戒中恢复后开放撤离捷径",
        ],
    ),
    beats=[
        AxisBeat(
            name="Outer Ward",
            gameplay_focus="Teach vision cones, shadow pockets, and reading a single patrol cycle.",
            required_assets=[
                "shadow volume marker",
                "vision cone marker",
                "patrol path ribbon",
                "cover block set",
            ],
            success_condition="Player crosses the ward without raising the alert above calm.",
            zh_name="外围病区",
            zh_focus="教学视线锥、暗影区，以及如何读懂一轮巡逻周期。",
            zh_success="玩家在警戒未超过平静等级的情况下穿过病区。",
        ),
        AxisBeat(
            name="Patrol Crossing",
            gameplay_focus="Time two overlapping patrols and spend the first noisemaker on a locked side door.",
            required_assets=[
                "locked side door",
                "noisemaker pickup",
                "overlapping patrol markers",
                "alert level UI",
            ],
            success_condition="Player opens the side door and reaches the hall with at least one noisemaker left.",
            zh_name="巡逻交汇口",
            zh_focus="为两条交叠巡逻计时，并把第一个噪音道具用在锁住的侧门上。",
            zh_success="玩家打开侧门进入中庭，且至少保留一个噪音道具。",
        ),
        AxisBeat(
            name="Vault Extraction",
            gameplay_focus="Take the objective from a lit hall and leave before the alert locks the exit down.",
            required_assets=[
                "objective vault prop",
                "lit hall floor marker",
                "extraction vent",
                "alert countdown UI",
            ],
            success_condition="Player exits with the objective while the alert is still decaying.",
            zh_name="密库撤离",
            zh_focus="从明亮的中庭取走目标，并在警戒封锁出口前离开。",
            zh_success="玩家在警戒仍在衰减时带着目标撤离。",
        ),
    ],
    assets=[
        "Greybox ward corridor kit",
        "Cover block set",
        "Vision cone marker set",
        "Patrol path ribbon",
        "Shadow volume marker set",
        "Noisemaker pickup",
        "Locked door prop",
        "Objective vault prop",
        "Alert level UI proxy",
    ],
    zh_assets=[
        "灰盒病区走廊套件",
        "掩体方块组",
        "视线锥标记组",
        "巡逻路径带",
        "暗影体积标记组",
        "噪音道具拾取物",
        "上锁的门道具",
        "目标密库道具",
        "警戒等级 UI proxy"
    ],
    narrative=AxisNarrative(
        player_fantasy="Read a hostile room well enough to walk through it untouched.",
        design_pillars=[
            "Observation is the primary verb",
            "Every patrol states its own timing",
            "Detection is a setback, not a game over",
            "Light and shadow are gameplay, not decoration",
        ],
        win_state="Take the objective and extract while the alert level is still decaying.",
        failure_states=[
            "Alert level reaches the lockdown threshold before extraction",
            "Objective room becomes unreachable after repeated detections",
            "Player spends every noisemaker and cannot open the final route",
        ],
        notes_for_comfyui=[
            "Generate lighting studies for shadow pockets and lit-hall contrast, not character art.",
            "Prioritize vision cone readability over atmospheric detail.",
            "Treat images as lighting references reviewed after the greybox proves observable.",
        ],
    zh_notes_for_comfyui=[
        "生成暗影区与明亮中庭的对比光照研究，而不是角色美术。",
        "优先保证视线锥的可读性，而不是氛围细节。",
        "图像只作为光照参考，且要在灰盒被证明可观察之后再评审。"
    ],
        zh_player_fantasy="把一个敌意空间读到足以毫发无伤地穿过去。",
        zh_pillars=[
            "观察是首要动词",
            "每条巡逻都要说明自己的节奏",
            "被发现是挫折，不是结束",
            "光与影是玩法，不是装饰",
        ],
        zh_win_state="在警戒等级仍在衰减时取得目标并撤离。",
        zh_failure_states=[
            "警戒在撤离前达到封锁阈值",
            "反复被发现后目标房间变得不可达",
            "玩家耗尽干扰道具，无法打开最后一段路线",
        ],
    ),
    enemies=[("Patrol Guard", "patrol", 3, 3), ("Watch Sentry", "stationary", 2, 2)],
)


_COMBAT = AxisTemplate(
    zh_label="战斗",
    verbs=["position", "attack", "evade", "recover"],
    loop=[
        AxisLoopStep(
            action="Read the enemy tell and take a position",
            player_decision="Fight in the open where damage is high or behind cover where windows are short.",
            feedback="Enemy wind-up color and ground markers show what the next attack will cover.",
            zh_action="读懂敌人预兆并占位",
            zh_decision="在开阔处打出高伤害，还是在掩体后打短窗口。",
            zh_feedback="敌人的起手颜色和地面标记会显示下一击覆盖的范围。",
        ),
        AxisLoopStep(
            action="Attack during the exposed window",
            player_decision="Spend stamina for a full combo or hold back and keep enough to evade.",
            feedback="Hit markers, posture damage, and a stamina bar show how much of the window was converted.",
            zh_action="在暴露窗口内进攻",
            zh_decision="消耗体力打满一套连招，还是留够体力用来闪避。",
            zh_feedback="命中标记、架势伤害和体力条会显示窗口被转化了多少。",
        ),
        AxisLoopStep(
            action="Evade the counter-attack",
            player_decision="Dodge late for a bigger punish window or disengage early and reset spacing.",
            feedback="A late dodge slows time briefly; a missed dodge costs health but leaves the fight recoverable.",
            zh_action="闪避反击",
            zh_decision="晚闪换取更大的惩罚窗口，还是早退重置距离。",
            zh_feedback="成功的晚闪会短暂减速；失手会掉血，但战斗仍可继续。",
        ),
        AxisLoopStep(
            action="Recover posture and reposition",
            player_decision="Create distance to regen stamina or stay close and pressure the stagger meter.",
            feedback="Stagger meter and enemy recovery state tell the player when the opening is real.",
            zh_action="恢复架势并重新占位",
            zh_decision="拉开距离回复体力，还是贴身继续压架势 meter。",
            zh_feedback="架势 meter 和敌人的恢复状态会告诉玩家破绽是不是真的。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Tell And Punish Window",
            purpose="Makes every attack readable so the fight is a timing problem, not a memorisation test.",
            inputs=["enemy attack state", "player proximity", "dodge timing"],
            outputs=["wind-up telegraph", "punish window", "stagger damage"],
            failure_pressure="Attacking outside the window deals reduced damage and leaves the player exposed.",
            zh_name="预兆与惩罚窗口",
            zh_purpose="让每一次攻击都可读，使战斗成为时机问题而不是背板问题。",
            zh_failure="在窗口外进攻伤害衰减，并让玩家处于暴露状态。",
        ),
        AxisSystem(
            name="Stamina Economy",
            purpose="Turns greed into a cost, so every combo is a decision about what to save.",
            inputs=["stamina pool", "attack cost", "elapsed time"],
            outputs=["available actions", "exhausted state", "recovery rate"],
            failure_pressure="Emptying stamina leaves no dodge available and turns the next tell into guaranteed damage.",
            zh_name="体力经济",
            zh_purpose="让贪刀付出代价，使每一次连招都是关于留多少的取舍。",
            zh_failure="体力清空后没有闪避可用，下一个预兆必然变成实打实的伤害。",
        ),
        AxisSystem(
            name="Stagger And Spacing",
            purpose="Gives the player a second way to win besides raw damage output.",
            inputs=["posture damage", "hit streak", "player proximity"],
            outputs=["stagger meter", "opening state", "arena control"],
            failure_pressure="Ignoring spacing lets enemies reset and drains the stagger meter before it breaks.",
            zh_name="架势与距离",
            zh_purpose="给玩家除纯伤害之外的第二条取胜路径。",
            zh_failure="忽视距离会让敌人重置状态，并在破防前把架势 meter 清空。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach one slow enemy with a long tell and no punishment for a mistimed dodge.",
        midpoint_shift="Add a second attacker with a faster tell so the player must choose who to face.",
        final_minutes="Force a stagger break on a heavier enemy while managing stamina and two spacing threats.",
        unlocks=[
            "Punish combo after the first clean late dodge",
            "Second weapon stance after the first stagger break",
            "Arena control score after clearing the final encounter",
        ],
        zh_first_minute="教学一个起手很慢、闪避失手也不惩罚的敌人。",
        zh_midpoint_shift="加入第二个起手更快的敌人，迫使玩家决定先打谁。",
        zh_final_minutes="要求在管理体力和两处距离威胁的同时，对更重的敌人打出一次破防。",
        zh_unlocks=[
            "第一次干净的晚闪后开放惩罚连招",
            "第一次破防后开放第二套武器架势",
            "通关最终遭遇战后开放场地控制评分",
        ],
    ),
    beats=[
        AxisBeat(
            name="Sparring Yard",
            gameplay_focus="Teach the tell, the dodge timing, and the basic punish window on one slow enemy.",
            required_assets=[
                "arena floor marker",
                "training dummy prop",
                "tell telegraph marker",
                "stamina UI",
            ],
            success_condition="Player lands three punish windows without dropping below half health.",
            zh_name="练武场",
            zh_focus="在一个慢速敌人身上教学预兆、闪避时机和基础惩罚窗口。",
            zh_success="玩家打出三次惩罚窗口，且血量未低于一半。",
        ),
        AxisBeat(
            name="Pressure Wave",
            gameplay_focus="Fight two attackers with different tells and decide which one to stagger first.",
            required_assets=[
                "cover pillar set",
                "second spawn marker",
                "stagger meter UI",
                "hazard edge marker",
            ],
            success_condition="Player breaks one enemy's stagger while keeping the other outside punish range.",
            zh_name="压迫波次",
            zh_focus="面对两个起手不同的敌人，并决定先破谁的架势。",
            zh_success="玩家破掉一个敌人的架势，同时把另一个挡在惩罚范围外。",
        ),
        AxisBeat(
            name="Boss Reckoning",
            gameplay_focus="Convert stamina and spacing discipline into a stagger break on the heaviest enemy.",
            required_assets=[
                "boss arena marker",
                "stagger break trigger",
                "recovery pickup",
                "victory gate",
            ],
            success_condition="Player lands the stagger break and opens the victory gate.",
            zh_name="首领清算",
            zh_focus="把体力和距离的纪律转化为对最重敌人的一次破防。",
            zh_success="玩家打出破防并打开胜利之门。",
        ),
    ],
    assets=[
        "Greybox arena kit",
        "Cover pillar set",
        "Training dummy prop",
        "Tell telegraph marker",
        "Stamina and stagger UI proxy",
        "Second spawn marker",
        "Recovery pickup",
        "Boss arena marker",
        "Victory gate",
    ],
    zh_assets=[
        "灰盒竞技场套件",
        "掩体柱组",
        "训练假人道具",
        "预兆提示标记",
        "体力与架势 UI proxy",
        "第二刷怪标记",
        "恢复拾取物",
        "首领场地标记",
        "胜利之门"
    ],
    narrative=AxisNarrative(
        player_fantasy="Win by reading the fight instead of out-damaging it.",
        design_pillars=[
            "Every attack is telegraphed before it lands",
            "Greed has a visible cost",
            "Positioning is a damage source",
            "Loss teaches the next opening",
        ],
        win_state="Break the heaviest enemy's stagger and open the victory gate.",
        failure_states=[
            "Player health reaches zero before the stagger break",
            "Stamina exhaustion leaves no answer to the boss tell",
            "Both attackers reach punish range and the arena becomes unrecoverable",
        ],
        notes_for_comfyui=[
            "Generate silhouette studies for enemy tells, not polished character renders.",
            "Prioritize wind-up pose clarity from the player camera angle.",
            "Use references only after the greybox encounter proves the punish window readable.",
        ],
    zh_notes_for_comfyui=[
        "生成敌人预兆的剪影研究，而不是精细的角色渲染。",
        "优先保证起手姿势在玩家镜头角度下清楚。",
        "只在灰盒遭遇战被证明可读之后使用参考图。"
    ],
        zh_player_fantasy="靠读懂战斗取胜，而不是靠数值压过去。",
        zh_pillars=[
            "每次攻击在命中前都要有预兆",
            "贪刀要付出可见代价",
            "站位本身就是伤害来源",
            "失败要教会玩家下一个破绽",
        ],
        zh_win_state="打破最重敌人的架势并打开胜利之门。",
        zh_failure_states=[
            "破防前玩家血量归零",
            "体力耗尽，无法应对首领的预兆",
            "两个敌人同时进入惩罚距离，场地无法挽回",
        ],
    ),
    enemies=[("Charger", "chase", 4, 3), ("Turret", "ranged", 3, 1)],
)


_SURVIVAL = AxisTemplate(
    zh_label="生存",
    verbs=["gather", "craft", "route", "endure"],
    loop=[
        AxisLoopStep(
            action="Gather from the nearest reachable node",
            player_decision="Take the rich node deeper in the hazard zone or the poor one close to shelter.",
            feedback="Resource counts, carry weight, and a depletion marker show what the node still holds.",
            zh_action="从最近可及的资源点采集",
            zh_decision="去危险区深处的高产点，还是庇护所附近的低产点。",
            zh_feedback="资源计数、负重和枯竭标记会显示这个点还剩多少。",
        ),
        AxisLoopStep(
            action="Craft what the next window needs",
            player_decision="Spend now on warmth for the coming spike or save for a tool that opens a new route.",
            feedback="Crafting shows exactly which threshold the item moves, so the trade is never opaque.",
            zh_action="制作下一段时间窗口需要的东西",
            zh_decision="现在花掉资源换取御寒，还是存起来做能开新路的工具。",
            zh_feedback="制作界面会显示这件道具究竟推动了哪个阈值，取舍不会是黑箱。",
        ),
        AxisLoopStep(
            action="Route between shelter and objective under drain",
            player_decision="Push to the objective on the current meter or detour to shelter and lose the window.",
            feedback="Drain meter, weather state, and distance-to-shelter readout make the detour cost explicit.",
            zh_action="在持续消耗中往返于庇护所和目标之间",
            zh_decision="带着当前的资源条冲向目标，还是绕回庇护所并放弃这个窗口。",
            zh_feedback="消耗 meter、天气状态和到庇护所的距离读数会让绕路代价一目了然。",
        ),
        AxisLoopStep(
            action="Endure the spike and bank progress",
            player_decision="Ride out the storm in place or sprint for the next shelter while the drain is high.",
            feedback="Survival report shows peak drain, crafted items, distance covered, and restart affordance.",
            zh_action="扛过消耗高峰并结算进度",
            zh_decision="就地硬扛过风暴，还是在消耗很高时冲向下一个庇护所。",
            zh_feedback="生存报告显示消耗峰值、制作件数、行进距离和重开入口。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Drain Clock",
            purpose="Makes time itself the pressure, so standing still is never free.",
            inputs=["elapsed time", "weather state", "player proximity", "shelter stock"],
            outputs=["drain rate", "threshold warning", "shelter value"],
            failure_pressure="A drain meter reaching zero forces a shelter reset instead of an instant loss.",
            zh_name="消耗时钟",
            zh_purpose="让时间本身成为压力，站着不动永远有代价。",
            zh_failure="消耗 meter 归零会触发庇护所重置，而不是立刻失败。",
        ),
        AxisSystem(
            name="Gather And Carry Tradeoff",
            purpose="Turns inventory into a routing decision rather than a number to maximise.",
            inputs=["node richness", "carry capacity", "hazard proximity"],
            outputs=["resource gain", "movement penalty", "depletion state"],
            failure_pressure="Over-encumbered players cannot outrun the next pressure spike.",
            zh_name="采集与负重取舍",
            zh_purpose="让背包成为路线决策，而不是一个要堆满的数字。",
            zh_failure="负重过高的玩家跑不过下一次消耗高峰。",
        ),
        AxisSystem(
            name="Craft Threshold",
            purpose="Keeps crafting tied to specific upcoming thresholds instead of general power.",
            inputs=["resource stock", "forecast window", "player proximity"],
            outputs=["threshold buffer", "route unlock", "stock cost"],
            failure_pressure="Crafting the wrong item leaves the coming spike unanswered and the run stalls.",
            zh_name="制作阈值",
            zh_purpose="让制作始终服务于具体的阈值，而不是笼统地变强。",
            zh_failure="做错东西会让即将到来的消耗高峰无人应对，整局停滞。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach gathering, one craft recipe, and a shelter that is always visible.",
        midpoint_shift="Introduce a forecast spike that punishes players who spent everything on the first route.",
        final_minutes="Ask the player to cross the hazard zone, bank the objective, and reach shelter during the worst spike.",
        unlocks=[
            "Second recipe after the first successful craft",
            "Deep hazard route after surviving one full spike",
            "End-state survival grade after banking the objective in shelter",
        ],
        zh_first_minute="教学采集、一个制作配方，以及一个始终可见的庇护所。",
        zh_midpoint_shift="引入一次预报中的消耗高峰，惩罚把资源全花在第一段路线的玩家。",
        zh_final_minutes="要求玩家穿越危险区、存入目标，并在最凶的高峰中抵达庇护所。",
        zh_unlocks=[
            "第一次成功制作后开放第二个配方",
            "扛过一次完整高峰后开放深入危险区的路线",
            "在庇护所存入目标后开放结算生存评级",
        ],
    ),
    beats=[
        AxisBeat(
            name="Shelter Basin",
            gameplay_focus="Teach gathering, the first recipe, and reading the drain meter safely.",
            required_assets=[
                "resource node set",
                "shelter marker",
                "crafting bench prop",
                "drain meter UI",
            ],
            success_condition="Player crafts one item and returns to shelter with the drain above half.",
            zh_name="庇护所盆地",
            zh_focus="安全地教学采集、第一个配方，以及如何读懂消耗 meter。",
            zh_success="玩家做出一件道具，并在消耗条高于一半时回到庇护所。",
        ),
        AxisBeat(
            name="Forecast Spike",
            gameplay_focus="Spend stock on the right threshold before the announced spike arrives.",
            required_assets=[
                "forecast board prop",
                "hazard zone marker",
                "warmth pickup",
                "weather state UI",
            ],
            success_condition="Player survives the spike outside shelter with at least one resource left.",
            zh_name="预报高峰",
            zh_focus="在预报的高峰到来前，把库存花在正确的阈值上。",
            zh_success="玩家在庇护所外扛过高峰，且至少保留一种资源。",
        ),
        AxisBeat(
            name="Cache Run",
            gameplay_focus="Cross the hazard zone, bank the objective, and reach shelter during the worst drain.",
            required_assets=[
                "objective cache prop",
                "hazard floor marker",
                "shelter door trigger",
                "survival grade UI",
            ],
            success_condition="Player banks the objective and reaches shelter before the drain meter empties.",
            zh_name="补给冲刺",
            zh_focus="穿越危险区、存入目标，并在消耗最凶时抵达庇护所。",
            zh_success="玩家在消耗 meter 清空前存入目标并抵达庇护所。",
        ),
    ],
    assets=[
        "Greybox terrain kit",
        "Resource node set",
        "Crafting bench prop",
        "Shelter marker",
        "Forecast board prop",
        "Hazard zone marker",
        "Warmth pickup",
        "Objective cache prop",
        "Drain meter UI proxy",
    ],
    zh_assets=[
        "灰盒地形套件",
        "资源点组",
        "制作台道具",
        "庇护所标记",
        "预报板道具",
        "危险区标记",
        "御寒拾取物",
        "目标补给道具",
        "消耗 meter UI proxy"
    ],
    narrative=AxisNarrative(
        player_fantasy="Turn scarcity into a plan instead of a panic.",
        design_pillars=[
            "Standing still is a decision with a cost",
            "Every craft answers a named threshold",
            "Failure teaches a better route, not a restart",
            "The forecast is readable before it is lethal",
        ],
        win_state="Bank the objective in shelter before the final drain spike empties the meter.",
        failure_states=[
            "Drain meter empties outside shelter during the final spike",
            "Player carries no resource that answers the coming threshold",
            "Objective cache is left behind and the shelter door stays locked",
        ],
        notes_for_comfyui=[
            "Generate weather and lighting studies for hazard readability, not survival kit renders.",
            "Prioritize the contrast between safe ground and drain ground.",
            "Use references only after the greybox route proves the forecast readable.",
        ],
    zh_notes_for_comfyui=[
        "生成天气与光照研究以服务危险区可读性，而不是求生装备渲染。",
        "优先保证安全地面与消耗地面的对比。",
        "只在灰盒路线被证明可读之后使用参考图。"
    ],
        zh_player_fantasy="把稀缺变成计划，而不是变成慌乱。",
        zh_pillars=[
            "站着不动也是一种有代价的决策",
            "每件制作物都回应一个具体阈值",
            "失败教的是更好的路线，不是重开",
            "预报先可读，再谈致命",
        ],
        zh_win_state="在最后的消耗高峰清空 meter 前，把目标存入庇护所。",
        zh_failure_states=[
            "消耗 meter 在庇护所外被最后的高峰清空",
            "玩家没有携带能应对下一阈值的资源",
            "目标补给被落下，庇护所门保持锁定",
        ],
    ),
    enemies=[("Stalker", "chase", 3, 2)],
)


_PUZZLE = AxisTemplate(
    zh_label="解谜",
    verbs=["observe", "combine", "trigger", "solve"],
    loop=[
        AxisLoopStep(
            action="Observe the room and name its rule",
            player_decision="Test the obvious rule first or spend time reading for a second constraint.",
            feedback="Interactable surfaces highlight their state so a wrong hypothesis is visibly wrong.",
            zh_action="观察房间并说出它的规则",
            zh_decision="先试最显然的规则，还是花时间读出第二条约束。",
            zh_feedback="可交互表面会高亮自己的状态，错误的假设会明显地错。",
        ),
        AxisLoopStep(
            action="Combine two elements into a new state",
            player_decision="Commit the current element to a slot or hold it for a later combination.",
            feedback="Combination results are shown immediately, so the player never waits to learn.",
            zh_action="把两个元素组合成新状态",
            zh_decision="把当前元素放进槽位，还是留着等后面组合。",
            zh_feedback="组合结果立刻呈现，玩家从不需要等待才知道对错。",
        ),
        AxisLoopStep(
            action="Trigger the mechanism and read the consequence",
            player_decision="Pull the trigger now or re-check the route it opens before committing.",
            feedback="Triggered changes animate to their source, showing which rule produced them.",
            zh_action="触发机关并读出后果",
            zh_decision="现在就拉下开关，还是先确认它打开的路线再决定。",
            zh_feedback="被触发的变化会回溯动画到源头，显示是哪条规则造成的。",
        ),
        AxisLoopStep(
            action="Solve the room and bank the exit",
            player_decision="Leave through the solved exit or spend remaining time on the optional room.",
            feedback="Solve report shows attempts, rule hints used, optional rooms cleared, and restart affordance.",
            zh_action="解开房间并结算出口",
            zh_decision="从已解开的出口离开，还是用剩余时间挑战可选房间。",
            zh_feedback="结算报告显示尝试次数、用过的提示、可选房完成数和重开入口。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Rule Discovery",
            purpose="Makes the rule learnable from the room instead of explained by a tutorial.",
            inputs=["interaction events", "element state", "player proximity"],
            outputs=["state feedback", "rule hint", "valid combination"],
            failure_pressure="A wrong hypothesis only wastes an attempt; it never hides the rule permanently.",
            zh_name="规则发现",
            zh_purpose="让规则从房间里被学会，而不是靠教程讲解。",
            zh_failure="错误的假设只会浪费一次尝试，永远不会永久隐藏规则。",
        ),
        AxisSystem(
            name="Element Combination",
            purpose="Turns inventory into a reasoning problem rather than a fetch list.",
            inputs=["element stock", "slot state", "line traces"],
            outputs=["combined state", "route opening", "consumed element"],
            failure_pressure="Consuming the wrong element locks a slot until the room is reset.",
            zh_name="元素组合",
            zh_purpose="让背包成为推理问题，而不是一张采集清单。",
            zh_failure="用错元素会锁住槽位，直到房间被重置。",
        ),
        AxisSystem(
            name="Hint Ladder",
            purpose="Keeps the player moving without handing over the answer.",
            inputs=["attempt count", "elapsed time", "hint budget"],
            outputs=["nudged affordance", "partial rule", "solve confidence"],
            failure_pressure="Running out of hints converts the room into a reset instead of a failure.",
            zh_name="提示阶梯",
            zh_purpose="让玩家持续前进，而不是直接把答案交出去。",
            zh_failure="提示用尽会把房间变成一次重置，而不是一次失败。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach one rule in a single room with no way to get stuck.",
        midpoint_shift="Require combining two rules learned in separate rooms to open the central door.",
        final_minutes="Ask the player to solve a chained room under a soft timer, with one optional room in reach.",
        unlocks=[
            "Second element type after the first combination",
            "Central door after both side rooms are solved",
            "End-state solve grade after exiting through the final chain",
        ],
        zh_first_minute="在一个房间里教学一条规则，且不留卡死的可能。",
        zh_midpoint_shift="要求组合两个分别学到的规则，才能打开中央门。",
        zh_final_minutes="要求玩家在一个软计时下解开串联房间，且有一间可选房触手可及。",
        zh_unlocks=[
            "第一次组合后开放第二种元素",
            "两侧房间都解开后开放中央门",
            "从最终串联房离开后开放结算解谜评级",
        ],
    ),
    beats=[
        AxisBeat(
            name="Teaching Chamber",
            gameplay_focus="Teach observation, one rule, and the fact that no attempt can waste the run.",
            required_assets=[
                "rule plate prop",
                "single slot pedestal",
                "state highlight marker",
                "attempt counter UI",
            ],
            success_condition="Player solves the chamber without spending a hint.",
            zh_name="教学密室",
            zh_focus="教学观察、一条规则，以及「任何尝试都不会浪费整局」这件事。",
            zh_success="玩家在不消耗提示的情况下解开密室。",
        ),
        AxisBeat(
            name="Twin Rule Hall",
            gameplay_focus="Carry one rule from each side room and combine them on the central pedestal.",
            required_assets=[
                "two side room doors",
                "central pedestal",
                "element pickup set",
                "combination feedback prop",
            ],
            success_condition="Player opens the central door by combining both learned rules.",
            zh_name="双规则大厅",
            zh_focus="从两侧房间各带出一条规则，并在中央基座上组合它们。",
            zh_success="玩家组合两条学到的规则，打开中央门。",
        ),
        AxisBeat(
            name="Chain Room",
            gameplay_focus="Solve a three-step chain under a soft timer, with one optional room in reach.",
            required_assets=[
                "chained trigger set",
                "optional room door",
                "soft timer UI",
                "solve grade trigger",
            ],
            success_condition="Player completes the chain and exits before the soft timer expires.",
            zh_name="串联房间",
            zh_focus="在软计时下解开三步串联，且有一间可选房触手可及。",
            zh_success="玩家在软计时结束前完成串联并离开。",
        ),
    ],
    assets=[
        "Greybox chamber kit",
        "Rule plate prop",
        "Slot pedestal set",
        "Element pickup set",
        "Chained trigger set",
        "Central door prop",
        "Optional room door",
        "Soft timer UI proxy",
        "Solve grade trigger",
    ],
    zh_assets=[
        "灰盒密室套件",
        "规则铭牌道具",
        "槽位基座组",
        "元素拾取物组",
        "串联触发器组",
        "中央门道具",
        "可选房门",
        "软计时 UI proxy",
        "解谜评级触发器"
    ],
    narrative=AxisNarrative(
        player_fantasy="Understand a room well enough that the solution feels earned.",
        design_pillars=[
            "The room teaches its own rule",
            "Every attempt gives information",
            "A wrong idea costs a try, not the run",
            "Hints point, they never solve",
        ],
        win_state="Complete the final chain and exit through the solved door before the soft timer expires.",
        failure_states=[
            "Soft timer expires before the final chain is complete",
            "Every element is consumed and a locked slot cannot be reset",
            "Optional room is opened at the cost of the required chain",
        ],
        notes_for_comfyui=[
            "Generate readability studies for state contrast, not ornate puzzle props.",
            "Prioritize the visual difference between solved and unsolved surfaces.",
            "Use references only after the greybox proves each rule learnable from the room.",
        ],
    zh_notes_for_comfyui=[
        "生成状态对比的可读性研究，而不是华丽的谜题道具。",
        "优先保证已解与未解表面的视觉差异。",
        "只在灰盒证明每条规则都能从房间里学会之后使用参考图。"
    ],
        zh_player_fantasy="把一个房间理解到让解法显得是自己挣来的。",
        zh_pillars=[
            "房间自己教会自己的规则",
            "每次尝试都提供信息",
            "错误的想法只花一次尝试，不花整局",
            "提示只指方向，从不代解",
        ],
        zh_win_state="在软计时结束前完成最终串联，并从解开的门离开。",
        zh_failure_states=[
            "软计时在完成最终串联前耗尽",
            "元素全部耗尽，且锁住的槽位无法重置",
            "为了开可选房而牺牲了必需的串联",
        ],
    ),
)


_MOBILITY = AxisTemplate(
    zh_label="竞速",
    verbs=["dash", "steer", "boost", "risk"],
    loop=[
        AxisLoopStep(
            action="Read the next corner and pick a line",
            player_decision="Take the tight inside line or the wide line that keeps more boost.",
            feedback="Corner markers, speed readout, and boost gauge show what the chosen line buys.",
            zh_action="读懂下一个弯道并选择一条线",
            zh_decision="走更短的内线，还是走能保留更多加速的外线。",
            zh_feedback="弯道标记、速度读数和加速槽会显示这条线换来了什么。",
        ),
        AxisLoopStep(
            action="Steer through the gate chain",
            player_decision="Hold the current line for a clean chain or cut early for a shorter but riskier path.",
            feedback="Gate color confirms each link in the chain, and a miss is announced instantly.",
            zh_action="穿行于连续门之间",
            zh_decision="保持当前路线吃满连段，还是提前切进更短但更险的路。",
            zh_feedback="门的颜色会确认连段的每一环，错过立刻有提示。",
        ),
        AxisLoopStep(
            action="Spend boost on the straight",
            player_decision="Burn boost now to pass a rival line or hold it for the final stretch.",
            feedback="Boost drains visibly and the gap timer shows exactly how much was gained.",
            zh_action="在直道上消耗加速",
            zh_decision="现在烧掉加速超过对手线，还是留到最后一段。",
            zh_feedback="加速槽可见地下降，差距计时会精确显示这次赚到了多少。",
        ),
        AxisLoopStep(
            action="Risk the final shortcut and finish",
            player_decision="Take the shortcut for a better time or stay safe and protect the current run.",
            feedback="Finish report shows split times, chain breaks, boost left, and restart affordance.",
            zh_action="赌一次最终捷径并冲线",
            zh_decision="走捷径换更好成绩，还是保守跑完保住当前这一局。",
            zh_feedback="终点报告显示分段成绩、断链次数、剩余加速和重开入口。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Line And Corner Readability",
            purpose="Makes the fast line visible before the player commits to it.",
            inputs=["player velocity", "corner marker", "surface tags"],
            outputs=["affordance color", "recommended line", "grip feedback"],
            failure_pressure="An unreadable corner costs speed and breaks the gate chain, not the run.",
            zh_name="路线与弯道可读性",
            zh_purpose="在玩家做出选择前，就把快线显示出来。",
            zh_failure="读不懂的弯道会损失速度并打断连续门，但不会毁掉整局。",
        ),
        AxisSystem(
            name="Boost Economy",
            purpose="Turns acceleration into a resource the player must spend deliberately.",
            inputs=["boost stock", "gate streaks", "elapsed time"],
            outputs=["speed burst", "gap change", "regen rate"],
            failure_pressure="Emptying boost before the final stretch surrenders the whole time advantage.",
            zh_name="加速经济",
            zh_purpose="让加速成为玩家必须有计划地花掉的资源。",
            zh_failure="在最后一段前耗尽加速，等于交出全部时间优势。",
        ),
        AxisSystem(
            name="Ghost Pressure",
            purpose="Gives a solo lap a rival without adding a full AI opponent.",
            inputs=["elapsed time", "target split", "player velocity"],
            outputs=["gap timer", "catch-up marker", "final grade"],
            failure_pressure="Falling behind the target split removes the shortcut reward rather than ending the run.",
            zh_name="幽灵压迫",
            zh_purpose="让单人跑圈也有对手，而不必真的加一个 AI。",
            zh_failure="落后于目标分段只是失去捷径奖励，不会直接结束这一局。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach steering, one corner type, and a generous gate chain with no time pressure.",
        midpoint_shift="Tighten the gates and introduce the first optional shortcut that costs boost.",
        final_minutes="Ask the player to hold a chain through mixed corners and beat the target split on the last straight.",
        unlocks=[
            "Boost pickup after the first clean gate chain",
            "Shortcut route after matching the target split once",
            "End-state lap grade after beating the final split",
        ],
        zh_first_minute="教学转向、一种弯道，以及一段没有时间压力的宽松连续门。",
        zh_midpoint_shift="收紧门的间距，并引入第一条需要消耗加速的可选捷径。",
        zh_final_minutes="要求玩家在混合弯道中保持连段，并在最后直道上跑赢目标分段。",
        zh_unlocks=[
            "第一次干净的连续门后开放加速道具",
            "首次追平目标分段后开放捷径路线",
            "跑赢最终分段后开放结算圈速评级",
        ],
    ),
    beats=[
        AxisBeat(
            name="Open Straight",
            gameplay_focus="Teach steering, one corner type, and reading the boost gauge safely.",
            required_assets=[
                "track floor marker",
                "corner marker set",
                "start gate",
                "boost gauge UI",
            ],
            success_condition="Player completes the opening chain without breaking it.",
            zh_name="起步直道",
            zh_focus="安全地教学转向、一种弯道，以及如何读懂加速槽。",
            zh_success="玩家完整跑完起步连段且没有断链。",
        ),
        AxisBeat(
            name="Switchback Section",
            gameplay_focus="Chain tighter gates through alternating corners and spend boost on one shortcut.",
            required_assets=[
                "tight gate set",
                "shortcut ramp",
                "boost pickup",
                "split timer UI",
            ],
            success_condition="Player keeps the chain alive through the switchbacks and stays near the target split.",
            zh_name="回头弯路段",
            zh_focus="在交替弯道中串起更紧的门，并在一条捷径上花掉加速。",
            zh_success="玩家在回头弯中保持连段，并维持在目标分段附近。",
        ),
        AxisBeat(
            name="Final Sprint",
            gameplay_focus="Hold the chain through mixed corners and beat the target split on the last straight.",
            required_assets=[
                "mixed corner set",
                "final straight marker",
                "finish gate",
                "lap grade UI",
            ],
            success_condition="Player crosses the finish gate ahead of the target split.",
            zh_name="最后冲刺",
            zh_focus="在混合弯道中保持连段，并在最后直道上跑赢目标分段。",
            zh_success="玩家以领先目标分段的成绩冲过终点门。",
        ),
    ],
    assets=[
        "Greybox track kit",
        "Corner marker set",
        "Start gate",
        "Tight gate set",
        "Shortcut ramp",
        "Boost pickup",
        "Mixed corner set",
        "Finish gate",
        "Split timer UI proxy",
    ],
    zh_assets=[
        "灰盒赛道套件",
        "弯道标记组",
        "起点门",
        "紧密门组",
        "捷径坡道",
        "加速拾取物",
        "混合弯道组",
        "终点门",
        "分段计时 UI proxy"
    ],
    narrative=AxisNarrative(
        player_fantasy="Find the line that makes a hard course feel effortless.",
        design_pillars=[
            "The fast line is visible before it is needed",
            "Boost is a decision, not a button",
            "A mistake costs time, not the run",
            "The rival is the clock, not a difficulty wall",
        ],
        win_state="Cross the finish gate ahead of the target split with an intact final chain.",
        failure_states=[
            "Final split is missed and the shortcut reward is forfeited",
            "Too many chain breaks drop the lap below the qualifying grade",
            "Player leaves the track boundary and loses the active lap",
        ],
        notes_for_comfyui=[
            "Generate track readability studies for corner contrast, not vehicle renders.",
            "Prioritize the visual separation between the racing line and the runoff area.",
            "Use references only after the greybox lap proves the gates readable at speed.",
        ],
    zh_notes_for_comfyui=[
        "生成弯道对比的赛道可读性研究，而不是载具渲染。",
        "优先保证竞速线与缓冲区在视觉上分离。",
        "只在灰盒圈速证明连续门在高速下可读之后使用参考图。"
    ],
        zh_player_fantasy="找到那条让一条难赛道显得毫不费力的线。",
        zh_pillars=[
            "快线要在需要之前就可见",
            "加速是决策，不是按钮",
            "失误只花时间，不花整局",
            "对手是计时器，不是难度墙",
        ],
        zh_win_state="以领先目标分段的成绩冲过终点门，且最后一段连段完整。",
        zh_failure_states=[
            "错过最终分段，捷径奖励被取消",
            "断链过多使圈速低于及格评级",
            "玩家离开赛道边界，丢失当前圈",
        ],
    ),
)


_SYSTEMS = AxisTemplate(
    # ``systems`` is the axis a prompt lands on when no other keyword family
    # matches. Its copy is deliberately generic: it describes the shape of a
    # playable slice without pretending to know the genre. That is honest, but
    # it means an unrecognised prompt still produces a generic design — if a
    # genre keeps landing here, the fix is a new axis, not better wording.
    zh_label="系统",
    verbs=["explore", "interact", "adapt", "complete"],
    loop=[
        AxisLoopStep(
            action="{verb_0} the immediate play space",
            player_decision="Choose a route, target, or interaction before pressure escalates.",
            feedback="Camera framing, UI markers, and audio cues confirm available options.",
            zh_action="{verb_0_zh}当前空间",
            zh_decision="在压力升级前选择路线、目标或互动方式。",
            zh_feedback="镜头、UI 标记和音效确认可用选择。",
        ),
        AxisLoopStep(
            action="{verb_1} to create an opening",
            player_decision="Spend time or a limited resource to improve the next move.",
            feedback="State changes are visible in the level and reflected in the objective tracker.",
            zh_action="通过{verb_1_zh}创造机会",
            zh_decision="投入时间或有限资源来改善下一步。",
            zh_feedback="关卡状态变化会被目标追踪器和场景反馈清楚呈现。",
        ),
        AxisLoopStep(
            action="{verb_2} under rising pressure",
            player_decision="Commit to the risky play or reset to a safer position.",
            feedback="Enemies, timers, hazards, or resource meters show the consequence quickly.",
            zh_action="在压力下{verb_2_zh}",
            zh_decision="选择冒险推进，还是回到更安全的位置重新组织。",
            zh_feedback="敌人、计时器、危险物或资源条会快速显示后果。",
        ),
        AxisLoopStep(
            action="{verb_3} the objective and bank progress",
            player_decision="Exit with partial gains or push for a better completion grade.",
            feedback="End screen reports time, failures, optional goals, and restart affordance.",
            zh_action="{verb_3_zh}目标并结算进度",
            zh_decision="带着基础成果撤离，还是继续争取更高完成评价。",
            zh_feedback="结算界面显示时间、失败原因、可选目标和重开入口。",
        ),
    ],
    systems=[
        AxisSystem(
            name="Objective State",
            purpose="Keeps the prototype finishable and prevents aimless play.",
            inputs=["player location", "interaction events", "objective triggers"],
            outputs=["active objective", "completion state", "restart state"],
            failure_pressure="The player loses if the primary objective becomes unreachable.",
            zh_name="目标状态",
            zh_purpose="保证原型可完成，避免玩家在空间里迷失。",
            zh_failure="如果主目标变得不可达，玩家失败。",
        ),
        AxisSystem(
            name="Pressure Clock",
            purpose="Creates urgency inside a short vertical slice.",
            inputs=["elapsed time", "alert level", "mistake count"],
            outputs=["hazard intensity", "enemy aggression", "score modifier"],
            failure_pressure="Pressure reaches a cap and forces extraction, defeat, or reset.",
            zh_name="压力时钟",
            zh_purpose="在短垂直切片里制造紧迫感。",
            zh_failure="压力到达上限后会强制撤离、失败或重开。",
        ),
        AxisSystem(
            name="Readable Interaction Layer",
            purpose="Makes every useful object obvious enough for game-jam iteration.",
            inputs=["overlap events", "line traces", "player inventory"],
            outputs=["interaction prompts", "state changes", "audio/visual feedback"],
            failure_pressure="Bad reads cost time or resources rather than hiding progress.",
            zh_name="可读互动层",
            zh_purpose="让每个有用物体足够清楚，适合快速迭代。",
            zh_failure="错误的阅读会消耗时间或资源，而不是隐藏进度。",
        ),
    ],
    progression=AxisProgression(
        first_minute="Teach movement, camera, and the first objective without punishment.",
        midpoint_shift="Combine the main verb with pressure so the player must plan ahead.",
        final_minutes="Ask the player to execute the full loop with a clear win/fail result.",
        unlocks=[
            "Optional shortcut after first objective",
            "Second interaction type after midpoint",
            "End-state scoring after completion",
        ],
        zh_first_minute="在没有惩罚的情况下教学移动、镜头和第一个目标。",
        zh_midpoint_shift="把主要动词与压力结合，让玩家必须提前计划。",
        zh_final_minutes="要求玩家用完整循环完成一次明确的胜负结算。",
        zh_unlocks=["第一个目标后开放可选捷径", "中段后开放第二种互动", "完成后开放结算评分"],
    ),
    beats=[
        AxisBeat(
            name="Onboarding Pocket",
            gameplay_focus="Learn controls and identify the objective language.",
            required_assets=["start marker", "objective prop", "interaction prompt"],
            success_condition="Player completes the first low-risk interaction.",
            zh_name="教学口袋区",
            zh_focus="学习控制并识别目标语言。",
            zh_success="玩家完成第一次低风险互动。",
        ),
        AxisBeat(
            name="System Mix",
            gameplay_focus="Use the core verbs while pressure changes the route.",
            required_assets=["arena blockers", "hazard markers", "feedback props"],
            success_condition="Player completes the central objective chain.",
            zh_name="系统混合区",
            zh_focus="在压力改变路线时使用核心动词。",
            zh_success="玩家完成中心目标链。",
        ),
        AxisBeat(
            name="Final Push",
            gameplay_focus="Resolve the complete loop with win/fail stakes.",
            required_assets=["exit gate", "final hazard", "score trigger"],
            success_condition="Player reaches the exit and receives performance feedback.",
            zh_name="最终推进",
            zh_focus="用胜负压力解决完整循环。",
            zh_success="玩家抵达出口并获得表现反馈。",
        ),
    ],
    assets=[
        "Greybox arena kit",
        "Objective prop set",
        "Hazard marker set",
        "Readable exit gate",
        "Simple UI objective tracker",
    ],
    zh_assets=[
        "灰盒场地套件",
        "目标道具组",
        "危险标记组",
        "可读出口门",
        "简易 UI 目标追踪器"
    ],
    narrative=AxisNarrative(
        player_fantasy="Master a compact systems-driven challenge through repeatable skill.",
        design_pillars=[
            "One readable objective at all times",
            "Every mechanic changes a player decision",
            "Failure teaches the next attempt",
            "Assets exist to clarify play space",
        ],
        win_state="Complete the primary objective and reach the exit before pressure caps out.",
        failure_states=[
            "Pressure clock reaches maximum",
            "Player health or critical resource reaches zero",
            "Required objective actor is destroyed or abandoned",
        ],
        notes_for_comfyui=[
            "Generate visual references only after gameplay readability needs are known.",
            "Prioritize objective, hazard, route, material, and UI clarity over style exploration.",
            "Treat generated images as reviewed references, not direct proof of playable progress.",
        ],
    zh_notes_for_comfyui=[
        "只在玩法可读性需求明确后生成视觉参考。",
        "优先表现目标、危险、路线、材质和 UI 清晰度，而不是风格探索。",
        "生成图像只能作为经评审的参考，不能证明原型已经可玩。"
    ],
        zh_player_fantasy="通过可重复练习掌握一个紧凑的系统驱动挑战。",
        zh_pillars=[
            "任何时刻都只有一个清晰目标",
            "每个机制都必须改变玩家决策",
            "失败要教会下一次尝试",
            "资产用于解释玩法空间",
        ],
        zh_win_state="在压力到达上限前完成主目标并抵达出口。",
        zh_failure_states=[
            "压力时钟到达最大值",
            "玩家生命或关键资源归零",
            "必要目标 Actor 被摧毁或放弃",
        ],
    ),
)


AXIS_TEMPLATES: dict[str, AxisTemplate] = {
    "parkour": _PARKOUR,
    "career": _CAREER,
    "stealth": _STEALTH,
    "combat": _COMBAT,
    "survival": _SURVIVAL,
    "puzzle": _PUZZLE,
    "mobility": _MOBILITY,
    "systems": _SYSTEMS,
}


def verb_fields(verbs: list[str], zh_verbs: list[str]) -> dict[str, str]:
    """Substitution fields for verb placeholders in a template.

    The generic ``systems`` axis writes its loop as "{verb_0} the immediate
    play space" so one template serves any verb set; a specialised axis names
    its actions outright and simply has nothing to substitute.
    """

    fields = {f"verb_{index}": verb for index, verb in enumerate(verbs)}
    fields.update({f"verb_{index}_zh": verb for index, verb in enumerate(zh_verbs)})
    return fields
