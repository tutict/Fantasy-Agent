const HANDOFF_KEY = "fantasy-agent-planning-handoff";

const correctionModeKeys = {
  gameplay: "modeGameplay",
  visuals: "modeVisuals",
  scope: "modeScope",
  import: "modeImport"
};

const correctionModeManualTargets = {
  gameplay: "planning",
  visuals: "comfyui",
  scope: "planning",
  import: "engine"
};

const manualTargetKeys = {
  planning: {
    label: "manualTargetPlanning",
    detail: "manualPlanningDetail"
  },
  comfyui: {
    label: "manualTargetComfyui",
    detail: "manualComfyMissing"
  },
  blender: {
    label: "manualTargetBlender",
    detail: "manualBlenderMissing"
  },
  unreal: {
    label: "manualTargetUnreal",
    detail: "manualUnrealMissing"
  },
  godot: {
    label: "manualTargetGodot",
    detail: "manualGodotMissing"
  },
  generated: {
    label: "manualTargetGenerated",
    detail: "manualGeneratedDetail"
  }
};

const i18n = {
  en: {
    productLabel: "Flow console",
    handoffTitle: "Planning handoff",
    handoffEmpty: "No planning handoff found.",
    handoffHint:
      "Planning Workbench owns idea capture. This console reviews the plan and records correction decisions before real tool operations.",
    handoffLoaded: "Latest handoff loaded",
    handoffReceived: "Planning handoff received",
    handoffLoadedShort: "Loaded",
    loadHandoff: "Load latest handoff",
    handoffSource: "Source",
    handoffTime: "Saved",
    handoffPlan: "Plan",
    openPlanningHint: "Generate or update the plan in Planning Workbench, then return here.",
    correctionTitle: "Correction queue",
    modeGameplay: "Gameplay loop",
    modeVisuals: "Visual direction",
    modeScope: "Scope control",
    modeImport: "Technical import",
    correctionNotes: "Correction notes",
    correctionPlaceholder:
      "Example: hazard color is unclear; keep wall-run routes readable before ComfyUI polish.",
    recordCorrection: "Record correction",
    correctionRecorded: "Correction recorded",
    correctionRequiresPlan: "Load a planning handoff before recording correction.",
    correctionPending: "Pending correction",
    statusLabel: "Execution readiness",
    emptyTitle: "No handoff loaded",
    idle: "Waiting",
    ready: "Reviewing",
    error: "Needs attention",
    toggleLog: "Activity",
    currentStage: "Current stage",
    nextStage: "Next stage",
    reviewItems: "Review items",
    blockedTasks: "Blocked tasks",
    tabOverview: "Overview",
    tabPipeline: "Pipeline",
    tabTasks: "Tasks",
    tabReview: "Review",
    tabBuild: "Build",
    tabVisuals: "Visuals",
    tabQa: "QA",
    tabGdd: "GDD",
    tabDsl: "DSL",
    emptyHeading: "Load a plan from Planning Workbench",
    emptyBody: "Use this console to review handoffs, capture corrections, and confirm execution steps.",
    gatesTitle: "Execution confirmations",
    defaultGateVisuals: "ComfyUI execution",
    defaultGateMeshes: "Blender execution",
    defaultGateUnreal: "Unreal execution",
    waitingForPlan: "Waiting for handoff",
    pillars: "Design pillars",
    loop: "Core loop",
    systems: "Systems",
    next: "Next actions",
    recommended: "Recommended",
    confirmation: "Confirmation required",
    sideEffects: "Tool operations",
    dependencies: "Dependencies",
    artifacts: "Artifacts",
    quality: "Quality gates",
    risks: "Risks",
    outputs: "Outputs",
    owner: "Owner",
    tools: "Tools",
    unreal: "Unreal plan",
    godot: "Godot quick-play",
    blender: "Blender jobs",
    comfyui: "ComfyUI references",
    creativeReview: "Creative review",
    artDirection: "Art direction",
    reviewQuestions: "Review questions",
    requiredDecisions: "Required decisions",
    approvalGate: "Approval gate",
    approve: "Approve",
    revise: "Revise",
    reject: "Reject",
    pendingReview: "Pending review",
    approved: "Approved",
    needsRevision: "Needs revision",
    rejected: "Rejected",
    qa: "QA checks",
    session: "Target session",
    minutes: "minutes",
    win: "Win state",
    failure: "Failure states",
    maps: "Maps",
    classes: "Gameplay classes",
    folders: "Folders",
    automation: "Automation",
    jobs: "Jobs",
    rules: "Usage rules",
    smoke: "Smoke tests",
    playability: "Playability checks",
    packaging: "Packaging checks",
    activityTitle: "Activity",
    switchedLocale: "Switched locale",
    reviewDecision: "Review decision",
    noItems: "No items",
    invalidHandoff: "Invalid planning handoff",
    themeDark: "Dark",
    themeLight: "Light",
    manualCorrectionTitle: "Manual correction",
    manualCorrectionHint:
      "Open the tool that owns this correction. Clicking an open action confirms one local tool operation.",
    manualRecommended: "Recommended",
    manualOpenRecommended: "Open recommended tool",
    manualOpen: "Open",
    manualChecking: "Checking local tools...",
    manualTargetPlanning: "Planning Workbench",
    manualTargetComfyui: "ComfyUI",
    manualTargetBlender: "Blender",
    manualTargetUnreal: "Unreal Editor",
    manualTargetGodot: "Godot",
    manualTargetGenerated: "Generated folder",
    manualPlanningDetail: "Return to the idea interview and planning preview when the correction changes the concept, loop, or scope.",
    manualComfyReady: "ComfyUI is reachable. Use it to revise visual references, logo direction, UI references, or material cues.",
    manualComfyMissing: "ComfyUI is not responding yet. Open the default local address after starting ComfyUI.",
    manualBlenderReady: "Blender is available. Use it to adjust modular meshes, scale, origins, collision naming, or greybox readability.",
    manualBlenderMissing: "Blender was not found. Install Blender or set BLENDER_EXECUTABLE before mesh correction.",
    manualUnrealReady: "Unreal Editor is available. Use it for asset ingest, level assembly, PIE validation, and gameplay tuning.",
    manualUnrealMissing: "Unreal Editor was not found. Install UE5 or set UNREAL_EDITOR before engine correction.",
    manualGodotReady: "Godot is available. Use it for quick playable-loop validation and route readability correction.",
    manualGodotMissing: "Godot was not found. Install Godot 4 or set GODOT_EXECUTABLE before quick-play correction.",
    manualGeneratedDetail: "Open generated handoff files, scripts, manifests, and exported assets for inspection.",
    manualStatusReady: "Ready",
    manualStatusDegraded: "Needs setup",
    manualStatusUnavailable: "Unavailable",
    manualOpenNeedsConfirmation: "Opening local tools requires an explicit click confirmation.",
    manualOpenUnknownTarget: "Unknown correction target.",
    manualOpenUnavailable: "Correction target is unavailable.",
    manualOpenStarted: "Correction target opened",
    manualOpenBlocked: "Correction target blocked",
    generateTitle: "Generate playable demo",
    generateHint:
      "Run the full executor chain for the loaded plan. Each side effect is confirmed once before anything is written.",
    generateButton: "Generate playable demo",
    generateWithAssets: "Include Blender assets",
    generateWithVisuals: "Include ComfyUI references",
    generateRequiresPlan: "Load a planning handoff before generating a demo.",
    generateConfirmTitle: "Confirm execution",
    generateConfirmIntro: "The following side effects will run:",
    generateConfirmProceed: "Proceed",
    generateConfirmCancel: "Cancel",
    generateRunning: "Generating demo…",
    generateDone: "Demo generated",
    generateFailed: "Demo generation failed",
    generateArtifact: "Project"
  },
  "zh-CN": {
    productLabel: "流程控制台",
    handoffTitle: "策划交接",
    handoffEmpty: "未找到策划交接。",
    handoffHint: "策划工作台负责玩法输入和方案生成；这里负责检查交接、记录纠偏，并在实际执行前确认。",
    handoffLoaded: "已载入最新交接",
    handoffReceived: "已收到策划交接",
    handoffLoadedShort: "已载入",
    loadHandoff: "载入最新交接",
    handoffSource: "来源",
    handoffTime: "保存时间",
    handoffPlan: "方案",
    openPlanningHint: "请先在策划工作台生成或更新方案，然后回到这里。",
    correctionTitle: "纠偏队列",
    modeGameplay: "玩法循环",
    modeVisuals: "视觉方向",
    modeScope: "范围控制",
    modeImport: "技术导入",
    correctionNotes: "纠偏记录",
    correctionPlaceholder: "例：危险色块不够清楚；ComfyUI 润色前先保证蹬墙路线可读。",
    recordCorrection: "记录纠偏",
    correctionRecorded: "已记录纠偏",
    correctionRequiresPlan: "请先载入策划交接，再记录纠偏。",
    correctionPending: "待处理纠偏",
    statusLabel: "执行准备度",
    emptyTitle: "尚未载入交接",
    idle: "等待中",
    ready: "审阅中",
    error: "需要处理",
    toggleLog: "活动",
    currentStage: "当前阶段",
    nextStage: "下一阶段",
    reviewItems: "审阅项",
    blockedTasks: "阻塞任务",
    tabOverview: "概览",
    tabPipeline: "流水线",
    tabTasks: "任务",
    tabReview: "审阅",
    tabBuild: "构建",
    tabVisuals: "视觉",
    tabQa: "QA",
    tabGdd: "GDD",
    tabDsl: "DSL",
    emptyHeading: "从策划工作台载入方案",
    emptyBody: "流程控制台用于检查交接、记录纠偏，并确认 ComfyUI、Blender、Unreal 等执行前事项。",
    gatesTitle: "执行前确认",
    defaultGateVisuals: "ComfyUI 执行",
    defaultGateMeshes: "Blender 执行",
    defaultGateUnreal: "Unreal 执行",
    waitingForPlan: "等待交接",
    pillars: "设计支柱",
    loop: "核心循环",
    systems: "系统",
    next: "下一步",
    recommended: "推荐",
    confirmation: "需要确认",
    sideEffects: "实际操作",
    dependencies: "依赖",
    artifacts: "产物",
    quality: "质量门",
    risks: "风险",
    outputs: "产出",
    owner: "负责人",
    tools: "工具",
    unreal: "Unreal 计划",
    godot: "Godot 快速验证",
    blender: "Blender 任务",
    comfyui: "ComfyUI 参考",
    creativeReview: "创意审阅",
    artDirection: "艺术方向",
    reviewQuestions: "审阅问题",
    requiredDecisions: "必要决定",
    approvalGate: "审批门",
    approve: "批准",
    revise: "修改",
    reject: "拒绝",
    pendingReview: "待审阅",
    approved: "已批准",
    needsRevision: "需要修改",
    rejected: "已拒绝",
    qa: "QA 检查",
    session: "目标时长",
    minutes: "分钟",
    win: "胜利状态",
    failure: "失败状态",
    maps: "地图",
    classes: "玩法类",
    folders: "目录",
    automation: "自动化",
    jobs: "任务",
    rules: "使用规则",
    smoke: "冒烟测试",
    playability: "可玩性检查",
    packaging: "打包检查",
    activityTitle: "活动",
    switchedLocale: "已切换语言",
    reviewDecision: "审阅决定",
    noItems: "无项目",
    invalidHandoff: "策划交接无效",
    themeDark: "深色",
    themeLight: "浅色",
    manualCorrectionTitle: "手动纠偏入口",
    manualCorrectionHint: "进入负责该纠偏的软件。点击打开按钮即表示确认执行一次本地实际操作。",
    manualRecommended: "推荐",
    manualOpenRecommended: "打开推荐工具",
    manualOpen: "打开",
    manualChecking: "正在检测本地工具...",
    manualTargetPlanning: "策划工作台",
    manualTargetComfyui: "ComfyUI",
    manualTargetBlender: "Blender",
    manualTargetUnreal: "Unreal Editor",
    manualTargetGodot: "Godot",
    manualTargetGenerated: "生成目录",
    manualPlanningDetail: "当纠偏会改变创意、核心循环或范围时，回到访谈和策划预览继续调整。",
    manualComfyReady: "ComfyUI 可连接。用于修正人物立绘、Logo、UI 参考、材质提示和视觉方向。",
    manualComfyMissing: "ComfyUI 尚未响应。启动 ComfyUI 后可打开默认本地地址检查。",
    manualBlenderReady: "Blender 可用。用于修正模块化模型、尺寸、origin、碰撞命名和灰盒可读性。",
    manualBlenderMissing: "未找到 Blender。请安装 Blender，或设置 BLENDER_EXECUTABLE 后再进行模型纠偏。",
    manualUnrealReady: "Unreal Editor 可用。用于资产导入、关卡组装、PIE 验证和玩法调参。",
    manualUnrealMissing: "未找到 Unreal Editor。请安装 UE5，或设置 UNREAL_EDITOR 后再进行引擎纠偏。",
    manualGodotReady: "Godot 可用。用于快速验证可玩循环、路线可读性和交互节奏。",
    manualGodotMissing: "未找到 Godot。请安装 Godot 4，或设置 GODOT_EXECUTABLE 后再进行快速可玩纠偏。",
    manualGeneratedDetail: "打开生成的交接文件、脚本、manifest 和导出资产进行检查。",
    manualStatusReady: "可用",
    manualStatusDegraded: "需配置",
    manualStatusUnavailable: "不可用",
    manualOpenNeedsConfirmation: "打开本地工具需要明确点击确认。",
    manualOpenUnknownTarget: "未知纠偏目标。",
    manualOpenUnavailable: "纠偏目标不可用。",
    manualOpenStarted: "已打开纠偏目标",
    manualOpenBlocked: "纠偏目标已阻止",
    generateTitle: "一键生成可玩 demo",
    generateHint: "对已加载的计划运行完整执行链。每个副作用在写盘前会先确认一次。",
    generateButton: "一键生成可玩 demo",
    generateWithAssets: "包含 Blender 资产",
    generateWithVisuals: "包含 ComfyUI 参考图",
    generateRequiresPlan: "请先加载策划交接，再生成 demo。",
    generateConfirmTitle: "确认执行",
    generateConfirmIntro: "以下副作用将被执行：",
    generateConfirmProceed: "继续",
    generateConfirmCancel: "取消",
    generateRunning: "正在生成 demo…",
    generateDone: "demo 已生成",
    generateFailed: "demo 生成失败",
    generateArtifact: "工程"
  }
};

