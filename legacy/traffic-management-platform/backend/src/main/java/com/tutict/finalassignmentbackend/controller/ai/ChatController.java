package com.tutict.finalassignmentbackend.controller.ai;

import com.tutict.finalassignmentbackend.model.ai.AgentEvent;
import com.tutict.finalassignmentbackend.model.ai.AgentSkillInfo;
import com.tutict.finalassignmentbackend.model.ai.ChatActionResponse;
import com.tutict.finalassignmentbackend.service.ChatAgent;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

import java.util.List;

@RestController
@RequestMapping("/api/ai")
@Tag(name = "AI Chat", description = "AI chat and action endpoints")
public class ChatController {

    private final ChatAgent chatAgent;

    public ChatController(ChatAgent chatAgent) {
        this.chatAgent = chatAgent;
    }

    @GetMapping(value = "/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @Operation(
            summary = "Stream chat events",
            description = "Streams agent status, web-search progress, answer content, and suggested actions via SSE."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Streaming response started successfully."),
            @ApiResponse(responseCode = "400", description = "Missing message or massage parameter."),
            @ApiResponse(responseCode = "500", description = "Internal server error.")
    })
    public Flux<ServerSentEvent<AgentEvent>> chat(
            @RequestParam(value = "message", required = false)
            @Parameter(description = "Primary user input", example = "How do I handle a speeding ticket?")
            String message,
            @RequestParam(value = "massage", required = false)
            @Parameter(description = "Legacy alias for message", deprecated = true)
            String massage,
            @RequestParam(value = "webSearch", defaultValue = "false")
            @Parameter(description = "Whether to enable web search", example = "true")
            boolean webSearch) {
        return chatAgent.streamChat(message, massage, webSearch);
    }

    @GetMapping(value = "/chat/actions", produces = MediaType.APPLICATION_JSON_VALUE)
    @Operation(
            summary = "Get chat actions",
            description = "Returns suggested UI actions that the frontend can confirm before executing."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Action plan returned successfully."),
            @ApiResponse(responseCode = "400", description = "Missing message or massage parameter."),
            @ApiResponse(responseCode = "500", description = "Internal server error.")
    })
    public ChatActionResponse chatActions(
            @RequestParam(value = "message", required = false)
            @Parameter(description = "Primary user input", example = "Open the fine search page for me")
            String message,
            @RequestParam(value = "massage", required = false)
            @Parameter(description = "Legacy alias for message", deprecated = true)
            String massage,
            @RequestParam(value = "webSearch", defaultValue = "false")
            @Parameter(description = "Whether to enable web search", example = "true")
            boolean webSearch) {
        return chatAgent.chatWithActions(message, massage, webSearch);
    }

    @GetMapping(value = "/skills", produces = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "List skills", description = "Returns the skills currently exposed by the agent.")
    public List<AgentSkillInfo> skills() {
        return chatAgent.listSkills();
    }
}
