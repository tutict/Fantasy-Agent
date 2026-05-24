package com.tutict.finalassignmentbackend.service.agent;

import com.tutict.finalassignmentbackend.model.ai.ChatAction;

import java.util.List;

public record AgentSkillResult(
        String skillId,
        String summary,
        List<String> highlights,
        List<String> searchResults,
        List<ChatAction> actions,
        boolean needConfirm
) {

    public AgentSkillResult {
        summary = summary == null ? "" : summary;
        highlights = highlights == null ? List.of() : List.copyOf(highlights);
        searchResults = searchResults == null ? List.of() : List.copyOf(searchResults);
        actions = actions == null ? List.of() : List.copyOf(actions);
    }

    public static AgentSkillResult empty(String skillId) {
        return new AgentSkillResult(skillId, "", List.of(), List.of(), List.of(), false);
    }

    public boolean hasContent() {
        return !summary.isBlank() || !highlights.isEmpty() || !searchResults.isEmpty() || !actions.isEmpty();
    }
}