const THEME_KEY = "fantasy-agent-theme";

function initialLocale() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("locale") || localStorage.getItem("fantasy-agent-web-console-locale");
  if (requested === "zh-CN" || requested === "en") return requested;
  return navigator.language?.startsWith("zh") ? "zh-CN" : "en";
}

function initialTheme() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("theme") || localStorage.getItem(THEME_KEY);
  if (requested === "light" || requested === "dark") return requested;
  // Light-first: default to light unless the OS explicitly prefers dark.
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

let uiLocale = initialLocale();
let uiTheme = initialTheme();
let currentPlan = null;
let currentHandoff = null;
let currentGddLocale = uiLocale;
let selectedCorrectionMode = "gameplay";
let reviewDecisions = {};
let correctionEntries = [];
let activityEntries = [];
let manualTargetsPayload = null;

const statusChip = document.querySelector("#status-chip");
const planTitle = document.querySelector("#plan-title");
const emptyState = document.querySelector(".empty-state");
const overviewContent = document.querySelector("#overview-content");
const pipelineOutput = document.querySelector("#pipeline-output");
const tasksOutput = document.querySelector("#tasks-output");
const reviewOutput = document.querySelector("#review-output");
const reviewInspector = document.querySelector("#review-inspector");
const dslOutput = document.querySelector("#dsl-output");
const gddOutput = document.querySelector("#gdd-output");
const buildOutput = document.querySelector("#build-output");
const visualsOutput = document.querySelector("#visuals-output");
const qaOutput = document.querySelector("#qa-output");
const gateSummary = document.querySelector("#gate-summary");
const stageStrip = document.querySelector("#stage-strip");
const activityDrawer = document.querySelector("#activity-drawer");
const activityLog = document.querySelector("#activity-log");
const activityCount = document.querySelector("#activity-count");
const handoffSummary = document.querySelector("#handoff-summary");
const handoffState = document.querySelector("#handoff-state");
const loadHandoffButton = document.querySelector("#load-handoff-button");
const correctionNotes = document.querySelector("#correction-notes");
const recordCorrectionButton = document.querySelector("#record-correction-button");
const manualToolSummary = document.querySelector("#manual-tool-summary");
const manualToolGrid = document.querySelector("#manual-tool-grid");
const openRecommendedToolButton = document.querySelector("#open-recommended-tool-button");

