package com.tutict.finalassignmentbackend.config;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.login.jwt.AuthenticationSnapshot;
import com.tutict.finalassignmentbackend.config.login.jwt.AuthenticationSnapshotService;
import com.tutict.finalassignmentbackend.config.login.jwt.TokenProvider;
import com.tutict.finalassignmentbackend.config.websocket.WsActionRegistry;
import com.tutict.finalassignmentbackend.model.ai.AgentEvent;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.vertx.core.AbstractVerticle;
import io.vertx.core.MultiMap;
import io.vertx.core.buffer.Buffer;
import io.vertx.core.http.*;
import io.vertx.core.json.JsonObject;
import io.vertx.ext.web.Router;
import io.vertx.ext.web.client.HttpResponse;
import io.vertx.ext.web.client.WebClient;
import io.vertx.ext.web.handler.CorsHandler;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Lazy;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.reactivestreams.Publisher;
import reactor.core.publisher.Flux;

import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import static io.vertx.core.Vertx.vertx;

@Slf4j
@Component
public class NetWorkHandler extends AbstractVerticle {
    private static final Set<String> SENSITIVE_HEADERS = Set.of(
            "authorization",
            "cookie",
            "set-cookie",
            "proxy-authorization"
    );
    private static final Set<String> SENSITIVE_FIELDS = Set.of(
            "token",
            "jwttoken",
            "refreshtoken",
            "authorization",
            "password",
            "currentpassword",
            "newpassword",
            "accesstoken"
    );

    @Value("${network.server.port:8081}")
    int port;

    @Value("${backend.url}")
    String backendUrl;

    @Value("${backend.port}")
    int backendPort;

    @Value("${network.cors.allowed-origins:}")
    String allowedOriginsConfig;

    TokenProvider tokenProvider;

    @Lazy
    WsActionRegistry wsActionRegistry;

    private final ObjectMapper objectMapper;
    private final AuthenticationSnapshotService authenticationSnapshotService;
    private WebClient webClient;

    public NetWorkHandler(TokenProvider tokenProvider,
                          ObjectMapper objectMapper,
                          AuthenticationSnapshotService authenticationSnapshotService) {
        this.tokenProvider = tokenProvider;
        this.objectMapper = objectMapper;
        this.authenticationSnapshotService = authenticationSnapshotService;
    }

    @PostConstruct
    public void init() {
        io.vertx.core.Vertx coreVertx = vertx();
        webClient = io.vertx.ext.web.client.WebClient.create(coreVertx);
    }

    @Override
    public void start() {
        this.webClient = WebClient.create(vertx);

        Router router = Router.router(vertx);
        configureCors(router);
        setupNetWorksServer(router);
    }

    private void setupNetWorksServer(Router router) {
        router.route("/api/*").handler(ctx -> {
            HttpServerRequest request = ctx.request();
            forwardHttpRequest(request);
        });

        router.route("/eventbus/*").handler(ctx -> {
            HttpServerRequest request = ctx.request();
            request.toWebSocket().onSuccess(ws -> {
                log.info("WebSocket 连接已建立, path={}", ws.path());
                if (ws.path().contains("/eventbus")) {
                    handleWebSocketConnection(ws);
                } else {
                    ws.close((short) 1003, "Unsupported path").onSuccess(success ->
                            log.info("关闭 {} WebSocket 连接成功 {}", ws.path(), success)
                    ).onFailure(failure ->
                            log.error("关闭 {} WebSocket 连接失败: {}", ws.path(), failure.getMessage(), failure)
                    );
                }
            }).onFailure(failure -> {
                log.error("WebSocket 升级失败: {}", failure.getMessage(), failure);
                ctx.response().setStatusCode(400).setStatusMessage("WebSocket upgrade failed").end();
            });
        });

        router.routeWithRegex("^/(?!api(/|$)|eventbus(/|$)).*")
                .handler(ctx -> ctx.response().setStatusCode(404)
                        .setStatusMessage("未找到资源")
                        .closed());

        HttpServerOptions options = new HttpServerOptions()
                .setMaxWebSocketFrameSize(1000000)
                .setTcpKeepAlive(true);

        vertx.createHttpServer(options)
                .requestHandler(router)
                .listen(port)
                .onSuccess(server -> log.info("Network服务器已在端口 {} 启动", server.actualPort()))
                .onFailure(failure -> log.error("Network服务器启动失败: {}", failure.getMessage(), failure));
    }

