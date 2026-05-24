package com.tutict.finalassignmentbackend.service.agent;

import com.tutict.finalassignmentbackend.model.ai.ChatAction;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TrafficCaseSkillTest {

    private final TrafficCaseSkill skill = new TrafficCaseSkill();

    @Test
    void shouldProvideUserSideFineActions() {
        AgentSkillResult result = skill.execute(new AgentSkillContext("我想处理罚款缴费", false));

        assertTrue(result.hasContent());
        assertTrue(result.needConfirm());
        assertTrue(result.summary().contains("罚款缴纳处理"));
        assertEquals(List.of("NAVIGATE", "SHOW_MODAL"), actionTypes(result.actions()));
        assertEquals("/fineInformation", result.actions().getFirst().getTarget());
    }

    @Test
    void shouldRouteManagerAppealIntentToAdminPage() {
        AgentSkillResult result = skill.execute(new AgentSkillContext("管理员要审核申诉记录", false));

        assertTrue(result.hasContent());
        assertEquals("/appealManagement", result.actions().getFirst().getTarget());
        assertTrue(result.highlights().stream().anyMatch(item -> item.contains("申诉管理")));
    }

    @Test
    void shouldRoutePrivilegedUserToAdminPageEvenWithoutManagerKeyword() {
        AgentSkillResult result = skill.execute(new AgentSkillContext(
                "我要查看申诉记录",
                false,
                true,
                "admin",
                99L,
                "Admin",
                "330123199001010099",
                "交警队",
                List.of("ROLE_ADMIN")
        ));

        assertTrue(result.hasContent());
        assertEquals("/appealManagement", result.actions().getFirst().getTarget());
    }

    @Test
    void shouldRouteUserAppealIntentToUserAppealPage() {
        AgentSkillResult result = skill.execute(new AgentSkillContext("我要提交申诉材料", false));

        assertTrue(result.hasContent());
        assertEquals("/userAppeal", result.actions().getFirst().getTarget());
    }

    @Test
    void shouldIgnoreUnrelatedConversation() {
        assertFalse(skill.supports(new AgentSkillContext("今天天气怎么样", false)));
    }

    private List<String> actionTypes(List<ChatAction> actions) {
        return actions.stream().map(ChatAction::getType).toList();
    }
}