function t(key) {
  return i18n[uiLocale]?.[key] || i18n.en[key] || key;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function list(items) {
  if (!items || !items.length) return `<p>${escapeHtml(t("noItems"))}</p>`;
  return `<ul>${items.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("")}</ul>`;
}

function numbered(items, mapper) {
  if (!items || !items.length) return `<p>${escapeHtml(t("noItems"))}</p>`;
  return `<ol>${items.map((item, index) => `<li>${mapper(item, index)}</li>`).join("")}</ol>`;
}

function block(title, body, wide = false) {
  return `<section class="summary-block${wide ? " wide" : ""}"><h3>${escapeHtml(title)}</h3>${body}</section>`;
}

function statusLabel(status) {
  if (status === "approved") return t("approved");
  if (status === "needs_revision") return t("needsRevision");
  if (status === "rejected") return t("rejected");
  if (status === "pending_user_review") return t("pendingReview");
  return status;
}

function modeLabel(mode) {
  return t(correctionModeKeys[mode] || "modeGameplay");
}

function selectedEngineVersion() {
  if (!currentPlan) return "UE5";
  return usesGodotEngine(currentPlan)
    ? currentPlan.godot_plan?.engine_version || "Godot 4"
    : currentPlan.unreal_plan?.engine_version || "UE5";
}

function recommendedManualTargetId() {
  const mapped = correctionModeManualTargets[selectedCorrectionMode] || "planning";
  if (mapped === "engine") {
    return usesGodotEngine(currentPlan) ? "godot" : "unreal";
  }
  return mapped;
}

function manualStatusLabel(status) {
  if (status === "ready") return t("manualStatusReady");
  if (status === "degraded") return t("manualStatusDegraded");
  return t("manualStatusUnavailable");
}

function manualTargetLabel(target) {
  const keys = manualTargetKeys[target.id] || manualTargetKeys.planning;
  return t(keys.label);
}

function manualTargetDetail(target) {
  const keys = manualTargetKeys[target.id] || manualTargetKeys.planning;
  return t(target.detail_key || keys.detail);
}

function localizedRoute(path) {
  const search = new URLSearchParams({ locale: uiLocale, theme: uiTheme });
  return `${path}?${search.toString()}`;
}

function addActivity(label, message) {
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  activityEntries = [{ time, label, message }, ...activityEntries].slice(0, 12);
  renderActivity();
}

function renderActivity() {
  activityCount.textContent = String(activityEntries.length);
  activityLog.innerHTML = activityEntries
    .map(
      (entry) =>
        `<li><span>${escapeHtml(entry.time)}</span><div><strong>${escapeHtml(entry.label)}</strong><br>${escapeHtml(entry.message)}</div></li>`
    )
    .join("");
}

function applyLocale(locale, options = {}) {
  uiLocale = locale === "zh-CN" ? "zh-CN" : "en";
  currentGddLocale = uiLocale;
  localStorage.setItem("fantasy-agent-web-console-locale", uiLocale);
  document.documentElement.lang = uiLocale;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll(".locale-option").forEach((button) => {
    button.classList.toggle("active", button.dataset.locale === uiLocale);
  });
  document.querySelectorAll("[data-gdd-locale]").forEach((button) => {
    button.classList.toggle("active", button.dataset.gddLocale === currentGddLocale);
  });
  document.querySelectorAll("[data-correction-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.correctionMode === selectedCorrectionMode);
  });
  renderHandoffSummary(currentHandoff || readPlanningHandoff());
  renderManualCorrectionTools();
  if (currentPlan) {
    renderPlan(currentPlan, { keepDecisions: true });
  } else {
    clearPlanView();
  }
  if (!options.silent) addActivity(t("switchedLocale"), uiLocale);
}

