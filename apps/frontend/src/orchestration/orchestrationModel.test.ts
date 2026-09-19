import { describe, expect, it } from "vitest";

import { studioI18n } from "../shared/i18n";
import type { DirectorBuildPlan, OrchestrationSession } from "../shared/types";
import {
  HUMAN_STAGE_KIND,
  PLAN_STATUSES,
  RUNTIME_STATUSES,
  approvableCards,
  boardCards,
  cardsFromPlan,
  cardsFromSession,
  drilldown,
  humanGates,
  newSessionId,
  reworkableCards,
  statusLabelKey
} from "./orchestrationModel";

/**
 * The board's model, tested without React.
 *
 * The two-source merge is the part worth pinning: before a run the cards come
 * from the handed-off plan, after one from the server's session, and "which
 * source is on screen" decides whether a card's status means anything. That is
 * a question about a function, not about JSX.
 */

function planWith(stages: DirectorBuildPlan["production_pipeline"]): DirectorBuildPlan {
  return { production_pipeline: stages } as DirectorBuildPlan;
}

const PIPELINE = {
  project_name: "neon-rooftops",
  goal: "ship a 10 minute slice",
  current_stage: "godot_quick_play" as const,
  next_stage: "creative_review" as const,
  stages: [
    {
      id: "godot_quick_play" as const,
      order: 2,
      title: "Godot quick play",
      status: "ready" as const,
      purpose: "assemble the greybox",
      owner_agent: "godot" as const,
      kind: "agent" as const,
      depends_on: ["blender_modeling" as const],
      mcp_tools: ["godot-mcp"],
      quality_gates: ["runs at 60fps"],
      risks: ["import blocks the loop"],
      requires_confirmation: true,
      exit_checks: []
    },
    {
      id: "creative_review" as const,
      order: 3,
      title: "Creative review",
      status: "blocked" as const,
      purpose: "a person signs off the look",
      owner_agent: "creative-review-agent" as const,
      kind: "human" as const,
      depends_on: ["godot_quick_play" as const],
      mcp_tools: [],
      quality_gates: [],
      risks: [],
      requires_confirmation: true
    },
    {
      id: "blender_modeling" as const,
      order: 1,
      title: "Blender modelling",
      status: "pending" as const,
      purpose: "cut the hero props",
      owner_agent: "blender-worker" as const,
      kind: "agent" as const,
      requires_confirmation: true
    }
  ]
};

describe("cards from the handed-off plan", () => {
  it("orders by the plan's own order, not by array position", () => {
    expect(cardsFromPlan(planWith(PIPELINE)).map((card) => card.id)).toEqual([
      "blender_modeling",
      "godot_quick_play",
      "creative_review"
    ]);
  });

  it("carries every plan-time field a card draws, including depends_on", () => {
    const card = cardsFromPlan(planWith(PIPELINE)).find((entry) => entry.id === "godot_quick_play")!;

    expect(card.plan_status).toBe("ready");
    expect(card.purpose).toBe("assemble the greybox");
    expect(card.owner_agent).toBe("godot");
    expect(card.depends_on).toEqual(["blender_modeling"]);
    expect(card.mcp_tools).toEqual(["godot-mcp"]);
    expect(card.quality_gates).toEqual(["runs at 60fps"]);
    expect(card.risks).toEqual(["import blocks the loop"]);
    // Before a run there is no runtime status at all, and `pending` is the
    // truthful one: nothing has been reached.
    expect(card.status).toBe("pending");
    expect(card.confirmed).toBe(false);
  });

  it("has no cards for a plan with no pipeline", () => {
    expect(cardsFromPlan(null)).toEqual([]);
    expect(cardsFromPlan({} as DirectorBuildPlan)).toEqual([]);
    expect(cardsFromPlan(planWith({ ...PIPELINE, stages: [] }))).toEqual([]);
  });
});

describe("cards from a run payload", () => {
  const session: OrchestrationSession = {
    session_id: "orch-1",
    status: "error",
    pending_confirmations: ["blender_modeling"],
    confirmed: ["godot_quick_play"],
    stage_translation: { blender_modeling: ["blender"] },
    stages: [
      {
        stage_id: "blender_modeling",
        order: 1,
        title: "Blender modelling",
        kind: "agent",
        plan_status: "pending",
        status: "awaiting_confirmation",
        requires_confirmation: true,
        confirmed: false,
        purpose: "cut the hero props",
        owner_agent: "blender-worker",
        depends_on: [],
        mcp_tools: ["blender-mcp"],
        quality_gates: [],
        risks: [],
        exit_checks: [],
        executor_stages: ["blender"],
        detail: "",
        tools: ["blender-mcp"],
        dispatched: false,
        tool_calls: 0,
        refusals: [],
        checks: [],
        answer: ""
      }
    ]
  };

  it("carries both status vocabularies, kept apart", () => {
    const card = cardsFromSession(session)[0];

    expect(card.plan_status).toBe("pending");
    expect(card.status).toBe("awaiting_confirmation");
  });

  it("prefers the session's cards once it has any", () => {
    const cards = boardCards(planWith(PIPELINE), session);
    expect(cards.map((card) => card.id)).toEqual(["blender_modeling"]);
  });

  it("falls back to the plan when the session has no cards", () => {
    // A session that has not run, or a `GET` for an id the server never saw,
    // answers with an empty stage list. Blanking the board there would hide the
    // plan the operator is about to run.
    expect(boardCards(planWith(PIPELINE), { stages: [] }).map((card) => card.id)).toEqual([
      "blender_modeling",
      "godot_quick_play",
      "creative_review"
    ]);
    expect(boardCards(planWith(PIPELINE), null).length).toBe(3);
  });
});

