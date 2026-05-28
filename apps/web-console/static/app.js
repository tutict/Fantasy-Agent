const i18n = {
  en: {
    productLabel: "AI-native production console",
    promptLabel: "Gameplay idea",
    promptPlaceholder: "A stealth courier escapes a haunted train station",
    sessionLabel: "Session",
    engineLabel: "Engine",
    sourceLocale: "Source language",
    outputLocales: "Output languages",
    constraintsLabel: "Constraints",
    constraintsPlaceholder: "One map, no online multiplayer, game jam scope",
    generate: "Generate plan",
    formNote: "The console uses the local Director workflow and does not call external model services.",
    statusLabel: "Plan status",
    emptyTitle: "No plan generated",
    idle: "Idle",
    running: "Generating",
    ready: "Ready",
    failed: "Failed",
    error: "Error",
    tabOverview: "Overview",
    tabTasks: "Tasks",
    tabDsl: "Gameplay DSL",
    tabGdd: "GDD",
    tabBuild: "Build",
    tabVisuals: "Visuals",
    tabQa: "QA",
    emptyHeading: "Generate a vertical slice plan",
    emptyBody: "Enter a gameplay idea to produce structured outputs for design, engine setup, assets, visuals, and QA.",
    pillars: "Design pillars",
    loop: "Core loop",
    systems: "Systems",
    next: "Next actions",
    recommended: "Recommended",
    confirmation: "Confirmation required",
    sideEffects: "Side effects",
    dependencies: "Dependencies",
    artifacts: "Artifacts",
    unreal: "Unreal plan",
    blender: "Blender jobs",
    comfyui: "ComfyUI references",
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
    errorPrefix: "Could not generate plan"
  },
  "zh-CN": {
    productLabel: "AI 原生生产控制台",
    promptLabel: "玩法想法",
    promptPlaceholder: "一名潜行信使逃离闹鬼火车站",
    sessionLabel: "时长",
    engineLabel: "引擎",
    sourceLocale: "输入语言",
    outputLocales: "输出语言",
    constraintsLabel: "约束",
    constraintsPlaceholder: "一张地图，不做联网多人，game jam 规模",
    generate: "生成计划",
    formNote: "控制台使用本地 Director workflow，不调用外部模型服务。",
    statusLabel: "计划状态",
    emptyTitle: "尚未生成计划",
    idle: "空闲",
    running: "生成中",
    ready: "就绪",
    failed: "失败",
    error: "错误",
    tabOverview: "概览",
    tabTasks: "任务",
    tabDsl: "Gameplay DSL",
    tabGdd: "GDD",
    tabBuild: "构建",
    tabVisuals: "视觉",
    tabQa: "QA",
    emptyHeading: "生成垂直切片计划",
    emptyBody: "输入玩法想法，生成设计、引擎搭建、资产、视觉参考和 QA 的结构化输出。",
    pillars: "设计支柱",
    loop: "核心循环",
    systems: "系统",
    next: "下一步",
    recommended: "推荐",
    confirmation: "需要确认",
    sideEffects: "副作用",
    dependencies: "依赖",
    artifacts: "产物",
    unreal: "Unreal 计划",
    blender: "Blender 任务",
    comfyui: "ComfyUI 参考",
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
    errorPrefix: "无法生成计划"
  }
};

let uiLocale = "en";
let currentPlan = null;
let currentGddLocale = "en";

const form = document.querySelector("#plan-form");
const minuteInput = document.querySelector("#target_minutes");
const minuteOutput = document.querySelector("#minute-output");
const statusChip = document.querySelector("#status-chip");
const planTitle = document.querySelector("#plan-title");
const generateButton = document.querySelector("#generate-button");
const overviewContent = document.querySelector("#overview-content");
const emptyState = document.querySelector(".empty-state");
const tasksOutput = document.querySelector("#tasks-output");
const dslOutput = document.querySelector("#dsl-output");
const gddOutput = document.querySelector("#gdd-output");
const buildOutput = document.querySelector("#build-output");
const visualsOutput = document.querySelector("#visuals-output");
const qaOutput = document.querySelector("#qa-output");

function t(key) {
  return i18n[uiLocale][key] || i18n.en[key] || key;
}

function applyLocale(locale) {
  uiLocale = locale;
  document.documentElement.lang = locale;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll(".locale-option").forEach((button) => {
    button.classList.toggle("active", button.dataset.locale === locale);
  });
  if (!currentPlan) {
    statusChip.textContent = t(statusChip.dataset.state === "idle" ? "idle" : statusChip.dataset.state);
    planTitle.textContent = t("emptyTitle");
  } else {
    renderPlan(currentPlan);
  }
}

function setStatus(state) {
  statusChip.dataset.state = state;
  statusChip.textContent = t(state);
}

function list(items) {
  if (!items || !items.length) return "<p>None</p>";
  return `<ul>${items.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("")}</ul>`;
}

function numbered(items, mapper) {
  if (!items || !items.length) return "<p>None</p>";
  return `<ol>${items.map((item, index) => `<li>${mapper(item, index)}</li>`).join("")}</ol>`;
}

function block(title, body, wide = false) {
  return `<section class="summary-block${wide ? " wide" : ""}"><h3>${escapeHtml(title)}</h3>${body}</section>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderPlan(plan) {
  currentPlan = plan;
  const spec = plan.gameplay_spec;
  const preferredTitle =
    uiLocale === "zh-CN" && spec.i18n?.field_translations?.title?.["zh-CN"]
      ? spec.i18n.field_translations.title["zh-CN"]
      : spec.title;
  planTitle.textContent = preferredTitle;
  setStatus("ready");

  emptyState.classList.add("hidden");
  overviewContent.classList.remove("hidden");
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

  dslOutput.textContent = JSON.stringify(spec, null, 2);
  renderGdd(plan);
  renderTasks(plan);
  renderBuild(plan);
  renderVisuals(plan);
  renderQa(plan);
}

function renderGdd(plan) {
  const docs = plan.gdd.markdown_by_locale || {};
  const selected = docs[currentGddLocale] || docs.en || plan.gdd.markdown || "";
  gddOutput.textContent = selected;
}

function localizedTaskTitle(task) {
  return uiLocale === "zh-CN"
    ? task.title_i18n?.["zh-CN"] || task.title
    : task.title_i18n?.en || task.title;
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
          : "",
        task.artifacts?.length
          ? `<span class="task-pill">${escapeHtml(t("artifacts"))}: ${escapeHtml(task.artifacts.length)}</span>`
          : ""
      ]
        .filter(Boolean)
        .join("");
      return `<section class="task-row"><div><h3>${escapeHtml(localizedTaskTitle(task))}</h3><p>${escapeHtml(task.purpose)}</p><div class="task-meta">${detail}</div></div></section>`;
    })
  ].join("");
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
      numbered(blender.jobs, (job) => `<strong>${escapeHtml(job.asset_name)}</strong><br><span>${escapeHtml(job.purpose)}</span>`),
      true
    )
  ].join("");
}

function renderVisuals(plan) {
  const comfy = plan.comfyui_plan;
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
    block(t("rules"), list(comfy.usage_rules), true)
  ].join("");
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
    renderPlan(await response.json());
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

applyLocale("en");