function applyTheme(theme) {
  uiTheme = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = uiTheme;
  localStorage.setItem(THEME_KEY, uiTheme);
  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.classList.toggle("active", button.dataset.themeChoice === uiTheme);
  });
}

function setStatus(state) {
  statusChip.dataset.state = state;
  statusChip.textContent = t(state);
}

function preferredTitle(spec) {
  if (!spec) return t("emptyTitle");
  return uiLocale === "zh-CN" && spec.i18n?.field_translations?.title?.["zh-CN"]
    ? spec.i18n.field_translations.title["zh-CN"]
    : spec.title;
}

function localizedStageTitle(stage) {
  return uiLocale === "zh-CN"
    ? stage.title_i18n?.["zh-CN"] || stage.title
    : stage.title_i18n?.en || stage.title;
}

function localizedTaskTitle(task) {
  return uiLocale === "zh-CN"
    ? task.title_i18n?.["zh-CN"] || task.title
    : task.title_i18n?.en || task.title;
}

function handoffTitle(handoff) {
  return handoff?.title || preferredTitle(handoff?.plan?.gameplay_spec) || t("emptyTitle");
}

function formatSavedAt(savedAt) {
  if (!savedAt) return "-";
  const parsed = new Date(savedAt);
  if (Number.isNaN(parsed.getTime())) return savedAt;
  return parsed.toLocaleString(uiLocale, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function readPlanningHandoff() {
  try {
    const raw = localStorage.getItem(HANDOFF_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.plan?.gameplay_spec) return parsed;
    if (parsed?.gameplay_spec) {
      return {
        schemaVersion: "0.1",
        source: "direct-plan",
        savedAt: null,
        title: preferredTitle(parsed.gameplay_spec),
        plan: parsed
      };
    }
  } catch {
    return { invalid: true };
  }
  return { invalid: true };
}

function savePlanningHandoff(plan, source = "planning-workbench") {
  const handoff = {
    schemaVersion: "0.1",
    source,
    savedAt: new Date().toISOString(),
    title: preferredTitle(plan.gameplay_spec),
    plan
  };
  localStorage.setItem(HANDOFF_KEY, JSON.stringify(handoff));
  return handoff;
}

function renderHandoffSummary(handoff) {
  if (handoff?.invalid) {
    handoffState.textContent = t("error");
    handoffSummary.innerHTML = `<p>${escapeHtml(t("invalidHandoff"))}</p>`;
    return;
  }
  if (!handoff?.plan) {
    handoffState.textContent = t("waitingForPlan");
    handoffSummary.innerHTML = `<p>${escapeHtml(t("handoffEmpty"))}</p><p>${escapeHtml(t("openPlanningHint"))}</p>`;
    return;
  }
  const spec = handoff.plan.gameplay_spec;
  handoffState.textContent = t("handoffLoadedShort");
  handoffSummary.innerHTML = [
    `<strong>${escapeHtml(handoffTitle(handoff))}</strong>`,
    `<div class="handoff-meta"><span>${escapeHtml(t("handoffSource"))}: ${escapeHtml(handoff.source || "-")}</span><span>${escapeHtml(t("handoffTime"))}: ${escapeHtml(formatSavedAt(handoff.savedAt))}</span><span>${escapeHtml(t("session"))}: ${escapeHtml(spec?.target_session_minutes || "-")} ${escapeHtml(t("minutes"))}</span></div>`
  ].join("");
}

function fallbackManualTargets() {
  const engineTarget = usesGodotEngine(currentPlan) ? "godot" : "unreal";
  return ["planning", "comfyui", "blender", engineTarget, "generated"].map((id) => ({
    id,
    status: id === "planning" || id === "generated" ? "ready" : "degraded",
    target: id === "planning" ? "/workbench" : "-",
    openable: id === "planning" || id === "generated",
    detail_key: manualTargetKeys[id]?.detail
  }));
}

function renderManualCorrectionTools() {
  const targets = manualTargetsPayload?.targets?.length
    ? manualTargetsPayload.targets
    : fallbackManualTargets();
  const recommended = recommendedManualTargetId();
  const recommendedTarget = targets.find((target) => target.id === recommended) || targets[0];
  manualToolSummary.textContent = `${t("manualRecommended")}: ${manualTargetLabel(recommendedTarget)} / ${modeLabel(selectedCorrectionMode)}`;
  openRecommendedToolButton.disabled = !recommendedTarget?.openable;
  openRecommendedToolButton.dataset.manualTarget = recommendedTarget?.id || recommended;
  manualToolGrid.innerHTML = targets
    .map((target) => {
      const isRecommended = target.id === recommended;
      const state = target.status === "ready" || target.status === "degraded" ? target.status : "unavailable";
      return `
        <article class="manual-tool-card" data-state="${escapeHtml(state)}" data-recommended="${isRecommended ? "true" : "false"}">
          <div class="manual-tool-top">
            <div>
              <h3>${escapeHtml(manualTargetLabel(target))}</h3>
              <span>${escapeHtml(manualStatusLabel(state))}</span>
            </div>
            ${isRecommended ? `<strong>${escapeHtml(t("manualRecommended"))}</strong>` : ""}
          </div>
          <p>${escapeHtml(manualTargetDetail(target))}</p>
          <code>${escapeHtml(target.target || "-")}</code>
          <button class="manual-card-action" type="button" data-manual-target="${escapeHtml(target.id)}" ${target.openable ? "" : "disabled"}>
            ${escapeHtml(t("manualOpen"))}
          </button>
        </article>
      `;
    })
    .join("");
}

async function loadManualCorrectionTargets() {
  manualToolSummary.textContent = t("manualChecking");
  renderManualCorrectionTools();
  try {
    const query = new URLSearchParams({ engine: selectedEngineVersion() });
    const response = await fetch(`/api/manual-correction/targets?${query.toString()}`, {
      headers: { Accept: "application/json" }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    manualTargetsPayload = await response.json();
  } catch {
    manualTargetsPayload = null;
  }
  renderManualCorrectionTools();
}

async function openManualCorrectionTarget(targetId) {
  if (targetId === "planning") {
    window.open(localizedRoute("/workbench"), "_blank", "noopener");
    addActivity(t("manualOpenStarted"), t("manualTargetPlanning"));
    return;
  }
  const target = targetId === "engine" ? recommendedManualTargetId() : targetId;
  try {
    const response = await fetch("/api/manual-correction/open", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: JSON.stringify({
        target_id: target,
        engine: selectedEngineVersion(),
        confirmed_side_effects: true
      })
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    const label = t(result.detail_key) || result.detail || result.status;
    if (result.status === "started" || result.status === "client_route") {
      addActivity(t("manualOpenStarted"), `${target}: ${result.target || label}`);
    } else {
      addActivity(t("manualOpenBlocked"), `${target}: ${label}`);
    }
  } catch (error) {
    addActivity(t("manualOpenBlocked"), String(error));
  } finally {
    loadManualCorrectionTargets();
  }
}

function loadPlanningHandoff(options = {}) {
  const handoff = readPlanningHandoff();
  renderHandoffSummary(handoff);
  if (!handoff?.plan) {
    if (!options.silent) {
      setStatus("error");
      addActivity(t("handoffEmpty"), t("openPlanningHint"));
    }
    return false;
  }
  currentHandoff = handoff;
  renderPlan(handoff.plan, { keepDecisions: true });
  if (!options.silent) {
    addActivity(options.activityLabel || t("handoffLoaded"), handoffTitle(handoff));
  }
  return true;
}

function clearPlanView() {
  currentPlan = null;
  planTitle.textContent = t("emptyTitle");
  setStatus("idle");
  emptyState.classList.remove("hidden");
  overviewContent.classList.add("hidden");
  overviewContent.innerHTML = "";
  pipelineOutput.innerHTML = "";
  tasksOutput.innerHTML = "";
  reviewOutput.innerHTML = "";
  reviewInspector.innerHTML = "";
  buildOutput.innerHTML = "";
  visualsOutput.innerHTML = "";
  qaOutput.innerHTML = "";
  gddOutput.textContent = "";
  dslOutput.textContent = "";
  document.querySelector("#metric-current-stage").textContent = "-";
  document.querySelector("#metric-next-stage").textContent = "-";
  document.querySelector("#metric-review-items").textContent = "0";
  document.querySelector("#metric-blocked-tasks").textContent = "0";
  renderDefaultGates();
  renderManualCorrectionTools();
}

function renderDefaultGates() {
  gateSummary.innerHTML = [
    gateItem(t("defaultGateVisuals"), t("waitingForPlan")),
    gateItem(t("defaultGateMeshes"), t("waitingForPlan")),
    gateItem(t("defaultGateUnreal"), t("waitingForPlan"))
  ].join("");
}

function gateItem(title, detail) {
  return `<div class="gate-item"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>`;
}

function renderGates(plan) {
  const tasks = plan.task_breakdown?.tasks || [];
  const gated = tasks.filter((task) => task.requires_confirmation).slice(0, 6);
  const corrections = correctionEntries
    .slice(0, 3)
    .map((entry) => gateItem(`${t("correctionPending")} · ${modeLabel(entry.mode)}`, entry.notes));
  const gates = gated.length
    ? gated.map((task) => gateItem(localizedTaskTitle(task), task.side_effects?.join(", ") || task.status))
    : [gateItem(t("confirmation"), t("noItems"))];
  gateSummary.innerHTML = [...corrections, ...gates].join("");
}

function initializeReviewDecisions(plan, keepDecisions) {
  if (!keepDecisions) reviewDecisions = {};
  for (const item of plan.creative_review?.items || []) {
    reviewDecisions[item.asset_id] = reviewDecisions[item.asset_id] || item.approval_status;
  }
}

function renderPlan(plan, options = {}) {
  currentPlan = plan;
  initializeReviewDecisions(plan, options.keepDecisions);
  const spec = plan.gameplay_spec;
  planTitle.textContent = preferredTitle(spec);
  setStatus("ready");

  emptyState.classList.add("hidden");
  overviewContent.classList.remove("hidden");

  renderMetrics(plan);
  renderStageStrip(plan);
  renderGates(plan);
  renderOverview(plan);
  renderPipeline(plan);
  renderTasks(plan);
  renderReview(plan);
  renderBuild(plan);
  renderVisuals(plan);
  renderQa(plan);
  renderGdd(plan);
  dslOutput.textContent = JSON.stringify(spec, null, 2);
  loadManualCorrectionTargets();
}

function renderMetrics(plan) {
  const pipeline = plan.production_pipeline;
  const tasks = plan.task_breakdown?.tasks || [];
  document.querySelector("#metric-current-stage").textContent = pipeline?.current_stage || "-";
  document.querySelector("#metric-next-stage").textContent = pipeline?.next_stage || "-";
  document.querySelector("#metric-review-items").textContent = String(plan.creative_review?.items?.length || 0);
  document.querySelector("#metric-blocked-tasks").textContent = String(tasks.filter((task) => task.status === "blocked").length);
}

function renderStageStrip(plan) {
  const stages = plan.production_pipeline?.stages || [];
  if (!stages.length) return;
  stageStrip.innerHTML = stages
    .map(
      (stage) =>
        `<div class="stage-node ${escapeHtml(stage.status)} ${stage.id === plan.production_pipeline?.current_stage ? "is-active" : ""}"><span>${String(stage.order).padStart(2, "0")}</span><strong>${escapeHtml(localizedStageTitle(stage))}</strong></div>`
    )
    .join("");
}

function renderOverview(plan) {
  const spec = plan.gameplay_spec;
  overviewContent.innerHTML = [
    block(t("session"), `<p>${spec.target_session_minutes} ${t("minutes")}</p>`),
    block(t("win"), `<p>${escapeHtml(spec.win_state)}</p>`),
    block(t("pillars"), list(spec.design_pillars)),
    block(t("failure"), list(spec.failure_states)),
    block(
      t("loop"),
      numbered(
        spec.core_loop,
        (step) => `<strong>${escapeHtml(step.action)}</strong><br><span>${escapeHtml(step.player_decision)}</span>`
      ),
      true
    ),
    block(
      t("systems"),
      numbered(
        spec.systems,
        (system) => `<strong>${escapeHtml(system.name)}</strong><br><span>${escapeHtml(system.purpose)}</span>`
      ),
      true
    ),
    block(t("next"), list(plan.next_actions), true)
  ].join("");
}

function renderPipeline(plan) {
  const pipeline = plan.production_pipeline;
  if (!pipeline) {
    pipelineOutput.innerHTML = "";
    return;
  }
  pipelineOutput.innerHTML = [
    `<section class="stage-row wide"><h3>${escapeHtml(pipeline.project_name)}</h3><p>${escapeHtml(pipeline.goal)}</p><div class="stage-meta"><span class="stage-pill">${escapeHtml(t("currentStage"))}: ${escapeHtml(pipeline.current_stage)}</span><span class="stage-pill">${escapeHtml(t("nextStage"))}: ${escapeHtml(pipeline.next_stage)}</span></div></section>`,
    ...(pipeline.stages || []).map((stage) => {
      const meta = [
        `<span class="stage-pill ${escapeHtml(stage.status)}">${escapeHtml(stage.status)}</span>`,
        `<span class="stage-pill">${escapeHtml(t("owner"))}: ${escapeHtml(stage.owner_agent)}</span>`,
        stage.requires_confirmation ? `<span class="stage-pill">${escapeHtml(t("confirmation"))}</span>` : "",
        stage.mcp_tools?.length ? `<span class="stage-pill">${escapeHtml(t("tools"))}: ${escapeHtml(stage.mcp_tools.join(", "))}</span>` : ""
      ]
        .filter(Boolean)
        .join("");
      return `<section class="stage-row"><h3>${String(stage.order).padStart(2, "0")} ${escapeHtml(localizedStageTitle(stage))}</h3><p>${escapeHtml(stage.purpose)}</p><div class="stage-meta">${meta}</div><h3>${escapeHtml(t("quality"))}</h3>${list(stage.quality_gates)}${stage.risks?.length ? `<h3>${escapeHtml(t("risks"))}</h3>${list(stage.risks)}` : ""}</section>`;
    })
  ].join("");
}

function renderTasks(plan) {
  const breakdown = plan.task_breakdown;
  if (!breakdown) {
    tasksOutput.innerHTML = "";
    return;
  }
  const goal =
    uiLocale === "zh-CN"
      ? breakdown.goal_i18n?.["zh-CN"] || breakdown.goal
      : breakdown.goal_i18n?.en || breakdown.goal;
  tasksOutput.innerHTML = [
    `<section class="task-row"><div><h3>${escapeHtml(goal)}</h3><p>${escapeHtml(t("recommended"))}: ${escapeHtml(breakdown.recommended_next_task)}</p></div><span class="task-pill">${breakdown.tasks.length}</span></section>`,
    ...(breakdown.tasks || []).map((task) => {
      const detail = [
        `<span class="task-pill ${escapeHtml(task.status)}">${escapeHtml(task.status)}</span>`,
        `<span class="task-pill">${escapeHtml(task.id)}</span>`,
        `<span class="task-pill">${escapeHtml(task.agent)}</span>`,
        task.requires_confirmation ? `<span class="task-pill">${escapeHtml(t("confirmation"))}</span>` : "",
        task.depends_on?.length
          ? `<span class="task-pill">${escapeHtml(t("dependencies"))}: ${escapeHtml(task.depends_on.length)}</span>`
          : "",
        task.side_effects?.length
          ? `<span class="task-pill">${escapeHtml(t("sideEffects"))}: ${escapeHtml(task.side_effects.length)}</span>`
          : ""
      ]
        .filter(Boolean)
        .join("");
      return `<section class="task-row"><div><h3>${escapeHtml(localizedTaskTitle(task))}</h3><p>${escapeHtml(task.purpose)}</p><div class="task-meta">${detail}</div></div></section>`;
    })
  ].join("");
}

function renderReview(plan) {
  const report = plan.creative_review;
  const items = report?.items || [];
  reviewOutput.innerHTML = items.length
    ? items.map((item) => reviewItemHtml(item)).join("")
    : `<section class="review-item"><div><h3>${escapeHtml(t("creativeReview"))}</h3><p>${escapeHtml(t("noItems"))}</p></div></section>`;
  reviewInspector.innerHTML = report
    ? [
        `<h3>${escapeHtml(t("artDirection"))}</h3><p>${escapeHtml(report.art_direction.visual_intent)}</p>`,
        `<h3>${escapeHtml(t("reviewQuestions"))}</h3>${list(report.art_direction.user_review_questions)}`,
        `<h3>${escapeHtml(t("requiredDecisions"))}</h3>${list(report.required_user_decisions)}`,
        `<div class="review-meta"><span class="review-pill">${escapeHtml(t("approvalGate"))}: ${escapeHtml(report.approval_gate)}</span></div>`
      ].join("")
    : "";
  bindReviewActions();
}

function reviewItemHtml(item) {
  const decision = reviewDecisions[item.asset_id] || item.approval_status;
  const actions = [
    ["approved", t("approve")],
    ["needs_revision", t("revise")],
    ["rejected", t("reject")]
  ]
    .map(
      ([value, label]) =>
        `<button class="review-action ${decision === value ? "active" : ""}" type="button" data-asset-id="${escapeHtml(item.asset_id)}" data-decision="${value}">${escapeHtml(label)}</button>`
    )
    .join("");
  return `<section class="review-item"><div><h3>${escapeHtml(item.asset_id)}</h3><p>${escapeHtml(item.user_prompt)}</p><code>${escapeHtml(item.asset_path)}</code><div class="review-meta"><span class="review-pill ${escapeHtml(decision)}">${escapeHtml(statusLabel(decision))}</span><span class="review-pill">${escapeHtml(item.source)}</span><span class="review-pill">${escapeHtml(item.gameplay_role)}</span></div></div><div class="review-actions">${actions}</div></section>`;
}

function bindReviewActions() {
  document.querySelectorAll("[data-asset-id][data-decision]").forEach((button) => {
    button.addEventListener("click", () => {
      const assetId = button.dataset.assetId;
      const decision = button.dataset.decision;
      reviewDecisions[assetId] = decision;
      addActivity(t("reviewDecision"), `${assetId}: ${statusLabel(decision)}`);
      if (currentPlan) {
        renderReview(currentPlan);
        renderMetrics(currentPlan);
      }
    });
  });
}

function usesGodotEngine(plan) {
  return Boolean(plan?.production_pipeline?.stages?.some((stage) => stage.id === "godot_quick_play"));
}

function renderBuild(plan) {
  const godotIsPrimary = usesGodotEngine(plan);
  const unreal = godotIsPrimary ? null : plan.unreal_plan;
  const godot = godotIsPrimary ? plan.godot_plan : null;
  const blender = plan.blender_plan;
  buildOutput.innerHTML = [
    unreal ? block(t("maps"), list(unreal.maps)) : "",
    unreal ? block(t("classes"), list(unreal.gameplay_classes)) : "",
    unreal ? block(t("folders"), list(unreal.folders)) : "",
    unreal ? block(t("automation"), list(unreal.automation_steps)) : "",
    godot
      ? block(
          t("godot"),
          [list(godot.scenes), list(godot.scripts), list(godot.automation_steps)].join(""),
          true
        )
      : "",
    blender
      ? block(
          t("blender"),
          numbered(
            blender.jobs,
            (job) => `<strong>${escapeHtml(job.asset_name)}</strong><br><span>${escapeHtml(job.purpose)}</span><br><code>${escapeHtml(job.export_path)}</code>`
          ),
          true
        )
      : ""
  ]
    .filter(Boolean)
    .join("");
}

function renderVisuals(plan) {
  const comfy = plan.comfyui_plan;
  const review = plan.creative_review;
  visualsOutput.innerHTML = [
    comfy
      ? block(
          t("jobs"),
          numbered(
            comfy.jobs,
            (job) =>
              `<strong>${escapeHtml(job.job_id)}</strong><br><span>${escapeHtml(job.gameplay_constraint)}</span><br><code>${escapeHtml(job.workflow_template)}</code>`
          ),
          true
        )
      : "",
    comfy ? block(t("rules"), list(comfy.usage_rules), true) : "",
    review ? block(t("creativeReview"), list(review.required_user_decisions), true) : ""
  ]
    .filter(Boolean)
    .join("");
}

function renderQa(plan) {
  const qa = plan.qa_plan;
  qaOutput.innerHTML = qa
    ? [
        block(t("smoke"), list(qa.smoke_tests)),
        block(t("playability"), list(qa.playability_checks)),
        block(t("failure"), list(qa.failure_checks)),
        block(t("packaging"), list(qa.packaging_checks))
      ].join("")
    : "";
}

function renderGdd(plan) {
  const docs = plan.gdd?.markdown_by_locale || {};
  const selected = docs[currentGddLocale] || docs.en || plan.gdd?.markdown || "";
  gddOutput.textContent = selected;
}

function recordCorrection() {
  const notes = correctionNotes.value.trim();
  if (!currentPlan) {
    setStatus("error");
    addActivity(t("correctionRequiresPlan"), t("openPlanningHint"));
    return;
  }
  if (!notes) {
    correctionNotes.focus();
    return;
  }
  correctionEntries = [
    {
      mode: selectedCorrectionMode,
      notes,
      createdAt: new Date().toISOString()
    },
    ...correctionEntries
  ].slice(0, 12);
  correctionNotes.value = "";
  setStatus("ready");
  renderGates(currentPlan);
  addActivity(t("correctionRecorded"), `${modeLabel(selectedCorrectionMode)}: ${notes}`);
}

document.querySelectorAll(".locale-option").forEach((button) => {
  button.addEventListener("click", () => applyLocale(button.dataset.locale));
});

document.querySelectorAll("[data-theme-choice]").forEach((button) => {
  button.addEventListener("click", () => applyTheme(button.dataset.themeChoice));
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`[data-panel="${button.dataset.tab}"]`).classList.add("active");
  });
});

document.querySelectorAll("[data-gdd-locale]").forEach((button) => {
  button.addEventListener("click", () => {
    currentGddLocale = button.dataset.gddLocale;
    document.querySelectorAll("[data-gdd-locale]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    if (currentPlan) renderGdd(currentPlan);
  });
});

document.querySelectorAll("[data-correction-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    selectedCorrectionMode = button.dataset.correctionMode || "gameplay";
    document.querySelectorAll("[data-correction-mode]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    renderManualCorrectionTools();
  });
});

const generateDemoButton = document.querySelector("#generate-demo-button");
const generateConfirmBox = document.querySelector("#generate-confirm");
const generateStagesBox = document.querySelector("#generate-stages");
let generatePollTimer = null;

function buildExecutePayload(confirmed) {
  return {
    plan: currentPlan,
    engine: usesGodotEngine(currentPlan) ? "godot" : "unreal",
    with_assets: !!document.querySelector("#generate-with-assets")?.checked,
    with_visuals: !!document.querySelector("#generate-with-visuals")?.checked,
    confirmed
  };
}

async function postExecute(confirmed) {
  const response = await fetch("/api/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildExecutePayload(confirmed))
  });
  return response.json();
}