describe("what gets a button", () => {
  const cards = cardsFromPlan(planWith(PIPELINE));

  it("names the human gate and never offers to approve it", () => {
    expect(humanGates(cards).map((card) => card.id)).toEqual(["creative_review"]);
    // Approving a gate does not make it run -- the orchestrator leaves these
    // out of `pending_confirmations` for the same reason -- so an approve
    // button here would be a control that does nothing.
    expect(approvableCards(cards).map((card) => card.id)).toEqual([
      "blender_modeling",
      "godot_quick_play"
    ]);
  });

  it("drops a stage once it has been approved", () => {
    const confirmed = cards.map((card) =>
      card.id === "godot_quick_play" ? { ...card, confirmed: true } : card
    );
    expect(approvableCards(confirmed).map((card) => card.id)).toEqual(["blender_modeling"]);
  });

  it("offers rework only on a card a pass has reached", () => {
    expect(reworkableCards(cards)).toEqual([]);

    const afterARun = cards.map((card) =>
      card.id === "blender_modeling" ? { ...card, status: "failed" } : card
    );
    expect(reworkableCards(afterARun).map((card) => card.id)).toEqual(["blender_modeling"]);
  });
});

describe("drill-down", () => {
  const card = cardsFromSession({
    stages: [{ stage_id: "blender_modeling", order: 1, executor_stages: ["blender"], status: "done" }]
  })[0];

  it("reads the route's table, which is there before anything runs", () => {
    expect(drilldown(card, { blender_modeling: ["blender", "validate"] })).toEqual([
      "blender",
      "validate"
    ]);
  });

  it("falls back to the list the card carried when the table has no entry", () => {
    expect(drilldown(card, {})).toEqual(["blender"]);
  });
});

describe("status labels", () => {
  it("has a label for every status the orchestrator can write", () => {
    const missing = RUNTIME_STATUSES.filter((status) => !statusLabelKey(status));
    expect(missing, "runtime statuses with no label key").toEqual([]);
  });

  it("spells the label keys out as literals the i18n guard can see", () => {
    // `t(statusLabelKey(x))` is a variable call, so the keys would look like
    // orphans -- the i18n guard reads bare quoted strings, which is why the
    // table holds literal key names rather than building them from the status.
    for (const status of RUNTIME_STATUSES) {
      const key = statusLabelKey(status);
      expect(key.startsWith("orchestrationStatus"), key).toBe(true);
    }
  });

  it("defines every one of those labels in both locales", () => {
    const keys = RUNTIME_STATUSES.map(statusLabelKey);
    for (const locale of ["en", "zh-CN"] as const) {
      const dictionary = studioI18n[locale];
      const missing = keys.filter((key) => !dictionary[key]);
      expect(missing, `${locale} has no label for these statuses`).toEqual([]);
    }
  });

  it("returns nothing for a status it does not know", () => {
    // The board falls back to the raw string. Inventing a key would render a
    // literal `orchestrationStatusWhatever` into the card.
    expect(statusLabelKey("invented")).toBe("");
    expect(statusLabelKey("")).toBe("");
  });

  it("keeps the plan vocabulary a subset of the runtime one", () => {
    // Every `ProductionTaskStatus` name also exists at runtime and means
    // something else there -- that overlap is why the two lists are separate
    // and the labels are shared.
    const unknown = PLAN_STATUSES.filter(
      (status) => !(RUNTIME_STATUSES as readonly string[]).includes(status)
    );
    expect(unknown).toEqual([]);
  });
});

describe("session ids", () => {
  it("are distinct, so two boards do not share outcomes", () => {
    const ids = new Set(Array.from({ length: 50 }, () => newSessionId()));
    expect(ids.size).toBe(50);
  });

  it("are safe to put in a URL path", () => {
    expect(newSessionId()).toMatch(/^orch-[a-z0-9]+-[a-z0-9]+$/);
  });
});

describe("the human gate constant", () => {
  it("matches the backend's `ProductionStageKind`", () => {
    expect(HUMAN_STAGE_KIND).toBe("human");
  });
});
