import type { IdeaSeed, InterviewAnswer, WorkbenchConfig } from "../shared/types";
import type { SeedEditorFields } from "./workbenchModel";
const KEY = "fantasy-agent-workbench-conversation-v1";
export interface ConversationDraft {
  chatInput: string; rawIdea: string; answers: InterviewAnswer[]; seed: IdeaSeed | null; seedConfirmed: boolean;
  fields: SeedEditorFields; config: WorkbenchConfig;
}
export function readConversationDraft(): Partial<ConversationDraft> {
  try { const value = JSON.parse(localStorage.getItem(KEY) || "{}"); return value && typeof value === "object" ? value : {}; }
  catch { return {}; }
}
export function saveConversationDraft(draft: ConversationDraft): void {
  try { localStorage.setItem(KEY, JSON.stringify(draft)); } catch { /* The mounted conversation remains available. */ }
}