function renderGenerateStages(result) {
  const stages = Array.isArray(result?.stages) ? result.stages : [];
  generateStagesBox.innerHTML = stages
    .map((stage) => {
      const state =
        stage.status === "done"
          ? "ready"
          : stage.status === "failed"
          ? "unavailable"
          : "degraded";
      return `<article class="mcp-status-card" data-state="${state}">
        <div class="mcp-status-top"><h4>${stage.name}</h4><span class="mcp-state">${stage.status}</span></div>
        <p>${stage.detail || ""}</p>
      </article>`;
    })
    .join("");
  if (result?.project_dir) {
    generateStagesBox.innerHTML += `<p class="handoff-note">${t("generateArtifact")}: <code>${result.project_dir}</code></p>`;
  }
}

function pollGenerate(jobId) {
  if (generatePollTimer) clearInterval(generatePollTimer);
  generatePollTimer = setInterval(async () => {
    const job = await fetch(`/api/execute/${jobId}`).then((r) => r.json());
    if (job.result) renderGenerateStages(job.result);
    if (job.status !== "running") {
      clearInterval(generatePollTimer);
      generatePollTimer = null;
      generateDemoButton.disabled = false;
      if (job.status === "done") {
        setStatus("ready");
        addActivity(t("generateDone"), job.result?.project_dir || "");
      } else {
        setStatus("error");
        addActivity(t("generateFailed"), job.error || job.status);
      }
    }
  }, 1500);
}

