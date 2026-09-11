import { describe, expect, it } from "vitest";

import {
  MAX_TARGET_MINUTES,
  MIN_TARGET_MINUTES,
  appendInterviewAnswer,
  canConfirmSeed,
  canGenerate,
  clampTargetMinutes,
  currentInterviewQuestion,
  defaultConfig,
  EMPTY_SEED_FIELDS,
  ideaDiscoveryPayload,
  inferredLoop,
  interviewQuestions,
  isInterviewComplete,
  joinLines,
  localizedTitle,
  normalizeToolResult,
  planDisplayTitle,
  promptRequestFromEditor,
  requestPayload,
  resultPanel,
  seedFromEditor,
  splitLines,
  usesGodotEngine,
  type SeedEditorFields
} from "./workbenchModel";

const config = { ...defaultConfig(), targetMinutes: 12, engineVersion: "Godot 4" };

function fields(patch: Partial<SeedEditorFields> = {}): SeedEditorFields {
  return { ...EMPTY_SEED_FIELDS, ...patch };
}

describe("splitLines / joinLines", () => {
  it("splits on newline, comma and both semicolon widths", () => {
    expect(splitLines("a\nb，c; d；e")).toEqual(["a", "b", "c", "d", "e"]);
  });

  it("drops empty entries and survives null", () => {
    expect(splitLines("a,,,\n\n b")).toEqual(["a", "b"]);
    expect(splitLines(null)).toEqual([]);
    expect(joinLines(["a", "b"])).toBe("a\nb");
    expect(joinLines(undefined)).toBe("");
  });
});

describe("interview state machine", () => {
  it("asks six questions in both locales", () => {
    expect(interviewQuestions("en")).toHaveLength(6);
    expect(interviewQuestions("zh-CN")).toHaveLength(6);
    expect(interviewQuestions("en").map((q) => q.id)).toEqual(
      interviewQuestions("zh-CN").map((q) => q.id)
    );
  });

  it("advances one question per answer and completes after six", () => {
    let collected: Array<{ question_id: string; question: string; answer: string }> = [];
    for (let index = 0; index < 6; index += 1) {
      const question = currentInterviewQuestion(collected, "en");
      expect(question).not.toBeNull();
      collected = appendInterviewAnswer(collected, question, `answer ${index}`, "en");
    }
    expect(isInterviewComplete(collected, "en")).toBe(true);
    expect(currentInterviewQuestion(collected, "en")).toBeNull();
  });

  it("tags answers beyond the scripted six as extra_context and caps the list", () => {
    let collected: Array<{ question_id: string; question: string; answer: string }> = [];
    for (let index = 0; index < 14; index += 1) {
      collected = appendInterviewAnswer(collected, null, `a${index}`, "en");
    }
    expect(collected).toHaveLength(10);
    expect(collected.every((entry) => entry.question_id === "extra_context")).toBe(true);
  });

  it("ignores blank answers", () => {
    expect(appendInterviewAnswer([], null, "   ", "en")).toEqual([]);
  });
});

describe("clampTargetMinutes", () => {
  it("keeps values inside the backend's 5..15 range", () => {
    expect(clampTargetMinutes(1)).toBe(MIN_TARGET_MINUTES);
    expect(clampTargetMinutes(99)).toBe(MAX_TARGET_MINUTES);
    expect(clampTargetMinutes("9")).toBe(9);
    expect(clampTargetMinutes(undefined)).toBe(10);
    expect(clampTargetMinutes("nonsense")).toBe(10);
  });
});

describe("seedFromEditor", () => {
  const filled = fields({
    rawIdea: "a rooftop parkour demo",
    playerFantasy: "a courier who never touches the ground",
    coreAction: "wall-run",
    tensionSource: "timed collapse",
    emotionalTarget: "mastery"
  });

  it("carries the edited fields into the seed", () => {
    const seed = seedFromEditor(filled, config);
    expect(seed.player_fantasy).toBe("a courier who never touches the ground");
    expect(seed.core_action).toBe("wall-run");
    expect(seed.tension_source).toBe("timed collapse");
    expect(seed.raw_idea).toBe("a rooftop parkour demo");
    expect(seed.source).toBe("idea-discovery-agent");
  });

  it("mints a next_prompt that mentions the minutes and engine", () => {
    const seed = seedFromEditor(filled, config);
    expect(seed.next_prompt).toContain("12-minute");
    expect(seed.next_prompt).toContain("Godot 4");
    expect(seed.next_prompt).toContain("wall-run");
  });

  it("falls back to an inferred loop and default cut list", () => {
    const seed = seedFromEditor(filled, config);
    expect(seed.playable_loop_candidate).toContain("courier");
    expect(seed.can_cut).toEqual(["large open world", "AAA art polish", "online multiplayer"]);
    expect(seed.reference_feel).toContain("greybox");
  });

  it("derives must_keep from the core action when left blank", () => {
    const seed = seedFromEditor(fields({ coreAction: "wall-run" }), config);
    expect(seed.must_keep).toEqual(["wall-run"]);
  });

  it("keeps server-side fields that the editor does not own", () => {
    const seed = seedFromEditor(filled, config, { open_questions: ["still unsure?"] });
    expect(seed.open_questions).toEqual(["still unsure?"]);
  });
});

