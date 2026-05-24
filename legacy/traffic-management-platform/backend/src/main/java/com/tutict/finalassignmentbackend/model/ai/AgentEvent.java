package com.tutict.finalassignmentbackend.model.ai;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record AgentEvent(
        String type,
        String content,
        List<String> searchResults,
        List<ChatAction> actions,
        AgentContextInfo agentContext
) {

    public AgentEvent {
        searchResults = searchResults == null ? null : List.copyOf(searchResults);
        actions = actions == null ? null : List.copyOf(actions);
    }

    public static AgentEvent status(String content) {
        return new AgentEvent("status", content, null, null, null);
    }

    public static AgentEvent message(String content) {
        return new AgentEvent("message", content, null, null, null);
    }

    public static AgentEvent search(String result) {
        return new AgentEvent("search", null, List.of(result), null, null);
    }

    public static AgentEvent actions(List<ChatAction> actions) {
        return new AgentEvent("actions", null, null, actions, null);
    }

    public static AgentEvent context(AgentContextInfo agentContext) {
        return new AgentEvent("context", null, null, null, agentContext);
    }

    public static AgentEvent error(String content) {
        return new AgentEvent("error", content, null, null, null);
    }

    public static AgentEvent complete() {
        return new AgentEvent("complete", null, null, null, null);
    }
}