async function startGenerate() {
  generateConfirmBox.hidden = true;
  generateDemoButton.disabled = true;
  setStatus("running");
  addActivity(t("generateRunning"), "");
  const started = await postExecute(true);
  if (started.job_id) {
    pollGenerate(started.job_id);
  } else {
    generateDemoButton.disabled = false;
    setStatus("error");
    addActivity(t("generateFailed"), started.status || "");
  }
}

async function onGenerateClick() {
  if (!currentPlan) {
    addActivity(t("generateRequiresPlan"), t("openPlanningHint"));
    setStatus("error");
    return;
  }
  const preview = await postExecute(false);
  const effects = Array.isArray(preview?.planned_side_effects) ? preview.planned_side_effects : [];
  generateConfirmBox.hidden = false;
  generateConfirmBox.innerHTML = `
    <strong>${t("generateConfirmTitle")}</strong>
    <p>${t("generateConfirmIntro")}</p>
    <ul>${effects.map((e) => `<li>${e}</li>`).join("")}</ul>
    <div class="handoff-actions">
      <button class="primary-action" type="button" id="generate-proceed">${t("generateConfirmProceed")}</button>
      <button class="ghost-action" type="button" id="generate-cancel">${t("generateConfirmCancel")}</button>
    </div>`;
  generateConfirmBox.querySelector("#generate-proceed").addEventListener("click", startGenerate);
  generateConfirmBox.querySelector("#generate-cancel").addEventListener("click", () => {
    generateConfirmBox.hidden = true;
  });
}

