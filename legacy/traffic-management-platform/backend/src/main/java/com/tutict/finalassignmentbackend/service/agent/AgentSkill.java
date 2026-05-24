package com.tutict.finalassignmentbackend.service.agent;

public interface AgentSkill {

    String id();

    String displayName();

    String description();

    default boolean supports(AgentSkillContext context) {
        return true;
    }

    AgentSkillResult execute(AgentSkillContext context);
}
