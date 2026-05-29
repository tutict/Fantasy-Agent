const i18n = {
  en: {
    productLabel: "Production cockpit",
    promptLabel: "Gameplay idea",
    promptPlaceholder: "A rooftop parkour demo with wall-runs, vaults, slides, boost pads, and checkpoints",
    sessionLabel: "Session",
    engineLabel: "Engine",
    sourceLocale: "Source language",
    outputLocales: "Output languages",
    constraintsLabel: "Constraints",
    constraintsPlaceholder: "One map, no online multiplayer, game jam scope",
    generate: "Generate production plan",
    statusLabel: "Plan status",
    emptyTitle: "No plan generated",
    idle: "Idle",
    running: "Generating",
    ready: "Ready",
    error: "Error",
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
    emptyHeading: "Generate a vertical slice plan",
    emptyBody: "Enter a gameplay idea to produce design, asset, review, Unreal, and QA handoffs.",
    gatesTitle: "Side-effect gates",
    defaultGateVisuals: "ComfyUI generation",
    defaultGateMeshes: "Blender generation",
    defaultGateUnreal: "Unreal execution",
    waitingForPlan: "Waiting for a plan",
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
    generatedPlan: "Generated plan",
    switchedLocale: "Switched locale",
    reviewDecision: "Review decision",
    noItems: "No items",
    errorPrefix: "Could not generate plan"
  },
  "zh-CN": {
    productLabel: "生产驾驶舱",
    promptLabel: "玩法想法",
    promptPlaceholder: "一个包含蹬墙跑、翻越、滑铲、加速板和检查点的屋顶跑酷 demo",
    sessionLabel: "时长",
    engineLabel: "引擎",
    sourceLocale: "输入语言",
    outputLocales: "输出语言",
    constraintsLabel: "约束",
    constraintsPlaceholder: "一张地图，不做联网多人，game jam 规模",
    generate: "生成生产计划",
    statusLabel: "计划状态",
    emptyTitle: "尚未生成计划",
    idle: "空闲",
    running: "生成中",
    ready: "就绪",
    error: "错误",
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
    emptyHeading: "生成垂直切片计划",
    emptyBody: "输入玩法想法，生成设计、资产、审阅、Unreal 和 QA 交接。",
    gatesTitle: "副作用确认",
    defaultGateVisuals: "ComfyUI 生成",
    defaultGateMeshes: "Blender 生成",
    defaultGateUnreal: "Unreal 执行",
    waitingForPlan: "等待计划",
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
    generatedPlan: "已生成计划",
    switchedLocale: "已切换语言",
    reviewDecision: "审阅决定",
    noItems: "无项目",
    errorPrefix: "无法生成计划"
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
let currentGddLocale = uiLocale;
let reviewDecisions = {};
let activityEntries = [];

const form = document.querySelector("#plan-form");
const minuteInput = document.querySelector("#target_minutes");
const minuteOutput = document.querySelector("#minute-output");
const statusChip = document.querySelector("#status-chip");
const planTitle = document.querySelector("#plan-title");
const generateButton = document.querySelector("#generate-button");
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

function applyLocale(locale) {
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
  if (!currentPlan) {
    setStatus(statusChip.dataset.state || "idle");
    planTitle.textContent = t("emptyTitle");
    renderDefaultGates();
  } else {
    renderPlan(currentPlan, { keepDecisions: true });
  }
  addActivity(t("switchedLocale"), uiLocale);
}

function setStatus(state) {
  statusChip.dataset.state = state;
  statusChip.textContent = t(state);
}

function preferredTitle(spec) {
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
  gateSummary.innerHTML = gated.length
    ? gated.map((task) => gateItem(localizedTaskTitle(task), task.side_effects?.join(", ") || task.status)).join("")
    : gateItem(t("confirmation"), t("noItems"));
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
        (step) =>
          `<strong>${escapeHtml(step.action)}</strong><br><span>${escapeHtml(step.player_decision)}</span>`
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
    ...pipeline.stages.map((stage) => {
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
    ...breakdown.tasks.map((task) => {
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
    block(t("maps"), list(unreal.maps)),
    block(t("classes"), list(unreal.gameplay_classes)),
    block(t("folders"), list(unreal.folders)),
    block(t("automation"), list(unreal.automation_steps)),
    block(
      t("blender"),
      numbered(
        blender.jobs,
        (job) => `<strong>${escapeHtml(job.asset_name)}</strong><br><span>${escapeHtml(job.purpose)}</span><br><code>${escapeHtml(job.export_path)}</code>`
      ),
      true
    )
  ].join("");
}

function renderVisuals(plan) {
  const comfy = plan.comfyui_plan;
  const review = plan.creative_review;
  visualsOutput.innerHTML = [
    block(
      t("jobs"),
      numbered(
        comfy.jobs,
        (job) =>
          `<strong>${escapeHtml(job.job_id)}</strong><br><span>${escapeHtml(job.gameplay_constraint)}</span><br><code>${escapeHtml(job.workflow_template)}</code>`
      ),
      true
    ),
    block(t("rules"), list(comfy.usage_rules), true),
    review ? block(t("creativeReview"), list(review.required_user_decisions), true) : ""
  ]
    .filter(Boolean)
    .join("");
}

function renderQa(plan) {
  const qa = plan.qa_plan;
  qaOutput.innerHTML = [
    block(t("smoke"), list(qa.smoke_tests)),
    block(t("playability"), list(qa.playability_checks)),
    block(t("failure"), list(qa.failure_checks)),
    block(t("packaging"), list(qa.packaging_checks))
  ].join("");
}

function renderGdd(plan) {
  const docs = plan.gdd.markdown_by_locale || {};
  const selected = docs[currentGddLocale] || docs.en || plan.gdd.markdown || "";
  gddOutput.textContent = selected;
}

function readPayload() {
  const formData = new FormData(form);
  const outputLocales = formData.getAll("output_locales");
  const constraints = String(formData.get("constraints") || "")
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
  return {
    prompt: String(formData.get("prompt") || "").trim(),
    target_minutes: Number(formData.get("target_minutes") || 10),
    engine_version: String(formData.get("engine_version") || "UE5").trim() || "UE5",
    source_locale: String(formData.get("source_locale") || "en"),
    output_locales: outputLocales.length ? outputLocales : ["en", "zh-CN"],
    platforms: ["Windows"],
    jam_scope: true,
    constraints
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("running");
  generateButton.disabled = true;
  try {
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readPayload())
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const plan = await response.json();
    renderPlan(plan);
    addActivity(t("generatedPlan"), preferredTitle(plan.gameplay_spec));
  } catch (error) {
    setStatus("error");
    planTitle.textContent = `${t("errorPrefix")}: ${error.message}`;
  } finally {
    generateButton.disabled = false;
  }
});

minuteInput.addEventListener("input", () => {
  minuteOutput.textContent = minuteInput.value;
});

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

document.querySelector("#log-toggle").addEventListener("click", () => {
  activityDrawer.classList.toggle("is-open");
});

renderDefaultGates();
renderActivity();
applyLocale(uiLocale);
