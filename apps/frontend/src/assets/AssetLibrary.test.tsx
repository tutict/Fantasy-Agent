import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AssetLibrary } from "./AssetLibrary";
import { formatBytes, shortSha, statusLabelKey } from "./parts";
import { getAssetLibrary, ingestAsset, removeAsset } from "../shared/api";
import { makeTranslator, studioI18n } from "../shared/i18n";
import type { AssetLibraryOverview } from "../shared/types";

/**
 * The asset library panel.
 *
 * The API layer is mocked rather than fetched: what these tests pin is the
 * panel's own behaviour -- what it renders from a payload, what it posts from
 * the form, and that a destructive action asks first. The endpoint's own
 * contract is proven in `tests/test_asset_library.py` and
 * `tests/test_studio_app.py`; duplicating it here would only test the mock.
 */

vi.mock("../shared/api", () => ({
  getAssetLibrary: vi.fn(),
  ingestAsset: vi.fn(),
  removeAsset: vi.fn()
}));

const t = makeTranslator("zh-CN", studioI18n);

function overview(overrides: Partial<AssetLibraryOverview> = {}): AssetLibraryOverview {
  return {
    entries: [],
    generated: [],
    library_path: "generated/asset-library/library.yaml",
    generated_manifest_path: "generated/asset-approval-manifest.yaml",
    generated_manifest_present: false,
    ...overrides
  };
}

function loadedLibrary() {
  return overview({
    entries: [
      {
        id: "asset-0123456789ab",
        name: "自然包",
        kind: "mesh",
        source: "open_source",
        original_name: "nature.glb",
        path: "generated/asset-library/files/asset-0123456789ab/asset-0123456789ab.glb",
        size_bytes: 2048,
        sha256: "a".repeat(64),
        license: "CC0",
        author: "Kenney",
        source_url: "https://kenney.nl/assets/nature-pack",
        notes: "",
        tags: ["自然", "环境"],
        ingested_at: "2026-10-18T06:00:00+00:00"
      },
      {
        id: "asset-0fedcba98765",
        name: "脚步声音轨",
        kind: "audio",
        source: "open_source",
        original_name: "steps.wav",
        path: "generated/asset-library/files/asset-0fedcba98765/asset-0fedcba98765.wav",
        size_bytes: 512,
        sha256: "b".repeat(64),
        license: "CC-BY",
        author: "",
        source_url: "",
        notes: "",
        tags: [],
        ingested_at: "2026-10-18T06:05:00+00:00"
      }
    ],
    generated: [
      {
        asset_id: "wall_straight",
        source: "blender",
        asset_path: "generated/assets/wall_straight.glb",
        gameplay_role: "route wall",
        status: "approved",
        sha256: "c".repeat(64)
      },
      {
        asset_id: "hero_concept",
        source: "comfyui",
        asset_path: "generated/comfyui/hero_concept.png",
        gameplay_role: "character direction",
        status: "needs_revision",
        sha256: null
      }
    ]
  });
}

