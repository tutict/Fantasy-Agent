package com.tutict.finalassignmentbackend.service;

import com.tutict.finalassignmentbackend.config.login.jwt.TokenProvider;
import com.tutict.finalassignmentbackend.config.tenant.TenantContextHolder;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.AuditLoginLog;
import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.SysUserRole;
import com.tutict.finalassignmentbackend.enums.DataScope;
import com.tutict.finalassignmentbackend.enums.RoleType;
import lombok.Data;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;

@Service
public class AuthWsService {
    private static final int DEFAULT_USER_LIST_PAGE = 1;
    private static final int DEFAULT_USER_LIST_SIZE = 100;


    private static final Logger logger = Logger.getLogger(AuthWsService.class.getName());
    private static final int MAX_ROLE_PAGE_SIZE = 100;
    private static final int MAX_FAILED_LOGIN_ATTEMPTS = 5;
    private static final int LOGIN_FAILURE_WINDOW_MINUTES = 15;
    private static final int LOGIN_LOCKOUT_MINUTES = 15;
    private static final String SYSTEM_LOGIN_IP = "127.0.0.1";

    private final TokenProvider tokenProvider;
    private final AuditLoginLogService auditLoginLogService;
    private final SysUserService sysUserService;
    private final SysRoleService sysRoleService;
    private final SysUserRoleService sysUserRoleService;
    private final ConcurrentMap<String, LoginThrottleState> loginThrottleStates = new ConcurrentHashMap<>();

    @Autowired
    public AuthWsService(TokenProvider tokenProvider,
                         AuditLoginLogService auditLoginLogService,
                         SysUserService sysUserService,
                         SysRoleService sysRoleService,
                         SysUserRoleService sysUserRoleService) {
        this.tokenProvider = tokenProvider;
        this.auditLoginLogService = auditLoginLogService;
        this.sysUserService = sysUserService;
        this.sysRoleService = sysRoleService;
        this.sysUserRoleService = sysUserRoleService;
    }

    @CacheEvict(cacheNames = "AuthCache", allEntries = true)
    @WsAction(service = "AuthWsService", action = "login", exposed = true, allowAnonymous = true)
    public Map<String, Object> login(LoginRequest loginRequest) {
        validateLoginRequest(loginRequest);
        String username = loginRequest.getUsername().trim();
        String throttleKey = normalizeThrottleKey(username);
        ensureLoginIsAllowed(throttleKey);

        logger.info(() -> String.format("[WS] Attempting to authenticate user: %s", username));
        SysUser user = sysUserService.findByUsername(username);

        if (user != null && sysUserService.verifyPassword(user, loginRequest.getPassword())) {
            RoleAggregation aggregation = aggregateRoles(user.getUserId());
            if (aggregation.getRoleCodes().isEmpty()) {
                clearFailedAttempts(throttleKey);
                sysUserService.resetLoginFailures(user);
                logger.severe(() -> String.format("No roles found for user: %s", username));
                recordFailedLogin(username, "NO_ROLES_ASSIGNED");
                throw new RuntimeException("No roles assigned to user.");
            }
            clearFailedAttempts(throttleKey);
            sysUserService.recordSuccessfulLogin(user, SYSTEM_LOGIN_IP);
            logger.info(() -> String.format("User authenticated successfully (WS): %s with roles: %s",
                    username, String.join(",", aggregation.getRoleCodes())));
            Map<String, Object> response = buildAuthenticationResponse(user, aggregation);
            recordSuccessfulLogin(username);
            return response;
        }

        if (user != null) {
            sysUserService.recordLoginFailure(user);
        }
        boolean locked = registerFailedAttempt(throttleKey);
        logger.severe(() -> String.format("Authentication failed (WS) for user: %s", username));
        recordFailedLogin(username, locked ? "TOO_MANY_ATTEMPTS" : "INVALID_CREDENTIALS");
        throw new RuntimeException(locked
                ? "Too many failed login attempts. Please try again later."
                : "Invalid username or password.");
    }