    private void configureCors(Router router) {
        Set<String> allowedHeaders = Set.of(
                "Authorization", "X-Requested-With", "Sec-WebSocket-Key",
                "Sec-WebSocket-Version", "Sec-WebSocket-Protocol", "Content-Type", "Accept"
        );

        CorsHandler corsHandler = CorsHandler.create();
        Arrays.stream(allowedOriginsConfig.split(","))
                .map(String::trim)
                .filter(origin -> !origin.isEmpty())
                .forEach(corsHandler::addOrigin);
        router.route().handler(corsHandler
                .allowedHeaders(allowedHeaders)
                .allowedMethod(io.vertx.core.http.HttpMethod.GET)
                .allowedMethod(io.vertx.core.http.HttpMethod.POST)
                .allowedMethod(io.vertx.core.http.HttpMethod.PUT)
                .allowedMethod(io.vertx.core.http.HttpMethod.OPTIONS));
    }

    private void handleWebSocketConnection(ServerWebSocket ws) {
        ws.frameHandler(frame -> {
            if (frame.isText()) {
                String message = frame.textData();
                try {
                    JsonNode root = objectMapper.readTree(message);
                    String service = root.path("service").asText(null);
                    String action = root.path("action").asText(null);
                    String idempotencyKey = root.path("idempotencyKey").asText(null);
                    String token = resolveWebSocketToken(ws, root.path("token").asText(null));
                    AuthenticationSnapshot authenticationSnapshot = resolveAuthenticationSnapshot(token);

                    JsonNode argsArray = root.path("args");
                    if (argsArray.isMissingNode() || !argsArray.isArray()) {
                        log.warn("Invalid or missing 'args' array");
                        ws.writeTextMessage("{\"error\":\"Missing or invalid 'args' array\"}")
                                .onSuccess(result -> log.info("WebSocket write success: {}", result))
                                .onFailure(failure -> log.error("WebSocket write failure: {}", failure.getMessage(), failure));
                        return;
                    }

                    log.info("Received service={}, action={}, idempotencyKey={}, args={}",
                            service, action, idempotencyKey, argsArray);

                    WsActionRegistry.HandlerMethod handler = wsActionRegistry.getHandler(service, action);
                    if (handler == null) {
                        ws.writeTextMessage("{\"error\":\"No such WsAction for " + service + "#" + action + "\"}")
                                .onSuccess(result -> log.info("WebSocket write success: {}", result))
                                .onFailure(failure -> log.error("WebSocket write failure: {}", failure.getMessage(), failure));
                        return;
                    }

                    if (!isAuthorized(handler, token, authenticationSnapshot)) {
                        log.warn("Rejected unauthorized WebSocket action {}#{}", service, action);
                        ws.writeTextMessage("{\"error\":\"Forbidden\"}")
                                .onSuccess(result -> log.info("WebSocket write success: {}", result))
                                .onFailure(failure -> log.error("WebSocket write failure: {}", failure.getMessage(), failure));
                        ws.close((short) 1008, "Forbidden");
                        return;
                    }

                    Method method = handler.getMethod();
                    Class<?>[] paramTypes = method.getParameterTypes();
                    Object bean = handler.getBean();
                    int paramCount = paramTypes.length;

                    if (argsArray.size() != paramCount) {
                        ws.writeTextMessage("{\"error\":\"Param mismatch, method expects "
                                        + paramCount + " but got " + argsArray.size() + "\"}")
                                .onSuccess(result -> log.info("WebSocket write success: {}", result))
                                .onFailure(failure -> log.error("WebSocket write failure: {}", failure.getMessage(), failure));
                        return;
                    }

                    Object[] invokeArgs = new Object[paramCount];
                    for (int i = 0; i < paramCount; i++) {
                        Class<?> pt = paramTypes[i];
                        JsonNode argNode = argsArray.get(i);
                        invokeArgs[i] = convertJsonToParam(argNode, pt);
                    }

                    SecurityContext previousContext = SecurityContextHolder.getContext();
                    SecurityContext currentContext = buildSecurityContext(authenticationSnapshot);
                    Object result;
                    try {
                        SecurityContextHolder.setContext(currentContext);
                        result = method.invoke(bean, invokeArgs);
                    } finally {
                        SecurityContextHolder.clearContext();
                        if (previousContext != null) {
                            SecurityContextHolder.setContext(previousContext);
                        }
                    }

                    if (result instanceof Publisher<?> publisher) {
                        streamReactiveResult(ws, publisher);
                        return;
                    }

                    if (method.getReturnType() != void.class && result != null) {
                        try {
                            String retJson = objectMapper.writeValueAsString(result);
                            ws.writeTextMessage("{\"result\":" + retJson + "}")
                                    .onSuccess(response -> log.info("WebSocket write success: {}", response))
                                    .onFailure(failure -> log.error("WebSocket write failure: {}", failure.getMessage(), failure));
                        } catch (JsonProcessingException e) {
                            log.error("Error serializing result to JSON", e);
                            ws.writeTextMessage("{\"error\":\"Internal server error\"}")
                                    .onSuccess(response -> log.info("Error response sent: {}", response))
                                    .onFailure(failure -> log.error("Failed to send error response: {}", failure.getMessage(), failure));
                        }
                    } else {
                        ws.writeTextMessage("{\"status\":\"OK\"}")
                                .onSuccess(response -> log.info("WebSocket write success: {}", response))
                                .onFailure(failure -> log.error("WebSocket write failure: {}", failure.getMessage(), failure));
                    }

                } catch (Exception e) {
                    log.error("JSON parsing or reflection error", e);
                    ws.close((short) 1000, "Invalid JSON or reflect error")
                            .onComplete(ar -> {
                                if (ar.succeeded()) {
                                    log.info("WebSocket closed due to invalid JSON");
                                } else {
                                    log.error("Error closing WebSocket: {}", ar.cause().getMessage(), ar.cause());
                                }
                            });
                }
            } else {
                log.warn("Unsupported WebSocket frame type");
            }
        });

        ws.closeHandler(v -> log.info("WebSocket connection closed, path={} {}", ws.path(), v));
    }