beforeEach(() => {
  vi.mocked(getAssetLibrary).mockResolvedValue(overview());
  vi.mocked(ingestAsset).mockResolvedValue({
    status: "ingested",
    entry: {
      id: "asset-aaaaaaaabbbb",
      name: "新资产",
      kind: "other",
      source: "open_source",
      original_name: "thing.bin",
      path: "generated/asset-library/files/asset-aaaaaaaabbbb/asset-aaaaaaaabbbb.bin",
      size_bytes: 10,
      sha256: "d".repeat(64),
      license: "MIT",
      author: "",
      source_url: "",
      notes: "",
      tags: [],
      ingested_at: "2026-10-18T07:00:00+00:00"
    }
  });
  vi.mocked(removeAsset).mockResolvedValue({ status: "removed", removed_id: "asset-0123456789ab" });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function renderPanel() {
  return render(<AssetLibrary t={t} />);
}

/**
 * The article that renders one library entry, found by the name it shows.
 * Waits, because the panel mounts before its first read comes back.
 */
async function entryCard(name: string): Promise<HTMLElement> {
  return (await screen.findByText(name)).closest("article") as HTMLElement;
}

describe("asset library panel", () => {
  it("shows the ingest form and both sections when the library is empty", async () => {
    renderPanel();

    expect(screen.getByText("录入开源资产")).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText("还没有录入任何资产。先在上方添加一个开源资产。")).toBeTruthy();
    });
    expect(screen.getByText("还没有任何审阅决策记录。")).toBeTruthy();
  });

  it("renders ingested entries with their provenance", async () => {
    vi.mocked(getAssetLibrary).mockResolvedValue(loadedLibrary());
    renderPanel();

    expect(await screen.findByText("自然包")).toBeTruthy();
    // The digest is shown short, with the full value on the title attribute.
    expect(screen.getByText(shortSha("a".repeat(64)))).toBeTruthy();
    expect(screen.getByText(formatBytes(2048))).toBeTruthy();
    expect(screen.getByText("CC0")).toBeTruthy();
    expect(screen.getByText("https://kenney.nl/assets/nature-pack")).toBeTruthy();
  });

  it("renders review decisions with their status badges", async () => {
    vi.mocked(getAssetLibrary).mockResolvedValue(loadedLibrary());
    renderPanel();

    expect(await screen.findByText("wall_straight")).toBeTruthy();
    // The status filters say the same words as the badges; the badge is what
    // carries the decision, so the query is scoped to it.
    const approved = screen.getByText("已批准", { selector: ".status-badge" });
    expect(approved.getAttribute("data-status")).toBe("approved");
    expect(
      screen.getByText("待修改", { selector: ".status-badge" }).getAttribute("data-status")
    ).toBe("needs_revision");
  });

  it("filters the library by kind without touching the generated list", async () => {
    vi.mocked(getAssetLibrary).mockResolvedValue(loadedLibrary());
    renderPanel();

    expect(await screen.findByText("自然包")).toBeTruthy();
    // Scoped to the filter group: the audio entry's own kind badge says the
    // same word, and an unscoped query would match both.
    fireEvent.click(within(screen.getByRole("group", { name: "类型" })).getByText("音频"));

    expect(screen.queryByText("自然包")).toBeNull();
    expect(screen.getByText("脚步声音轨")).toBeTruthy();
    // The other section is a different filter and must not move.
    expect(screen.getByText("wall_straight")).toBeTruthy();
  });

  it("filters the generated list by decision", async () => {
    vi.mocked(getAssetLibrary).mockResolvedValue(loadedLibrary());
    renderPanel();

    expect(await screen.findByText("wall_straight")).toBeTruthy();
    fireEvent.click(within(screen.getByRole("group", { name: "状态" })).getByText("待修改"));

    expect(screen.queryByText("wall_straight")).toBeNull();
    expect(screen.getByText("hero_concept")).toBeTruthy();
  });

  it("posts the form and reports what was ingested", async () => {
    renderPanel();

    fireEvent.change(screen.getByLabelText("名称"), { target: { value: "新资产" } });
    fireEvent.change(screen.getByLabelText("本机文件路径"), {
      target: { value: "C:/Users/me/Downloads/thing.bin" }
    });
    fireEvent.change(screen.getByLabelText("标签"), { target: { value: "道具, 测试" } });
    // The submit button reads "ingesting" while the first load is still in
    // flight, so the click waits for that read to come back.
    fireEvent.click(await screen.findByText("录入"));

    await waitFor(() => {
      expect(ingestAsset).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(ingestAsset).mock.calls[0][0]).toMatchObject({
      name: "新资产",
      source_path: "C:/Users/me/Downloads/thing.bin",
      license: "CC0",
      tags: ["道具", "测试"]
    });
    expect(await screen.findByText("已录入 新资产。")).toBeTruthy();
    // The form is reset after a successful ingest, so the next file starts clean.
    expect((screen.getByLabelText("名称") as HTMLInputElement).value).toBe("");
  });

  it("asks before removing, and only then deletes", async () => {
    vi.mocked(getAssetLibrary).mockResolvedValue(loadedLibrary());
    renderPanel();

    // Two entries means two remove buttons; the one that matters belongs to
    // the entry the assertion below names.
    fireEvent.click(within(await entryCard("自然包")).getByText("移除"));

    // The dialog names what happens -- and what does not.
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("移除这个资产？")).toBeTruthy();
    expect(within(dialog).getByText("只会删除库里的副本，你下载的原始文件不受影响。")).toBeTruthy();
    expect(removeAsset).not.toHaveBeenCalled();

    fireEvent.click(within(dialog).getByText("保留"));
    expect(removeAsset).not.toHaveBeenCalled();

    fireEvent.click(within(await entryCard("自然包")).getByText("移除"));
    fireEvent.click(within(screen.getByRole("dialog")).getByText("移除"));
    await waitFor(() => {
      expect(removeAsset).toHaveBeenCalledWith("asset-0123456789ab");
    });
    expect(await screen.findByText("已移除 自然包。")).toBeTruthy();
  });

  it("surfaces a failed load as an error instead of an empty library", async () => {
    vi.mocked(getAssetLibrary).mockRejectedValue(new Error("HTTP 400 审批清单无法读取"));
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(/资产库读取失败/)).toBeTruthy();
    });
    // "Nothing was generated" would be a claim; the panel does not make it.
    expect(screen.queryByText("还没有任何审阅决策记录。")).toBeNull();
  });

  it("names every decision it can render", () => {
    // Literal keys, so the i18n guard's source scan sees them as called.
    expect(statusLabelKey("approved")).toBe("assetsStatusApproved");
    expect(statusLabelKey("needs_revision")).toBe("assetsStatusNeedsRevision");
    expect(statusLabelKey("rejected")).toBe("assetsStatusRejected");
    expect(statusLabelKey("pending_user_review")).toBe("assetsStatusPending");
    expect(statusLabelKey("something_else")).toBe("assetsStatusUnknown");
  });
});