    @CacheEvict(cacheNames = "AuthCache", allEntries = true)
    @WsAction(service = "AuthWsService", action = "refreshToken", exposed = true, allowAnonymous = true)
    public Map<String, Object> refreshToken(String refreshToken) {
        if (!StringUtils.hasText(refreshToken) || !tokenProvider.validateToken(refreshToken)) {
            throw new RuntimeException("Invalid refresh token.");
        }
        if (!tokenProvider.isRefreshToken(refreshToken)) {
            throw new RuntimeException("Unsupported token type for refresh.");
        }

        String username = tokenProvider.getUsernameFromToken(refreshToken);
        SysUser user = sysUserService.findByUsername(username);
        if (user == null) {
            throw new RuntimeException("Refresh token user not found.");
        }

        RoleAggregation aggregation = aggregateRoles(user.getUserId());
        if (aggregation.getRoleCodes().isEmpty()) {
            throw new RuntimeException("No roles assigned to user.");
        }
        return buildAuthenticationResponse(user, aggregation);
    }

    @Transactional
    @CacheEvict(cacheNames = {"AuthCache", "usernameExistsCache"}, allEntries = true)
    @WsAction(service = "AuthWsService", action = "registerUser", exposed = true, allowAnonymous = true)
    public String registerUser(RegisterRequest registerRequest) {
        validateRegisterRequest(registerRequest);
        logger.info(() -> String.format("Attempting to register user: %s", registerRequest.getUsername()));

        String idempotencyKey = registerRequest.getIdempotencyKey();
        boolean useIdempotency = StringUtils.hasText(idempotencyKey);
        if (useIdempotency && sysUserService.shouldSkipProcessing(idempotencyKey)) {
            logger.info(() -> String.format("Registration replay acknowledged for idempotency key: %s", idempotencyKey));
            return "CREATED";
        }

        if (sysUserService.isUsernameExists(registerRequest.getUsername())) {
            logger.severe(() -> String.format("Username already exists: %s", registerRequest.getUsername()));
            throw new RuntimeException("Username already exists: " + registerRequest.getUsername());
        }

        if (useIdempotency) {
            SysUser probe = new SysUser();
            probe.setUsername(registerRequest.getUsername());
            try {
                sysUserService.checkAndInsertIdempotency(idempotencyKey, probe, "create");
            } catch (RuntimeException e) {
                if (sysUserService.shouldSkipProcessing(idempotencyKey)) {
                    logger.info(() -> String.format("Registration replay completed during idempotency check for key: %s",
                            idempotencyKey));
                    return "CREATED";
                }
                logger.log(Level.WARNING, "Idempotency check failed for key {0}: {1}",
                        new Object[]{idempotencyKey, e.getMessage()});
                throw new RuntimeException("Registration failed: duplicate request", e);
            }
        }

        try {
            SysUser newUser = new SysUser();
            newUser.setUsername(registerRequest.getUsername());
            newUser.setPassword(registerRequest.getPassword());
            newUser.setPasswordUpdateTime(LocalDateTime.now());
            newUser.setStatus("Active");
            newUser.setCreatedAt(LocalDateTime.now());
            newUser.setUpdatedAt(LocalDateTime.now());
            sysUserService.createSysUser(newUser);
            logger.info(() -> String.format("User created successfully: %s", registerRequest.getUsername()));

            SysUser savedUser = sysUserService.findByUsername(registerRequest.getUsername());
            if (savedUser == null) {
                logger.warning(() -> String.format("Unable to load newly created user: %s", registerRequest.getUsername()));
                throw new RuntimeException("User creation failed because the saved user could not be loaded.");
            }

            SysRole role = resolveRegistrationRole(registerRequest.getRole());
            assignRole(savedUser, role);

            if (useIdempotency) {
                sysUserService.markHistorySuccess(idempotencyKey, savedUser.getUserId());
            }

            logger.info(() -> String.format("User registration completed: %s", registerRequest.getUsername()));
            return "CREATED";
        } catch (RuntimeException e) {
            if (useIdempotency) {
                sysUserService.markHistoryFailure(idempotencyKey, e.getMessage());
            }
            throw e;
        }
    }

