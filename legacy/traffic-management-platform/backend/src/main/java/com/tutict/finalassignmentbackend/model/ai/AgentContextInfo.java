package com.tutict.finalassignmentbackend.model.ai;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.tutict.finalassignmentbackend.service.agent.AgentSkillContext;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record AgentContextInfo(
        String operatorLabel,
        String accessScopeLabel,
        boolean authenticated,
        boolean privilegedOperator
) {

    public static AgentContextInfo from(AgentSkillContext context) {
        return new AgentContextInfo(
                context.operatorLabel(),
                context.accessScopeLabel(),
                context.isAuthenticated(),
                context.isPrivilegedOperator()
        );
    }
}