generateDemoButton.addEventListener("click", onGenerateClick);

loadHandoffButton.addEventListener("click", () => loadPlanningHandoff());
recordCorrectionButton.addEventListener("click", recordCorrection);
openRecommendedToolButton.addEventListener("click", () => {
  openManualCorrectionTarget(openRecommendedToolButton.dataset.manualTarget || recommendedManualTargetId());
});

manualToolGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-manual-target]");
  if (!button || button.disabled) return;
  openManualCorrectionTarget(button.dataset.manualTarget);
});

document.querySelector("#log-toggle").addEventListener("click", () => {
  activityDrawer.classList.toggle("is-open");
});

window.addEventListener("storage", (event) => {
  if (event.key === HANDOFF_KEY) {
    loadPlanningHandoff({ activityLabel: t("handoffReceived") });
  }
});

window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin) return;
  const data = event.data;
  if (data?.method === "fantasy-agent/planning-handoff" && data.plan?.gameplay_spec) {
    currentHandoff = savePlanningHandoff(data.plan, data.source || "planning-workbench");
    renderHandoffSummary(currentHandoff);
    renderPlan(data.plan, { keepDecisions: true });
    addActivity(t("handoffReceived"), handoffTitle(currentHandoff));
  }
});

renderActivity();
applyTheme(uiTheme);
applyLocale(uiLocale, { silent: true });
loadManualCorrectionTargets();
loadPlanningHandoff({ silent: true });