    @CacheEvict(cacheNames = "AuthCache", allEntries = true)
    @WsAction(service = "AuthWsService", action = "getAllUsers", exposed = true, rolesAllowed = {"SUPER_ADMIN", "ADMIN"})
    public List<SysUser> getAllUsers() {
        return getUsers(DEFAULT_USER_LIST_PAGE, DEFAULT_USER_LIST_SIZE);
    }

    public List<SysUser> getUsers(int page, int size) {
        logger.info(() -> String.format("[WS] Fetching users page=%d size=%d", page, size));
        List<SysUser> users = sysUserService.listUsers(page, size);
        if (users.isEmpty()) {
            logger.warning("No users found in the system");
        }
        return users;
    }

    private void validateLoginRequest(LoginRequest loginRequest) {
        Objects.requireNonNull(loginRequest, "Login request must not be null");
        if (!StringUtils.hasText(loginRequest.getUsername())) {
            logger.severe("Authentication failed: username is null or empty");
            throw new RuntimeException("Invalid username");
        }
        if (!StringUtils.hasText(loginRequest.getPassword())) {
            logger.severe("Authentication failed: password is null or empty");
            throw new RuntimeException("Invalid password");
        }
    }

    private void validateRegisterRequest(RegisterRequest registerRequest) {
        Objects.requireNonNull(registerRequest, "Register request must not be null");
        if (!StringUtils.hasText(registerRequest.getUsername())) {
            throw new IllegalArgumentException("Username must not be blank");
        }
        if (!StringUtils.hasText(registerRequest.getPassword())) {
            throw new IllegalArgumentException("Password must not be blank");
        }
    }

    private SysRole resolveRegistrationRole(String requestedRole) {
        String roleCode = StringUtils.hasText(requestedRole)
                ? requestedRole.trim().toUpperCase(Locale.ROOT)
                : "USER";
        if (!"USER".equals(roleCode)) {
            logger.warning(() -> String.format("Rejected self-registration with elevated role: %s", roleCode));
            throw new IllegalArgumentException("Self registration only supports USER role.");
        }
        SysRole role = sysRoleService.findByRoleCode(roleCode);
        if (role != null) {
            return role;
        }
        logger.info(() -> String.format("Role %s not found, creating default self-service role", roleCode));
        SysRole newRole = new SysRole();
        newRole.setRoleCode(roleCode);
        newRole.setRoleName(roleCode);
        newRole.setRoleDescription("SELF_REGISTERED_USER");
        newRole.setRoleType(RoleType.CUSTOM.getCode());
        newRole.setDataScope(DataScope.SELF.getCode());
        newRole.setStatus("Active");
        newRole.setCreatedAt(LocalDateTime.now());
        newRole.setUpdatedAt(LocalDateTime.now());
        return sysRoleService.createSysRole(newRole);
    }

