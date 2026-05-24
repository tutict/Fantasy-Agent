package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.service.AuthWsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.PermitAll;
import jakarta.annotation.security.RolesAllowed;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/auth")
@Tag(name = "Authentication", description = "Authentication and registration endpoints")
public class AuthController {

    private static final Logger LOG = Logger.getLogger(AuthController.class.getName());

    private final AuthWsService authWsService;

    public AuthController(AuthWsService authWsService) {
        this.authWsService = authWsService;
    }

    @PostMapping("/login")
    @PermitAll
    @Operation(
            summary = "User login",
            description = "Authenticates a user with username and password and returns a JWT payload."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Login succeeded and returned a structured token payload.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(type = "object",
                                    example = "{\"jwtToken\":\"<token>\",\"username\":\"admin\",\"roles\":[\"ROLE_ADMIN\"]}")))
            ,
            @ApiResponse(
                    responseCode = "400",
                    description = "Request parameters are missing or invalid.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(type = "object", example = "{\"error\":\"Username and password are required\"}")))
            ,
            @ApiResponse(
                    responseCode = "401",
                    description = "Username or password is incorrect.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(type = "object", example = "{\"error\":\"Invalid credentials\"}")))
    })
    public CompletableFuture<ResponseEntity<Map<String, Object>>> login(
            @RequestBody
            @Parameter(description = "Login request payload containing username and password", required = true)
            AuthWsService.LoginRequest loginRequest) {
        String username = safeUsername(loginRequest == null ? null : loginRequest.getUsername());
        if (loginRequest == null
                || !StringUtils.hasText(loginRequest.getUsername())
                || !StringUtils.hasText(loginRequest.getPassword())) {
            LOG.log(Level.WARNING, "Login request missing username or password");
            return CompletableFuture.completedFuture(
                    ResponseEntity.status(HttpStatus.BAD_REQUEST)
                            .body(Map.of("error", "Username and password are required")));
        }

        try {
            Map<String, Object> result = authWsService.login(loginRequest);
            LOG.log(Level.INFO, "Login succeeded for username: {0}", username);
            return CompletableFuture.completedFuture(ResponseEntity.ok(result));
        } catch (IllegalArgumentException ex) {
            LOG.log(Level.WARNING, "Login rejected for username: {0}, error: {1}",
                    new Object[]{username, ex.getMessage()});
            return CompletableFuture.completedFuture(
                    ResponseEntity.status(HttpStatus.BAD_REQUEST)
                            .body(Map.of("error", ex.getMessage())));
        } catch (Exception ex) {
            return CompletableFuture.completedFuture(loginExceptionResponse(username, ex));
        }
    }

    @PostMapping("/refresh")
    @PermitAll
    @Operation(summary = "Refresh access token")
    public ResponseEntity<Map<String, Object>> refreshToken(
            @RequestBody AuthWsService.RefreshRequest refreshRequest) {
        if (refreshRequest == null || refreshRequest.getRefreshToken() == null || refreshRequest.getRefreshToken().isBlank()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(Map.of("error", "Refresh token is required"));
        }
        try {
            return ResponseEntity.ok(authWsService.refreshToken(refreshRequest.getRefreshToken()));
        } catch (Exception ex) {
            return refreshExceptionResponse(ex);
        }
    }

    @PostMapping("/register")
    @PermitAll
    @Transactional
    @Operation(
            summary = "User registration",
            description = "Registers a new user, assigns the default role, and supports idempotent requests."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "Registration succeeded.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(type = "object", example = "{\"status\":\"CREATED\"}")))
            ,
            @ApiResponse(
                    responseCode = "409",
                    description = "Username already exists or the request is duplicated.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(type = "object", example = "{\"error\":\"Username already exists\"}")))
            ,
            @ApiResponse(
                    responseCode = "500",
                    description = "Internal server error.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(type = "object", example = "{\"error\":\"Internal server error\"}")))
    })
    public CompletableFuture<ResponseEntity<Map<String, String>>> registerUser(
            @RequestBody
            @Parameter(description = "Registration request payload containing username, password, role, and idempotency key",
                    required = true)
            AuthWsService.RegisterRequest registerRequest) {
        String username = safeUsername(registerRequest == null ? null : registerRequest.getUsername());
        if (registerRequest == null
                || !StringUtils.hasText(registerRequest.getUsername())
                || !StringUtils.hasText(registerRequest.getPassword())) {
            LOG.log(Level.WARNING, "Register request missing username or password");
            return CompletableFuture.completedFuture(
                    ResponseEntity.status(HttpStatus.BAD_REQUEST)
                            .body(Map.of("error", "Username and password are required")));
        }

        try {
            String status = authWsService.registerUser(registerRequest);
            LOG.log(Level.INFO, "Register succeeded for username: {0}", username);
            return CompletableFuture.completedFuture(
                    ResponseEntity.status(HttpStatus.CREATED)
                            .body(Map.of("status", status)));
        } catch (IllegalArgumentException ex) {
            LOG.log(Level.WARNING, "Register rejected for username: {0}, error: {1}",
                    new Object[]{username, ex.getMessage()});
            return CompletableFuture.completedFuture(
                    ResponseEntity.status(HttpStatus.BAD_REQUEST)
                            .body(Map.of("error", ex.getMessage())));
        } catch (Exception ex) {
            return CompletableFuture.completedFuture(registerExceptionResponse(username, ex));
        }
    }

    @GetMapping("/users")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN"})
    @SecurityRequirement(name = "bearerAuth")
    @Operation(
            summary = "List all users",
            description = "Returns all system users. Restricted to administrator roles."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Query succeeded.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(implementation = SysUser.class)))
            ,
            @ApiResponse(
                    responseCode = "403",
                    description = "Access denied.",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(type = "object", example = "{\"error\":\"Access denied\"}")))
    })
    public ResponseEntity<List<SysUser>> getAllUsers(@RequestParam(defaultValue = "1") int page,
                                                     @RequestParam(defaultValue = "100") int size) {
        try {
            List<SysUser> users = authWsService.getUsers(page, size);
            LOG.log(Level.INFO, "Fetched {0} users", users.size());
            return ResponseEntity.ok(users);
        } catch (Exception ex) {
            LOG.log(Level.SEVERE, "GetAllUsers failed: {0}", ex.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(List.of());
        }
    }

    private String safeUsername(String username) {
        return StringUtils.hasText(username) ? username.trim() : "<unknown>";
    }

    private ResponseEntity<Map<String, Object>> loginExceptionResponse(String username, Exception ex) {
        if (isAuthenticationFailure(ex)) {
            LOG.log(Level.WARNING, "Login rejected for username: {0}, error: {1}",
                    new Object[]{username, ex.getMessage()});
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", safeErrorMessage(ex, "Invalid username or password.")));
        }

        LOG.log(Level.SEVERE, "Login failed for username: " + username, ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", internalServerErrorMessage()));
    }

    private ResponseEntity<Map<String, Object>> refreshExceptionResponse(Exception ex) {
        if (isRefreshFailure(ex)) {
            LOG.log(Level.WARNING, "Refresh token rejected: {0}", ex.getMessage());
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", safeErrorMessage(ex, "Invalid refresh token.")));
        }

        LOG.log(Level.SEVERE, "Refresh token failed", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", internalServerErrorMessage()));
    }

    private ResponseEntity<Map<String, String>> registerExceptionResponse(String username, Exception ex) {
        if (isRegistrationConflict(ex)) {
            LOG.log(Level.WARNING, "Register conflict for username: {0}, error: {1}",
                    new Object[]{username, ex.getMessage()});
            return ResponseEntity.status(HttpStatus.CONFLICT)
                    .body(Map.of("error", safeErrorMessage(ex, "Username already exists")));
        }

        LOG.log(Level.SEVERE, "Register failed for username: " + username, ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", internalServerErrorMessage()));
    }

    private boolean isAuthenticationFailure(Exception ex) {
        String message = normalizedMessage(ex);
        return message.contains("invalid username or password")
                || message.contains("invalid username")
                || message.contains("invalid password")
                || message.contains("no roles assigned");
    }

    private boolean isRefreshFailure(Exception ex) {
        String message = normalizedMessage(ex);
        return message.contains("invalid refresh token")
                || message.contains("unsupported token type")
                || message.contains("refresh token user not found")
                || message.contains("no roles assigned");
    }

    private boolean isRegistrationConflict(Exception ex) {
        String message = normalizedMessage(ex);
        return message.contains("username already exists")
                || message.contains("duplicate request");
    }

    private String normalizedMessage(Exception ex) {
        return safeErrorMessage(ex, "").toLowerCase();
    }

    private String safeErrorMessage(Exception ex, String fallback) {
        return StringUtils.hasText(ex.getMessage()) ? ex.getMessage() : fallback;
    }

    private String internalServerErrorMessage() {
        return "Internal server error";
    }
}