    private void streamReactiveResult(ServerWebSocket ws, Publisher<?> publisher) {
        Flux.from(publisher).subscribe(
                item -> writeWsJson(ws, item),
                error -> {
                    log.error("Reactive WebSocket handler failed", error);
                    writeWsJson(ws, AgentEvent.error(error.getMessage() == null ? "Agent stream failed" : error.getMessage()));
                    ws.close((short) 1011, "Agent stream failed");
                },
                () -> {
                    ws.writeTextMessage(writeJson(AgentEvent.complete()))
                            .onComplete(ignored -> ws.close((short) 1000, "Completed"));
                }
        );
    }

    private void writeWsJson(ServerWebSocket ws, Object payload) {
        ws.writeTextMessage(writeJson(payload))
                .onFailure(failure -> log.error("WebSocket write failure: {}", failure.getMessage(), failure));
    }

    private String writeJson(Object payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize WebSocket payload", e);
            try {
                return objectMapper.writeValueAsString(Map.of(
                        "type", "error",
                        "content", "Internal serialization error"
                ));
            } catch (JsonProcessingException ex) {
                return "{\"type\":\"error\",\"content\":\"Internal serialization error\"}";
            }
        }
    }

    private Object convertJsonToParam(JsonNode node, Class<?> targetType) throws JsonProcessingException {
        if (targetType == String.class) {
            return node.asText();
        } else if (targetType == int.class || targetType == Integer.class) {
            return node.asInt();
        } else if (targetType == long.class || targetType == Long.class) {
            return node.asLong();
        } else if (targetType == boolean.class || targetType == Boolean.class) {
            return node.asBoolean();
        } else {
            return objectMapper.treeToValue(node, targetType);
        }
    }

    private SecurityContext buildSecurityContext(AuthenticationSnapshot snapshot) {
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        if (snapshot == null) {
            return context;
        }
        context.setAuthentication(new UsernamePasswordAuthenticationToken(
                snapshot.username(),
                null,
                snapshot.grantedAuthorities()
        ));
        return context;
    }

    private AuthenticationSnapshot resolveAuthenticationSnapshot(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        String username = tokenProvider.getUsernameFromToken(token);
        return authenticationSnapshotService.findActiveSnapshotByUsername(username);
    }

    private String resolveWebSocketToken(ServerWebSocket ws, String messageToken) {
        if (messageToken != null && !messageToken.isBlank()) {
            return messageToken.trim();
        }
        String authorization = ws.headers().get("Authorization");
        if (authorization != null && authorization.startsWith("Bearer ")) {
            return authorization.substring(7).trim();
        }
        return null;
    }

    private boolean isAuthorized(WsActionRegistry.HandlerMethod handler, String token, AuthenticationSnapshot snapshot) {
        var wsAction = handler.getWsAction();
        if (wsAction == null) {
            return false;
        }
        if (wsAction.allowAnonymous()) {
            return true;
        }
        if (token == null || token.isBlank() || !tokenProvider.validateToken(token) || !tokenProvider.isAccessToken(token)) {
            return false;
        }
        if (snapshot == null) {
            return false;
        }
        String[] rolesAllowed = wsAction.rolesAllowed();
        if (rolesAllowed == null || rolesAllowed.length == 0) {
            return true;
        }
        Authentication authentication = buildSecurityContext(snapshot).getAuthentication();
        if (authentication == null) {
            return false;
        }
        Set<String> granted = authentication.getAuthorities().stream()
                .map(authority -> authority == null ? null : authority.getAuthority())
                .filter(authority -> authority != null && !authority.isBlank())
                .collect(Collectors.toSet());
        return Arrays.stream(rolesAllowed)
                .map(role -> role == null ? "" : role.trim())
                .filter(role -> !role.isEmpty())
                .map(role -> role.startsWith("ROLE_") ? role : "ROLE_" + role)
                .anyMatch(granted::contains);
    }

    private void forwardHttpRequest(HttpServerRequest request) {
        String requestId = UUID.randomUUID().toString();
        String path = request.path();
        String query = request.query();
        String targetUrl = backendUrl + ":" + backendPort + path + (query != null ? "?" + query : "");
        log.debug("[{}] Forwarding request from path: {} to targetUrl: {}", requestId, path, targetUrl);

        if (request.headers().contains("X-Forwarded-By")) {
            log.error("[{}] Detected circular forwarding, aborting request", requestId);
            request.response().setStatusCode(500).setStatusMessage("Circular forwarding detected").end();
            return;
        }

        request.headers().add("X-Forwarded-By", "NetWorkHandler");

        MultiMap headers = MultiMap.caseInsensitiveMultiMap();
        request.headers().forEach(entry -> {
            headers.add(entry.getKey(), entry.getValue());
            log.debug("[{}] Forwarded header: {} = {}", requestId, entry.getKey(),
                    redactHeaderValue(entry.getKey(), entry.getValue()));
        });

        MultiMap queryParams = request.params();
        log.debug("[{}] Query params: {}", requestId, queryParams);

        HttpMethod method = request.method();
        var httpRequest = webClient.requestAbs(method, targetUrl).putHeaders(headers);

        if (method == HttpMethod.GET || method == HttpMethod.DELETE) {
            log.debug("[{}] Forwarding {} request with query params: {}", requestId, method, queryParams);
            httpRequest.send()
                    .onSuccess(response -> handleResponse(request, response, requestId))
                    .onFailure(failure -> {
                        log.error("[{}] Forwarding {} request failed: {}", requestId, method, failure.getMessage(), failure);
                        request.response().setStatusCode(500).setStatusMessage("Forwarding failed").end();
                    });
        } else {
            request.bodyHandler(body -> {
                try {
                    String contentType = request.getHeader("Content-Type");
                    if (body.length() == 0) {
                        log.debug("[{}] No body provided for {} request, proceeding with empty request", requestId, method);
                        httpRequest.send()
                                .onSuccess(response -> handleResponse(request, response, requestId))
                                .onFailure(failure -> {
                                    log.error("[{}] Forwarding {} request failed: {}", requestId, method, failure.getMessage(), failure);
                                    request.response().setStatusCode(500).setStatusMessage("Forwarding failed").end();
                                });
                    } else if (contentType != null && contentType.toLowerCase().contains("text/plain")) {
                        String rawBody = body.toString();
                        log.debug("[{}] Raw body for {}: {}", requestId, method, sanitizeForLog(rawBody));
                        httpRequest.putHeader("Content-Type", contentType);
                        httpRequest.sendBuffer(Buffer.buffer(rawBody))
                                .onSuccess(response -> handleResponse(request, response, requestId))
                                .onFailure(failure -> {
                                    log.error("[{}] Forwarding {} request failed: {}", requestId, method, failure.getMessage(), failure);
                                    request.response().setStatusCode(500).setStatusMessage("Forwarding failed").end();
                                });
                    } else if (contentType != null && contentType.toLowerCase().contains("application/json")) {
                        JsonObject jsonBody = body.toJsonObject();
                        log.debug("[{}] JSON body for {}: {}", requestId, method, sanitizeForLog(jsonBody.encode()));
                        httpRequest.putHeader("Content-Type", "application/json");
                        httpRequest.sendJsonObject(jsonBody)
                                .onSuccess(response -> handleResponse(request, response, requestId))
                                .onFailure(failure -> {
                                    log.error("[{}] Forwarding {} request failed: {}", requestId, method, failure.getMessage(), failure);
                                    request.response().setStatusCode(500).setStatusMessage("Forwarding failed").end();
                                });
                    } else {
                        log.warn("[{}] Unrecognized Content-Type: {} for {}, forwarding as raw buffer", requestId, contentType, method);
                        httpRequest.sendBuffer(body)
                                .onSuccess(response -> handleResponse(request, response, requestId))
                                .onFailure(failure -> {
                                    log.error("[{}] Forwarding {} request failed: {}", requestId, method, failure.getMessage(), failure);
                                    request.response().setStatusCode(500).setStatusMessage("Forwarding failed").end();
                                });
                    }
                } catch (Exception e) {
                    log.error("[{}] Request body parsing failed for {}: {}", requestId, method, e.getMessage(), e);
                    request.response().setStatusCode(400).setStatusMessage("Request body parsing failed").end();
                }
            });
        }
    }

    private void handleResponse(HttpServerRequest request, HttpResponse<io.vertx.core.buffer.Buffer> response, String requestId) {
        log.debug("[{}] Response status code: {}", requestId, response.statusCode());
        log.debug("[{}] Response headers: {}", requestId, sanitizeHeaders(response.headers().entries()));
        String responseBody = response.bodyAsString();
        log.debug("[{}] Backend response body: {}", requestId, responseBody != null ? sanitizeForLog(responseBody) : "null");

        HttpServerResponse clientResponse = request.response();
        clientResponse.setStatusCode(response.statusCode());

        String statusMessage = response.statusMessage();
        if (statusMessage != null) {
            clientResponse.setStatusMessage(statusMessage);
        } else {
            log.warn("[{}] Backend response statusMessage is null", requestId);
            clientResponse.setStatusMessage(HttpResponseStatus.valueOf(response.statusCode()).reasonPhrase());
        }

        response.headers().forEach(entry -> {
            if (!entry.getKey().equalsIgnoreCase("Transfer-Encoding")) {
                clientResponse.putHeader(entry.getKey(), entry.getValue());
            }
        });

        if (responseBody != null && !responseBody.isEmpty()) {
            clientResponse.putHeader("Content-Type", "application/json");
            clientResponse.end(responseBody);
        } else {
            log.warn("[{}] Response body is null or empty, status: {}", requestId, response.statusCode());
            clientResponse.putHeader("Content-Type", "application/json");
            clientResponse.end();
        }
    }

    private String redactHeaderValue(String name, String value) {
        return name != null && SENSITIVE_HEADERS.contains(name.toLowerCase())
                ? "<redacted>"
                : sanitizeForLog(value);
    }

    private Map<String, String> sanitizeHeaders(Iterable<Map.Entry<String, String>> entries) {
        Map<String, String> sanitized = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : entries) {
            sanitized.put(entry.getKey(), redactHeaderValue(entry.getKey(), entry.getValue()));
        }
        return sanitized;
    }

    private String sanitizeForLog(String value) {
        if (value == null || value.isBlank()) {
            return value;
        }
        try {
            JsonNode root = objectMapper.readTree(value);
            redactJsonNode(root);
            return objectMapper.writeValueAsString(root);
        } catch (Exception ignored) {
            return value;
        }
    }

    private void redactJsonNode(JsonNode node) {
        if (node == null) {
            return;
        }
        if (node.isObject()) {
            var fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> entry = fields.next();
                if (SENSITIVE_FIELDS.contains(entry.getKey().toLowerCase())) {
                    ((com.fasterxml.jackson.databind.node.ObjectNode) node).put(entry.getKey(), "<redacted>");
                } else {
                    redactJsonNode(entry.getValue());
                }
            }
            return;
        }
        if (node.isArray()) {
            for (JsonNode child : node) {
                redactJsonNode(child);
            }
        }
    }
}