    private Map<String, Object> buildUserSummary(SysUser user) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("userId", user.getUserId());
        summary.put("username", user.getUsername());
        summary.put("realName", user.getRealName());
        summary.put("email", user.getEmail());
        summary.put("contactNumber", user.getContactNumber());
        summary.put("status", user.getStatus());
        summary.put("tenantId", user.getTenantId());
        summary.put("organizationCode", user.getOrganizationCode());
        summary.put("regionCode", user.getRegionCode());
        summary.put("departmentCode", user.getDepartmentCode());
        return summary;
    }

    private Map<String, Object> buildAuthenticationResponse(SysUser user, RoleAggregation aggregation) {
        String roleCodesCsv = String.join(",", aggregation.getRoleCodes());
        String roleTypesCsv = String.join(",", aggregation.getRoleTypes());
        String dataScopeCode = aggregation.getDataScope().getCode();
        String tenantId = firstNonBlank(user.getTenantId(), TenantContextHolder.getTenantId());
        String organizationCode = firstNonBlank(user.getOrganizationCode(), TenantContextHolder.getOrganizationCode());
        String regionCode = firstNonBlank(user.getRegionCode(), TenantContextHolder.getRegionCode());
        String departmentCode = firstNonBlank(user.getDepartmentCode(), TenantContextHolder.getDepartmentCode());
        boolean claimsSupported = StringUtils.hasText(roleCodesCsv)
                && StringUtils.hasText(roleTypesCsv)
                && tokenProvider.validateRoleClaims(roleCodesCsv, roleTypesCsv, dataScopeCode);

        String jwtToken;
        if (claimsSupported) {
            jwtToken = hasTenantClaims(tenantId, organizationCode, regionCode, departmentCode)
                    ? tokenProvider.createEnhancedToken(
                    user.getUsername(),
                    roleCodesCsv,
                    roleTypesCsv,
                    dataScopeCode,
                    tenantId,
                    organizationCode,
                    regionCode,
                    departmentCode
            )
                    : tokenProvider.createEnhancedToken(
                    user.getUsername(),
                    roleCodesCsv,
                    roleTypesCsv,
                    dataScopeCode
            );
        } else {
            logger.warning(() -> String.format(
                    "Role claims are incomplete; falling back to a basic token for user=%s",
                    user.getUsername()));
            jwtToken = hasTenantClaims(tenantId, organizationCode, regionCode, departmentCode)
                    ? tokenProvider.createToken(
                    user.getUsername(),
                    roleCodesCsv,
                    tenantId,
                    organizationCode,
                    regionCode,
                    departmentCode
            )
                    : tokenProvider.createToken(
                    user.getUsername(),
                    roleCodesCsv
            );
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("jwtToken", jwtToken);
        response.put("refreshToken", tokenProvider.createRefreshToken(user.getUsername()));
        response.put("username", user.getUsername());
        response.put("roles", aggregation.getRoleCodes());
        response.put("roleCodes", aggregation.getRoleCodes());
        response.put("roleNames", aggregation.getRoleNames());
        response.put("roleTypes", aggregation.getRoleTypes());
        response.put("dataScope", dataScopeCode);
        response.put("systemRole", tokenProvider.hasSystemRole(jwtToken));
        response.put("businessRole", tokenProvider.hasBusinessRole(jwtToken));
        response.put("departmentScope", tokenProvider.hasDataScopePermission(jwtToken, DataScope.DEPARTMENT));
        response.put("tenantId", tenantId);
        response.put("organizationCode", organizationCode);
        response.put("regionCode", regionCode);
        response.put("departmentCode", departmentCode);
        response.put("user", buildUserSummary(user));
        return response;
    }

    private String firstNonBlank(String primary, String fallback) {
        if (StringUtils.hasText(primary)) {
            return primary.trim();
        }
        return StringUtils.hasText(fallback) ? fallback.trim() : null;
    }

    private boolean hasTenantClaims(String tenantId,
                                    String organizationCode,
                                    String regionCode,
                                    String departmentCode) {
        return StringUtils.hasText(tenantId)
                || StringUtils.hasText(organizationCode)
                || StringUtils.hasText(regionCode)
                || StringUtils.hasText(departmentCode);
    }

    private void assignRole(SysUser user, SysRole role) {
        SysUserRole relation = new SysUserRole();
        relation.setUserId(user.getUserId());
        relation.setRoleId(role.getRoleId());
        relation.setCreatedAt(LocalDateTime.now());
        relation.setCreatedBy("AuthWsService");
        sysUserRoleService.createRelation(relation);
    }

    private void recordSuccessfulLogin(String username) {
        AuditLoginLog loginLog = buildLoginLog(username, "SUCCESS", null);
        persistLoginAudit(loginLog);
    }

    private void recordFailedLogin(String username, String reason) {
        AuditLoginLog loginLog = buildLoginLog(username, "FAILED", reason);
        persistLoginAudit(loginLog);
    }

    private AuditLoginLog buildLoginLog(String username, String loginResult, String failureReason) {
        AuditLoginLog loginLog = new AuditLoginLog();
        loginLog.setUsername(username);
        loginLog.setLoginTime(LocalDateTime.now());
        loginLog.setLoginResult(loginResult);
        loginLog.setFailureReason(failureReason);
        loginLog.setLoginIp("127.0.0.1");
        loginLog.setLoginLocation("LOCAL");
        loginLog.setBrowserType("SYSTEM");
        loginLog.setBrowserVersion("N/A");
        loginLog.setOsType("SERVER");
        loginLog.setOsVersion(System.getProperty("os.version", "N/A"));
        loginLog.setDeviceType("SERVER");
        loginLog.setUserAgent("AuthWsService");
        loginLog.setSessionId("SYSTEM");
        loginLog.setToken(null);
        loginLog.setCreatedAt(LocalDateTime.now());
        loginLog.setRemarks("SYSTEM_MANAGED_LOGIN_AUDIT");
        return loginLog;
    }

    private String normalizeThrottleKey(String username) {
        return username == null ? "" : username.trim().toLowerCase(Locale.ROOT);
    }

    private void ensureLoginIsAllowed(String throttleKey) {
        if (!StringUtils.hasText(throttleKey)) {
            return;
        }
        LoginThrottleState state = loginThrottleStates.get(throttleKey);
        if (state == null) {
            return;
        }
        synchronized (state) {
            LocalDateTime now = LocalDateTime.now();
            if (state.lockedUntil != null && state.lockedUntil.isAfter(now)) {
                throw new RuntimeException("Too many failed login attempts. Please try again later.");
            }
            if (state.lockedUntil != null || isFailureWindowExpired(state, now)) {
                loginThrottleStates.remove(throttleKey, state);
            }
        }
    }

    private boolean registerFailedAttempt(String throttleKey) {
        if (!StringUtils.hasText(throttleKey)) {
            return false;
        }
        LocalDateTime now = LocalDateTime.now();
        LoginThrottleState state = loginThrottleStates.computeIfAbsent(throttleKey, ignored -> new LoginThrottleState());
        synchronized (state) {
            if (isFailureWindowExpired(state, now)) {
                state.failedAttempts = 0;
                state.firstFailureAt = null;
                state.lockedUntil = null;
            }
            if (state.firstFailureAt == null) {
                state.firstFailureAt = now;
            }
            state.failedAttempts++;
            if (state.failedAttempts >= MAX_FAILED_LOGIN_ATTEMPTS) {
                state.lockedUntil = now.plusMinutes(LOGIN_LOCKOUT_MINUTES);
                return true;
            }
            return false;
        }
    }

    private void clearFailedAttempts(String throttleKey) {
        if (StringUtils.hasText(throttleKey)) {
            loginThrottleStates.remove(throttleKey);
        }
    }

    private boolean isFailureWindowExpired(LoginThrottleState state, LocalDateTime now) {
        return state.firstFailureAt != null
                && state.firstFailureAt.plusMinutes(LOGIN_FAILURE_WINDOW_MINUTES).isBefore(now);
    }

    private void persistLoginAudit(AuditLoginLog loginLog) {
        try {
            auditLoginLogService.createAuditLoginLogSystemManaged(loginLog);
        } catch (Exception ex) {
            logger.log(Level.WARNING, "Failed to persist login audit for user=" + loginLog.getUsername(), ex);
        }
    }

    private RoleAggregation aggregateRoles(Long userId) {
        if (userId == null) {
            return RoleAggregation.empty();
        }
        try {
            List<SysUserRole> relations = sysUserRoleService.findByUserId(userId, 1, MAX_ROLE_PAGE_SIZE);
            if (relations == null || relations.isEmpty()) {
                return RoleAggregation.empty();
            }
            List<String> roleNames = new ArrayList<>();
            List<String> roleCodes = new ArrayList<>();
            List<String> roleTypes = new ArrayList<>();
            DataScope aggregatedScope = DataScope.SELF;

            for (SysUserRole relation : relations) {
                if (relation == null || relation.getRoleId() == null) {
                    continue;
                }
                SysRole role = sysRoleService.findById(relation.getRoleId());
                if (role == null) {
                    continue;
                }
                if (StringUtils.hasText(role.getRoleName())) {
                    roleNames.add(role.getRoleName());
                }
                String roleCode = resolveRoleCode(role);
                if (StringUtils.hasText(roleCode)) {
                    roleCodes.add(roleCode);
                }
                String roleType = resolveRoleType(role);
                if (StringUtils.hasText(roleType)) {
                    roleTypes.add(roleType);
                }
                DataScope requiredScope = resolveDataScope(role);
                aggregatedScope = widenScope(aggregatedScope, requiredScope);
            }

            return new RoleAggregation(
                    roleNames.stream().distinct().collect(Collectors.toList()),
                    roleCodes.stream().distinct().collect(Collectors.toList()),
                    roleTypes.stream().distinct().collect(Collectors.toList()),
                    aggregatedScope
            );
        } catch (Exception ex) {
            logger.log(Level.WARNING, "Failed to aggregate roles for userId=" + userId, ex);
            return RoleAggregation.empty();
        }
    }

    private String resolveRoleCode(SysRole role) {
        if (role == null) {
            return null;
        }
        String code = StringUtils.hasText(role.getRoleCode()) ? role.getRoleCode() : role.getRoleName();
        return StringUtils.hasText(code) ? code.trim().toUpperCase(Locale.ROOT) : null;
    }

    private String resolveRoleType(SysRole role) {
        if (role == null || !StringUtils.hasText(role.getRoleType())) {
            return RoleType.BUSINESS.getCode();
        }
        RoleType type = RoleType.fromCode(role.getRoleType());
        return type != null ? type.getCode() : RoleType.BUSINESS.getCode();
    }

    private DataScope resolveDataScope(SysRole role) {
        if (role == null) {
            return DataScope.SELF;
        }
        DataScope scope = DataScope.fromCode(role.getDataScope());
        return scope != null ? scope : DataScope.SELF;
    }

    private DataScope widenScope(DataScope current, DataScope candidate) {
        if (candidate == null) {
            return current;
        }
        if (current == null) {
            return candidate;
        }
        return scopeRank(candidate) > scopeRank(current) ? candidate : current;
    }

    private int scopeRank(DataScope scope) {
        if (scope == null) {
            return 0;
        }
        return switch (scope) {
            case CUSTOM -> 1;
            case SELF -> 2;
            case DEPARTMENT -> 3;
            case DEPARTMENT_AND_SUB -> 4;
            case ALL -> 5;
        };
    }

    private static class RoleAggregation {
        private final List<String> roleNames;
        private final List<String> roleCodes;
        private final List<String> roleTypes;
        private final DataScope dataScope;

        private RoleAggregation(List<String> roleNames, List<String> roleCodes, List<String> roleTypes, DataScope dataScope) {
            this.roleNames = roleNames;
            this.roleCodes = roleCodes;
            this.roleTypes = roleTypes;
            this.dataScope = dataScope == null ? DataScope.SELF : dataScope;
        }

        static RoleAggregation empty() {
            return new RoleAggregation(List.of(), List.of(), List.of(), DataScope.SELF);
        }

        List<String> getRoleNames() {
            return roleNames;
        }

        List<String> getRoleCodes() {
            return roleCodes;
        }

        List<String> getRoleTypes() {
            return roleTypes;
        }

        DataScope getDataScope() {
            return dataScope;
        }
    }

    @Data
    public static class LoginRequest {
        private String username;
        private String password;
    }

    @Data
    public static class RegisterRequest {
        private String username;
        private String password;
        private String role;
        private String idempotencyKey;
    }

    @Data
    public static class RefreshRequest {
        private String refreshToken;
    }

    private static final class LoginThrottleState {
        private int failedAttempts;
        private LocalDateTime firstFailureAt;
        private LocalDateTime lockedUntil;
    }
}
