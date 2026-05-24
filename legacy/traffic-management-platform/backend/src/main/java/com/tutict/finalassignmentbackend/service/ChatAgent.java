package com.tutict.finalassignmentbackend.service;

import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.model.ai.AgentContextInfo;
import com.tutict.finalassignmentbackend.model.ai.AgentEvent;
import com.tutict.finalassignmentbackend.model.ai.AgentSkillInfo;
import com.tutict.finalassignmentbackend.model.ai.ChatAction;
import com.tutict.finalassignmentbackend.model.ai.ChatActionResponse;
import com.tutict.finalassignmentbackend.service.agent.AgentSkill;
import com.tutict.finalassignmentbackend.service.agent.AgentSkillContext;
import com.tutict.finalassignmentbackend.service.agent.AgentSkillResult;
import com.tutict.finalassignmentbackend.service.agent.AgentUserContextResolver;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.FluxSink;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.concurrent.CancellationException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Service
public class ChatAgent {

    private static final Logger logger = LoggerFactory.getLogger(ChatAgent.class);
    private static final int DEFAULT_MAX_CONCURRENT = 16;
    private static final Duration DEFAULT_SKILL_TIMEOUT = Duration.ofSeconds(8);
    private static final String ANALYZING_STATUS = "正在分析问题并规划技能执行。";
    private static final String BUSY_STATUS = "当前 AI 会话较多，正在保护服务稳定性。";
    private static final String BUSY_ANSWER = "当前请求较多，我暂时没有接入新的会话。请稍后再试。";

    private final List<AgentSkill> skills;
    private final AgentUserContextResolver agentUserContextResolver;
    private final ExecutorService agentExecutor;
    private final Semaphore conversationLimiter;
    private final Duration skillTimeout;
    private final int maxConcurrentConversations;

    @Autowired
    public ChatAgent(
            List<AgentSkill> skills,
            AgentUserContextResolver agentUserContextResolver,
            @Value("${app.ai.chat.max-concurrent:16}") int maxConcurrentConversations,
            @Value("${app.ai.chat.skill-timeout-seconds:8}") long skillTimeoutSeconds
    ) {
        this(
                skills,
                agentUserContextResolver,
                maxConcurrentConversations,
                Duration.ofSeconds(skillTimeoutSeconds),
                Executors.newVirtualThreadPerTaskExecutor()
        );
    }

    ChatAgent(List<AgentSkill> skills, AgentUserContextResolver agentUserContextResolver) {
        this(
                skills,
                agentUserContextResolver,
                DEFAULT_MAX_CONCURRENT,
                DEFAULT_SKILL_TIMEOUT,
                Executors.newVirtualThreadPerTaskExecutor()
        );
    }

    ChatAgent(
            List<AgentSkill> skills,
            AgentUserContextResolver agentUserContextResolver,
            int maxConcurrentConversations,
            Duration skillTimeout
    ) {
        this(
                skills,
                agentUserContextResolver,
                maxConcurrentConversations,
                skillTimeout,
                Executors.newVirtualThreadPerTaskExecutor()
        );
    }

    private ChatAgent(
            List<AgentSkill> skills,
            AgentUserContextResolver agentUserContextResolver,
            int maxConcurrentConversations,
            Duration skillTimeout,
            ExecutorService agentExecutor
    ) {
        this.skills = skills.stream()
                .sorted(Comparator.comparing(AgentSkill::id))
                .toList();
        this.agentUserContextResolver = agentUserContextResolver;
        this.maxConcurrentConversations = Math.max(1, maxConcurrentConversations);
        this.skillTimeout = normalizeSkillTimeout(skillTimeout);
        this.agentExecutor = agentExecutor;
        this.conversationLimiter = new Semaphore(this.maxConcurrentConversations, true);
    }

    public Flux<ServerSentEvent<AgentEvent>> streamChat(String message, String massage, boolean webSearch) {
        return streamChatEvents(message, massage, webSearch)
                .map(payload -> ServerSentEvent.<AgentEvent>builder(payload)
                        .event(payload.type())
                        .build());
    }

    public Flux<AgentEvent> streamChatEvents(String message, String massage, boolean webSearch) {
        String userMessage = resolveUserMessage(message, massage);
        AgentSkillContext context = buildContext(userMessage, webSearch);
        return Flux.create(sink -> agentExecutor.submit(() -> streamConversation(context, sink)));
    }

    @WsAction(service = "ChatAgent", action = "chatStream", exposed = true)
    public Flux<AgentEvent> chatStream(String message, boolean webSearch) {
        return streamChatEvents(message, null, webSearch);
    }