describe("payload construction", () => {
  const filled = fields({
    rawIdea: "rooftop parkour with wall runs",
    playerFantasy: "courier",
    coreAction: "wall-run",
    tensionSource: "collapse"
  });

  it("uses the seed prompt only once the seed is confirmed", () => {
    const seed = seedFromEditor(filled, config);
    const confirmed = requestPayload(filled, config, seed, true);
    expect(confirmed.prompt).toBe(seed.next_prompt);

    const unconfirmed = requestPayload(filled, config, seed, false);
    expect(unconfirmed.prompt).toBe("rooftop parkour with wall runs");
  });

  it("carries configuration into the request", () => {
    const seed = seedFromEditor(filled, config);
    const request = promptRequestFromEditor(seed, config);
    expect(request.target_minutes).toBe(12);
    expect(request.engine_version).toBe("Godot 4");
    expect(request.platforms).toEqual(["Windows"]);
    expect(request.jam_scope).toBe(true);
    expect(request.output_locales).toEqual(["en", "zh-CN"]);
  });

  it("wraps a request with the interview answers for extraction", () => {
    const seed = seedFromEditor(filled, config);
    const request = promptRequestFromEditor(seed, config);
    const answers = appendInterviewAnswer([], interviewQuestions("en")[0], "a courier", "en");
    const payload = ideaDiscoveryPayload(request, "rooftop parkour", answers);
    expect(payload.raw_idea).toBe("rooftop parkour");
    expect(payload.answers).toHaveLength(1);
    expect(payload.answers?.[0].question_id).toBe("player_fantasy");
  });
});

describe("gates", () => {
  it("requires the three core fields before a seed can be confirmed", () => {
    expect(canConfirmSeed(fields({ playerFantasy: "a", coreAction: "b", tensionSource: "c" }))).toBe(true);
    expect(canConfirmSeed(fields({ playerFantasy: "a", coreAction: "b" }))).toBe(false);
  });

  it("requires a confirmed seed before any plan tool may run", () => {
    const seed = seedFromEditor(fields({ coreAction: "wall-run" }), config);
    expect(canGenerate(seed, true)).toBe(true);
    expect(canGenerate(seed, false)).toBe(false);
    expect(canGenerate(null, true)).toBe(false);
  });
});

describe("normalizeToolResult", () => {
  it("reads the flat REST envelope", () => {
    const result = normalizeToolResult({
      structuredContent: { kind: "gdd_document", gdd: { markdown: "# hi" } },
      content: [{ type: "text", text: "Rendered GDD" }],
      _meta: { toolName: "render_gdd", activePanel: "gdd" }
    });
    expect(result.toolName).toBe("render_gdd");
    expect(result.structured.gdd?.markdown).toBe("# hi");
    expect(result.text).toBe("Rendered GDD");
  });

  it("also reads an envelope wrapped under result", () => {
    const result = normalizeToolResult({
      result: {
        structuredContent: { kind: "qa_plan", qa_plan: { smoke_tests: ["boot"] } },
        _meta: { toolName: "prepare_qa_plan" }
      }
    });
    expect(result.structured.qa_plan?.smoke_tests).toEqual(["boot"]);
  });

  it("survives null", () => {
    expect(normalizeToolResult(null).structured).toEqual({});
  });
});

describe("resultPanel", () => {
  it("prefers the panel the backend asked for", () => {
    expect(resultPanel("prepare_qa_plan", { activePanel: "gdd" })).toBe("gdd");
  });

  it("falls back per tool when the backend says nothing", () => {
    expect(resultPanel("render_gdd", {})).toBe("gdd");
    expect(resultPanel("prepare_godot_plan", {})).toBe("build");
    expect(resultPanel("prepare_comfyui_plan", {})).toBe("visuals");
    expect(resultPanel("decompose_production_tasks", {})).toBe("tasks");
  });
});

describe("localized helpers", () => {
  it("prefers the locale title then the plain title", () => {
    expect(
      localizedTitle({ title: "Fallback", title_i18n: { "zh-CN": "中文", en: "English" } }, "zh-CN")
    ).toBe("中文");
    expect(localizedTitle({ title: "Fallback" }, "zh-CN")).toBe("Fallback");
    expect(localizedTitle(undefined, "en")).toBe("");
  });

  it("reads the translated plan title when present", () => {
    const plan = {
      gameplay_spec: {
        title: "Neon Rooftops",
        i18n: { field_translations: { title: { "zh-CN": "霓虹屋顶" } } }
      }
    };
    expect(planDisplayTitle(plan, "zh-CN")).toBe("霓虹屋顶");
    expect(planDisplayTitle(plan, "en")).toBe("Neon Rooftops");
    expect(planDisplayTitle(null, "en")).toBe("");
  });

  it("detects a godot pipeline from its stage ids", () => {
    expect(usesGodotEngine({ production_pipeline: { stages: [{ id: "godot_quick_play" }] } })).toBe(
      true
    );
    expect(usesGodotEngine({ production_pipeline: { stages: [{ id: "unreal_ingest" }] } })).toBe(
      false
    );
    expect(usesGodotEngine(null)).toBe(false);
  });
});

describe("inferredLoop", () => {
  it("fills every blank with a readable placeholder", () => {
    expect(inferredLoop("", "", "", "")).toContain("the player fantasy");
  });
});
