const HANDOFF_KEY = "fantasy-agent-planning-handoff";

const correctionModeKeys = {
  gameplay: "modeGameplay",
  visuals: "modeVisuals",
  scope: "modeScope",
  import: "modeImport"
};

const i18n = {
  en: {
    productLabel: "Flow console",
    handoffTitle: "Planning handoff",
    handoffEmpty: "No planning handoff found.",
    handoffHint:
      "Planning Workbench owns idea capture. This console reviews the plan and records correction decisions before side effects.",
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
    emptyBody: "Use this console to review handoffs, capture corrections, and confirm side-effect gates.",
    gatesTitle: "Execution gates",
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
    sideEffects: "Side effects",
    dependencies: "Dependencies",
    artifacts: "Artifacts",
    quality: "Quality gates",
    risks: "Risks",
    outputs: "Outputs",
    owner: "Owner",
    tools: "Tools",
    unreal: "Unreal plan",
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
    invalidHandoff: "Invalid planning handoff"
  },
  "zh-CN": {
    productLabel: "流程控制台",
    handoffTitle: "策划交接",
    handoffEmpty: "未找到策划交接。",
    handoffHint: "策划工作台负责玩法输入和方案生成；这里负责检查交接、记录纠偏，并在副作用执行前确认。",
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
    emptyBody: "流程控制台用于检查交接、记录纠偏，并确认 ComfyUI、Blender、Unreal 等执行门禁。",
    gatesTitle: "执行门禁",
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
    sideEffects: "副作用",
    dependencies: "依赖",
    artifacts: "产物",
    quality: "质量门",
    risks: "风险",
    outputs: "产出",
    owner: "负责人",
    tools: "工具",
    unreal: "Unreal 计划",
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
    invalidHandoff: "策划交接无效"
  }
};

function initialLocale() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("locale") || localStorage.getItem("fantasy-agent-web-console-locale");
  if (requested === "zh-CN" || requested === "en") return requested;
  return navigator.language?.startsWith("zh") ? "zh-CN" : "en";
}

let uiLocale = initialLocale();
let currentPlan = null;
let currentHandoff = null;
let currentGddLocale = uiLocale;
let selectedCorrectionMode = "gameplay";
let reviewDecisions = {};
let correctionEntries = [];
let activityEntries = [];

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
  if (currentPlan) {
    renderPlan(currentPlan, { keepDecisions: true });
  } else {
    clearPlanView();
  }
  if (!options.silent) addActivity(t("switchedLocale"), uiLocale);
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
        source: "legacy",
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

function renderBuild(plan) {
  const unreal = plan.unreal_plan;
  const blender = plan.blender_plan;
  buildOutput.innerHTML = [
    unreal ? block(t("maps"), list(unreal.maps)) : "",
    unreal ? block(t("classes"), list(unreal.gameplay_classes)) : "",
    unreal ? block(t("folders"), list(unreal.folders)) : "",
    unreal ? block(t("automation"), list(unreal.automation_steps)) : "",
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
  });
});

loadHandoffButton.addEventListener("click", () => loadPlanningHandoff());
recordCorrectionButton.addEventListener("click", recordCorrection);

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
applyLocale(uiLocale, { silent: true });
loadPlanningHandoff({ silent: true });