    public ChatActionResponse chatWithActions(String message, String massage, boolean webSearch) {
        String userMessage = resolveUserMessage(message, massage);
        AgentConversation conversation = executeConversationWithPermit(buildContext(userMessage, webSearch));
        return new ChatActionResponse(
                conversation.answer(),
                conversation.actions(),
                conversation.needConfirm(),
                conversation.agentContext()
        );
    }

    public List<AgentSkillInfo> listSkills() {
        return skills.stream()
                .map(skill -> new AgentSkillInfo(skill.id(), skill.displayName(), skill.description()))
                .toList();
    }

    private void streamConversation(AgentSkillContext context, FluxSink<AgentEvent> sink) {
        if (!tryAcquireConversationSlot()) {
            emitBusyConversation(context, sink);
            return;
        }

        try {
            sink.next(AgentEvent.status(ANALYZING_STATUS));

            AgentConversation conversation = executeConversation(context);

            sink.next(AgentEvent.context(conversation.agentContext()));

            if (!conversation.skillNames().isEmpty()) {
                sink.next(AgentEvent.status("已启用技能: " + String.join("、", conversation.skillNames())));
            }

            for (String result : conversation.searchResults()) {
                sink.next(AgentEvent.search(result));
            }

            for (String chunk : splitIntoChunks(conversation.answer())) {
                sink.next(AgentEvent.message(chunk));
            }

            if (!conversation.actions().isEmpty()) {
                sink.next(AgentEvent.actions(conversation.actions()));
            }

            sink.complete();
        } catch (Exception error) {
            logger.error("Agent stream failed", error);
            sink.error(error);
        } finally {
            conversationLimiter.release();
        }
    }

    private AgentConversation executeConversationWithPermit(AgentSkillContext context) {
        if (!tryAcquireConversationSlot()) {
            return busyConversation(context);
        }

        try {
            return executeConversation(context);
        } finally {
            conversationLimiter.release();
        }
    }

    private AgentConversation executeConversation(AgentSkillContext context) {
        List<AgentSkill> selectedSkills = skills.stream()
                .filter(skill -> skill.supports(context))
                .toList();

        List<AgentSkillResult> results = submitSkills(selectedSkills, context).stream()
                .filter(AgentSkillResult::hasContent)
                .toList();

        List<String> summaries = results.stream()
                .map(AgentSkillResult::summary)
                .filter(summary -> summary != null && !summary.isBlank())
                .distinct()
                .toList();
        List<String> highlights = results.stream()
                .flatMap(result -> result.highlights().stream())
                .distinct()
                .toList();
        List<String> searchResults = results.stream()
                .flatMap(result -> result.searchResults().stream())
                .distinct()
                .toList();
        List<ChatAction> actions = deduplicateActions(results.stream()
                .flatMap(result -> result.actions().stream())
                .toList());
        boolean needConfirm = !actions.isEmpty() && results.stream().anyMatch(AgentSkillResult::needConfirm);

        String answer = buildAnswer(context, summaries, highlights, searchResults, actions);
        AgentContextInfo agentContext = AgentContextInfo.from(context);
        List<String> skillNames = selectedSkills.stream().map(AgentSkill::displayName).toList();
        return new AgentConversation(answer, actions, needConfirm, searchResults, skillNames, agentContext);
    }

    private List<AgentSkillResult> submitSkills(List<AgentSkill> selectedSkills, AgentSkillContext context) {
        if (selectedSkills.isEmpty()) {
            return List.of();
        }

        List<SkillExecution> executions = selectedSkills.stream()
                .map(skill -> new SkillExecution(
                        skill,
                        agentExecutor.submit(() -> skill.execute(context)),
                        System.nanoTime() + skillTimeout.toNanos()
                ))
                .toList();

        return executions.stream()
                .map(this::awaitSkillResult)
                .toList();
    }

    private AgentSkillResult awaitSkillResult(SkillExecution execution) {
        long remainingNanos = execution.deadlineNanos() - System.nanoTime();
        if (remainingNanos <= 0) {
            execution.future().cancel(true);
            logger.warn("Skill {} timed out after {} ms", execution.skill().id(), skillTimeout.toMillis());
            return AgentSkillResult.empty(execution.skill().id());
        }

        try {
            return execution.future().get(remainingNanos, TimeUnit.NANOSECONDS);
        } catch (TimeoutException error) {
            execution.future().cancel(true);
            logger.warn("Skill {} timed out after {} ms", execution.skill().id(), skillTimeout.toMillis());
            return AgentSkillResult.empty(execution.skill().id());
        } catch (InterruptedException error) {
            execution.future().cancel(true);
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Agent conversation was interrupted", error);
        } catch (CancellationException error) {
            logger.warn("Skill {} was cancelled", execution.skill().id());
            return AgentSkillResult.empty(execution.skill().id());
        } catch (ExecutionException error) {
            Throwable cause = error.getCause() == null ? error : error.getCause();
            logger.warn("Skill {} failed: {}", execution.skill().id(), cause.getMessage());
            return AgentSkillResult.empty(execution.skill().id());
        }
    }

