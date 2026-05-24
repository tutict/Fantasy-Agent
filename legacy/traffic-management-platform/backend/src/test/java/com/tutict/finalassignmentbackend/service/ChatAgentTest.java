package com.tutict.finalassignmentbackend.service;

import com.tutict.finalassignmentbackend.model.ai.AgentEvent;
import com.tutict.finalassignmentbackend.model.ai.ChatActionResponse;
import com.tutict.finalassignmentbackend.service.agent.AgentSkill;
import com.tutict.finalassignmentbackend.service.agent.AgentSkillContext;
import com.tutict.finalassignmentbackend.service.agent.AgentSkillResult;
import com.tutict.finalassignmentbackend.service.agent.AgentUserContextResolver;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

class ChatAgentTest {

    private static final AgentSkillContext TEST_CONTEXT = new AgentSkillContext(
            "查询我的违法记录",
            false,
            true,
            "user01",
            1L,
            "Test User",
            "330123199001010011",
            "群众",
            List.of()
    );

    @Test
    void shouldCaptureResolvedContextBeforeAsyncStreaming() {
        AgentUserContextResolver resolver = Mockito.mock(AgentUserContextResolver.class);
        when(resolver.resolve("查询我的违法记录", false)).thenReturn(TEST_CONTEXT);

        AgentSkill skill = new AgentSkill() {
            @Override
            public String id() {
                return "test-skill";
            }

            @Override
            public String displayName() {
                return "Test Skill";
            }

            @Override
            public String description() {
                return "Test";
            }

            @Override
            public AgentSkillResult execute(AgentSkillContext skillContext) {
                return new AgentSkillResult(
                        id(),
                        "captured-user=" + skillContext.username(),
                        List.of("先核对违法时间与地点"),
                        List.of(),
                        List.of(),
                        false
                );
            }
        };

        ChatAgent chatAgent = new ChatAgent(List.of(skill), resolver);

        var flux = chatAgent.streamChatEvents("查询我的违法记录", null, false);
        verify(resolver).resolve("查询我的违法记录", false);

        List<AgentEvent> events = flux.collectList().block(Duration.ofSeconds(5));
        verifyNoMoreInteractions(resolver);

        AgentEvent contextEvent = events.stream()
                .filter(event -> "context".equals(event.type()))
                .findFirst()
                .orElse(null);
        assertNotNull(contextEvent);
        assertNotNull(contextEvent.agentContext());
        assertTrue(contextEvent.agentContext().operatorLabel().contains("Test User(user01)"));
        assertTrue(contextEvent.agentContext().accessScopeLabel().contains("本人名下"));

        AgentEvent firstStatus = events.stream()
                .filter(event -> "status".equals(event.type()))
                .findFirst()
                .orElse(null);
        assertNotNull(firstStatus);
        assertTrue(firstStatus.content().contains("正在分析问题并规划技能执行"));

        String combinedMessages = events.stream()
                .filter(event -> "message".equals(event.type()))
                .map(AgentEvent::content)
                .reduce("", String::concat);

        assertTrue(combinedMessages.contains("核心判断"));
        assertTrue(combinedMessages.contains("建议步骤"));
        assertTrue(combinedMessages.contains("captured-user=user01"));
        assertTrue(combinedMessages.contains("先核对违法时间与地点"));
    }

    @Test
    void shouldIgnoreTimedOutSkillAndKeepFastResult() {
        AgentUserContextResolver resolver = Mockito.mock(AgentUserContextResolver.class);
        when(resolver.resolve("查询我的违法记录", false)).thenReturn(TEST_CONTEXT);

        AgentSkill slowSkill = new AgentSkill() {
            @Override
            public String id() {
                return "slow-skill";
            }

            @Override
            public String displayName() {
                return "Slow Skill";
            }

            @Override
            public String description() {
                return "Slow";
            }

            @Override
            public AgentSkillResult execute(AgentSkillContext skillContext) {
                try {
                    Thread.sleep(200);
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
                return new AgentSkillResult(id(), "slow-summary", List.of("slow-highlight"), List.of(), List.of(), false);
            }
        };

        AgentSkill fastSkill = new AgentSkill() {
            @Override
            public String id() {
                return "fast-skill";
            }

            @Override
            public String displayName() {
                return "Fast Skill";
            }

            @Override
            public String description() {
                return "Fast";
            }

            @Override
            public AgentSkillResult execute(AgentSkillContext skillContext) {
                return new AgentSkillResult(id(), "fast-summary", List.of("fast-highlight"), List.of(), List.of(), false);
            }
        };

        ChatAgent chatAgent = new ChatAgent(List.of(slowSkill, fastSkill), resolver, 4, Duration.ofMillis(50));

        ChatActionResponse response = chatAgent.chatWithActions("查询我的违法记录", null, false);

        assertTrue(response.getAnswer().contains("fast-summary"));
        assertTrue(response.getAnswer().contains("fast-highlight"));
        assertFalse(response.getAnswer().contains("slow-summary"));
        assertFalse(response.isNeedConfirm());
        assertNotNull(response.getAgentContext());
    }

    @Test
    void shouldReturnBusyFallbackWhenConcurrencyLimitReached() throws Exception {
        AgentUserContextResolver resolver = Mockito.mock(AgentUserContextResolver.class);
        when(resolver.resolve("查询我的违法记录", false)).thenReturn(TEST_CONTEXT);

        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);

        AgentSkill blockingSkill = new AgentSkill() {
            @Override
            public String id() {
                return "blocking-skill";
            }

            @Override
            public String displayName() {
                return "Blocking Skill";
            }

            @Override
            public String description() {
                return "Blocking";
            }

            @Override
            public AgentSkillResult execute(AgentSkillContext skillContext) {
                started.countDown();
                try {
                    if (!release.await(5, TimeUnit.SECONDS)) {
                        throw new IllegalStateException("timed out waiting for test release");
                    }
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
                return new AgentSkillResult(id(), "blocking-summary", List.of(), List.of(), List.of(), false);
            }
        };

        ChatAgent chatAgent = new ChatAgent(List.of(blockingSkill), resolver, 1, Duration.ofSeconds(2));

        CompletableFuture<ChatActionResponse> firstConversation = CompletableFuture.supplyAsync(
                () -> chatAgent.chatWithActions("查询我的违法记录", null, false)
        );

        assertTrue(started.await(1, TimeUnit.SECONDS));

        ChatActionResponse busyResponse = chatAgent.chatWithActions("查询我的违法记录", null, false);

        assertTrue(busyResponse.getAnswer().contains("请稍后再试"));
        assertFalse(busyResponse.isNeedConfirm());
        assertNotNull(busyResponse.getAgentContext());

        release.countDown();
        ChatActionResponse firstResponse = firstConversation.get(5, TimeUnit.SECONDS);
        assertTrue(firstResponse.getAnswer().contains("blocking-summary"));
    }
}