    private AgentSkillContext buildContext(String userMessage, boolean webSearch) {
        return agentUserContextResolver.resolve(userMessage, webSearch);
    }

    private List<ChatAction> deduplicateActions(List<ChatAction> actions) {
        LinkedHashMap<String, ChatAction> unique = new LinkedHashMap<>();
        for (ChatAction action : actions) {
            String key = String.join("|",
                    safe(action.getType()),
                    safe(action.getTarget()),
                    safe(action.getValue()));
            unique.putIfAbsent(key, action);
        }
        return new ArrayList<>(unique.values());
    }

    private String buildAnswer(
            AgentSkillContext context,
            List<String> summaries,
            List<String> highlights,
            List<String> searchResults,
            List<ChatAction> actions
    ) {
        StringBuilder builder = new StringBuilder("已按交通违法处理场景整理出可执行建议。");

        if (!summaries.isEmpty()) {
            builder.append("\n\n核心判断:");
            for (String summary : summaries) {
                builder.append("\n- ").append(summary);
            }
        }

        if (!highlights.isEmpty()) {
            builder.append("\n\n建议步骤:");
            for (int i = 0; i < highlights.size(); i++) {
                builder.append("\n").append(i + 1).append(". ").append(highlights.get(i));
            }
        }

        if (!searchResults.isEmpty()) {
            builder.append("\n\n联网检索补充:");
            for (int i = 0; i < Math.min(searchResults.size(), 3); i++) {
                builder.append("\n").append(i + 1).append(". ").append(searchResults.get(i));
            }
        } else if (!context.webSearch()) {
            builder.append("\n\n如需结合最新公开信息，可开启联网检索后再次提问。");
        }

        if (!actions.isEmpty()) {
            builder.append("\n\n我还为你编排了可直接执行的页面动作和办理清单，确认后即可继续。");
        } else {
            builder.append("\n\n如果你愿意，我也可以继续帮你细化成页面操作步骤。");
        }

        return builder.toString();
    }

    private boolean tryAcquireConversationSlot() {
        boolean acquired = conversationLimiter.tryAcquire();
        if (!acquired) {
            logger.warn("Rejecting chat conversation because the agent is busy. maxConcurrent={}", maxConcurrentConversations);
        }
        return acquired;
    }

    private AgentConversation busyConversation(AgentSkillContext context) {
        return new AgentConversation(
                BUSY_ANSWER,
                List.of(),
                false,
                List.of(),
                List.of(),
                AgentContextInfo.from(context)
        );
    }

    private void emitBusyConversation(AgentSkillContext context, FluxSink<AgentEvent> sink) {
        AgentConversation conversation = busyConversation(context);
        sink.next(AgentEvent.context(conversation.agentContext()));
        sink.next(AgentEvent.status(BUSY_STATUS));
        for (String chunk : splitIntoChunks(conversation.answer())) {
            sink.next(AgentEvent.message(chunk));
        }
        sink.complete();
    }

    private List<String> splitIntoChunks(String content) {
        if (content == null || content.isBlank()) {
            return List.of("暂时没有可返回的内容。");
        }

        List<String> chunks = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (char ch : content.toCharArray()) {
            current.append(ch);
            if ("。！？\n".indexOf(ch) >= 0 || current.length() >= 56) {
                chunks.add(current.toString());
                current.setLength(0);
            }
        }
        if (current.length() > 0) {
            chunks.add(current.toString());
        }
        return chunks;
    }

    private String resolveUserMessage(String message, String massage) {
        if (message != null && !message.isBlank()) {
            return message.trim();
        }
        if (massage != null && !massage.isBlank()) {
            logger.warn("Parameter 'massage' is deprecated. Please use 'message' instead.");
            return massage.trim();
        }
        throw new IllegalArgumentException("缺少请求参数，message 或 massage 至少提供一个。");
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }

    private Duration normalizeSkillTimeout(Duration configuredSkillTimeout) {
        if (configuredSkillTimeout == null
                || configuredSkillTimeout.isZero()
                || configuredSkillTimeout.isNegative()) {
            return DEFAULT_SKILL_TIMEOUT;
        }
        return configuredSkillTimeout;
    }

    @PreDestroy
    public void shutdown() {
        agentExecutor.shutdown();
    }

    private record AgentConversation(
            String answer,
            List<ChatAction> actions,
            boolean needConfirm,
            List<String> searchResults,
            List<String> skillNames,
            AgentContextInfo agentContext
    ) {
    }

    private record SkillExecution(
            AgentSkill skill,
            Future<AgentSkillResult> future,
            long deadlineNanos
    ) {
    }
}
