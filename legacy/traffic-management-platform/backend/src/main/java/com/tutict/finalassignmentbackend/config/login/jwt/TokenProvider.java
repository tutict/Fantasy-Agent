package com.tutict.finalassignmentbackend.config.login.jwt;

import com.tutict.finalassignmentbackend.enums.DataScope;
import com.tutict.finalassignmentbackend.enums.RoleType;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.Getter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;

@Service
public class TokenProvider {

    private static final Logger LOG = Logger.getLogger(TokenProvider.class.getName());
    private static final long ACCESS_TOKEN_EXPIRATION_MS = 86400000L;
    private static final long REFRESH_TOKEN_EXPIRATION_MS = 604800000L;
    private static final String CLAIM_ROLES = "roles";
    private static final String CLAIM_ROLE_TYPES = "roleTypes";
    private static final String CLAIM_DATA_SCOPE = "dataScope";
    private static final String CLAIM_TOKEN_TYPE = "tokenType";
    private static final String CLAIM_TENANT_ID = "tenantId";
    private static final String CLAIM_ORGANIZATION_CODE = "organizationCode";
    private static final String CLAIM_REGION_CODE = "regionCode";
    private static final String CLAIM_DEPARTMENT_CODE = "departmentCode";
    private static final String TOKEN_TYPE_ACCESS = "access";
    private static final String TOKEN_TYPE_REFRESH = "refresh";

    @Value("${jwt.secret.key}")
    private String base64Secret;

    private SecretKey secretKey;

    private static final Map<String, RoleMetadata> ROLE_SCHEMA;

    static {
        Map<String, RoleMetadata> schema = new LinkedHashMap<>();
        schema.put("USER", new RoleMetadata(RoleType.CUSTOM, DataScope.SELF));
        schema.put("SUPER_ADMIN", new RoleMetadata(RoleType.SYSTEM, DataScope.ALL));
        schema.put("ADMIN", new RoleMetadata(RoleType.SYSTEM, DataScope.ALL));
        schema.put("CASE_OFFICER", new RoleMetadata(RoleType.BUSINESS, DataScope.DEPARTMENT_AND_SUB));
        schema.put("REVIEW_OFFICER", new RoleMetadata(RoleType.BUSINESS, DataScope.DEPARTMENT_AND_SUB));
        schema.put("CASHIER", new RoleMetadata(RoleType.BUSINESS, DataScope.DEPARTMENT));
        schema.put("AUDITOR", new RoleMetadata(RoleType.BUSINESS, DataScope.ALL));
        schema.put("OPS_ANALYST", new RoleMetadata(RoleType.BUSINESS, DataScope.ALL));
        schema.put("TRAFFIC_POLICE", new RoleMetadata(RoleType.BUSINESS, DataScope.DEPARTMENT));
        schema.put("FINANCE", new RoleMetadata(RoleType.BUSINESS, DataScope.DEPARTMENT));
        schema.put("APPEAL_REVIEWER", new RoleMetadata(RoleType.BUSINESS, DataScope.DEPARTMENT));
        ROLE_SCHEMA = Collections.unmodifiableMap(schema);
    }

    @PostConstruct
    public void init() {
        String normalizedSecret = base64Secret == null ? "" : base64Secret.trim();
        if (normalizedSecret.isEmpty()) {
            throw new IllegalStateException("Property jwt.secret.key must be configured via APP_JWT_SECRET_KEY");
        }
        byte[] keyBytes;
        try {
            keyBytes = Base64.getDecoder().decode(normalizedSecret);
        } catch (IllegalArgumentException ex) {
            throw new IllegalStateException("Property jwt.secret.key must be a valid Base64-encoded key", ex);
        }
        if (keyBytes.length < 32) {
            throw new IllegalStateException("Property jwt.secret.key must decode to at least 32 bytes");
        }
        this.secretKey = Keys.hmacShaKeyFor(keyBytes);
        LOG.info("TokenProvider initialized with HS256 secret key");
    }

    public String createToken(String username, String roles) {
        return createToken(username, roles, null, null, null, null);
    }

    public String createToken(String username,
                              String roles,
                              String tenantId,
                              String organizationCode,
                              String regionCode,
                              String departmentCode) {
        if (!validateRoleCodes(roles)) {
            throw new IllegalArgumentException("Invalid role codes provided for token creation");
        }
        Map<String, Object> claims = new LinkedHashMap<>();
        claims.put(CLAIM_ROLES, String.join(",", normalizeRoleCodes(roles)));
        claims.put(CLAIM_TOKEN_TYPE, TOKEN_TYPE_ACCESS);
        putOptionalClaim(claims, CLAIM_TENANT_ID, tenantId);
        putOptionalClaim(claims, CLAIM_ORGANIZATION_CODE, organizationCode);
        putOptionalClaim(claims, CLAIM_REGION_CODE, regionCode);
        putOptionalClaim(claims, CLAIM_DEPARTMENT_CODE, departmentCode);
        return buildSignedToken(username, ACCESS_TOKEN_EXPIRATION_MS, claims);
    }

    public String createEnhancedToken(String username, String roleCodes, String roleTypes, String dataScope) {
        return createEnhancedToken(username, roleCodes, roleTypes, dataScope, null, null, null, null);
    }

    public String createEnhancedToken(String username,
                                      String roleCodes,
                                      String roleTypes,
                                      String dataScope,
                                      String tenantId,
                                      String organizationCode,
                                      String regionCode,
                                      String departmentCode) {
        if (!validateRoleClaims(roleCodes, roleTypes, dataScope)) {
            throw new IllegalArgumentException("Role claims do not match the database schema");
        }
        Map<String, Object> claims = new LinkedHashMap<>();
        claims.put(CLAIM_ROLES, String.join(",", normalizeRoleCodes(roleCodes)));
        claims.put(CLAIM_ROLE_TYPES, roleTypes);
        claims.put(CLAIM_DATA_SCOPE, dataScope);
        claims.put(CLAIM_TOKEN_TYPE, TOKEN_TYPE_ACCESS);
        putOptionalClaim(claims, CLAIM_TENANT_ID, tenantId);
        putOptionalClaim(claims, CLAIM_ORGANIZATION_CODE, organizationCode);
        putOptionalClaim(claims, CLAIM_REGION_CODE, regionCode);
        putOptionalClaim(claims, CLAIM_DEPARTMENT_CODE, departmentCode);
        return buildSignedToken(username, ACCESS_TOKEN_EXPIRATION_MS, claims);
    }

    public String createRefreshToken(String username) {
        Map<String, Object> claims = new LinkedHashMap<>();
        claims.put(CLAIM_TOKEN_TYPE, TOKEN_TYPE_REFRESH);
        return buildSignedToken(username, REFRESH_TOKEN_EXPIRATION_MS, claims);
    }

    public boolean validateToken(String token) {
        try {
            parseClaims(token);
            return true;
        } catch (JwtException e) {
            LOG.log(Level.WARNING, "Invalid token: " + e.getMessage(), e);
            return false;
        }
    }

    public boolean isRefreshToken(String token) {
        return hasTokenType(token, TOKEN_TYPE_REFRESH);
    }

    public boolean isAccessToken(String token) {
        return hasTokenType(token, TOKEN_TYPE_ACCESS);
    }

    private boolean hasTokenType(String token, String expectedType) {
        try {
            return expectedType.equalsIgnoreCase(parseClaims(token).get(CLAIM_TOKEN_TYPE, String.class));
        } catch (JwtException e) {
            LOG.log(Level.WARNING, "Failed to inspect token type: " + e.getMessage(), e);
            return false;
        }
    }

    public List<String> extractRoles(String token) {
        try {
            String roles = parseClaims(token).get(CLAIM_ROLES, String.class);
            if (roles == null || roles.isEmpty()) {
                return List.of();
            }
            return normalizeRoleCodes(roles).stream()
                    .filter(this::isRoleDefined)
                    .map(role -> "ROLE_" + role)
                    .collect(Collectors.toList());
        } catch (JwtException e) {
            LOG.log(Level.WARNING, "Failed to extract roles from token: " + e.getMessage(), e);
            return List.of();
        }
    }

    public String getUsernameFromToken(String token) {
        return parseClaims(token).getSubject();
    }

    public String getTenantId(String token) {
        return parseClaims(token).get(CLAIM_TENANT_ID, String.class);
    }

    public String getOrganizationCode(String token) {
        return parseClaims(token).get(CLAIM_ORGANIZATION_CODE, String.class);
    }

    public String getRegionCode(String token) {
        return parseClaims(token).get(CLAIM_REGION_CODE, String.class);
    }

    public String getDepartmentCode(String token) {
        return parseClaims(token).get(CLAIM_DEPARTMENT_CODE, String.class);
    }

    public List<RoleType> extractRoleTypes(String token) {
        try {
            String roleTypes = parseClaims(token).get(CLAIM_ROLE_TYPES, String.class);
            if (roleTypes == null || roleTypes.isEmpty()) {
                return List.of();
            }
            return Arrays.stream(roleTypes.split(","))
                    .map(String::trim)
                    .map(RoleType::fromCode)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (JwtException e) {
            LOG.log(Level.WARNING, "Failed to extract role types from token: " + e.getMessage(), e);
            return List.of();
        }
    }

    public DataScope extractDataScope(String token) {
        try {
            return DataScope.fromCode(parseClaims(token).get(CLAIM_DATA_SCOPE, String.class));
        } catch (JwtException e) {
            LOG.log(Level.WARNING, "Failed to extract data scope from token: " + e.getMessage(), e);
            return null;
        }
    }

    public boolean hasRoleType(String token, RoleType roleType) {
        return extractRoleTypes(token).contains(roleType);
    }

    public boolean hasSystemRole(String token) {
        return hasRoleType(token, RoleType.SYSTEM);
    }

    public boolean hasBusinessRole(String token) {
        return hasRoleType(token, RoleType.BUSINESS);
    }

    public boolean hasDataScopePermission(String token, DataScope requiredDataScope) {
        DataScope userDataScope = extractDataScope(token);
        return userDataScope != null && userDataScope.includes(requiredDataScope);
    }

    public boolean validateRoleCodes(String roleCodes) {
        List<String> normalized = normalizeRoleCodes(roleCodes);
        if (normalized.isEmpty()) {
            return false;
        }
        boolean valid = normalized.stream().allMatch(this::isRoleDefined);
        if (!valid) {
            LOG.log(Level.WARNING, "Detected undefined role codes: {0}", normalized);
        }
        return valid;
    }

    public boolean validateRoleClaims(String roleCodes, String roleTypes, String dataScope) {
        if (!validateRoleCodes(roleCodes)) {
            return false;
        }
        if (!validateRoleTypes(roleTypes) || !validateDataScope(dataScope)) {
            return false;
        }

        DataScope requestedScope = DataScope.fromCode(dataScope);
        if (requestedScope == null) {
            return false;
        }

        Set<RoleType> requestedTypes = Arrays.stream(roleTypes.split(","))
                .map(String::trim)
                .map(RoleType::fromCode)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        for (String roleCode : normalizeRoleCodes(roleCodes)) {
            RoleMetadata metadata = ROLE_SCHEMA.get(roleCode);
            if (metadata == null) {
                LOG.log(Level.WARNING, "Role {0} not defined in schema", roleCode);
                return false;
            }
            if (!requestedTypes.contains(metadata.getRoleType())) {
                LOG.log(Level.WARNING,
                        "Role type {0} missing from claim for role {1}",
                        new Object[]{metadata.getRoleType().getCode(), roleCode});
                return false;
            }
            if (!requestedScope.includes(metadata.getDataScope())) {
                LOG.log(Level.WARNING,
                        "Data scope {0} does not cover required scope {1} for role {2}",
                        new Object[]{requestedScope.getCode(), metadata.getDataScope().getCode(), roleCode});
                return false;
            }
        }

        return true;
    }

    public boolean validateRoleTypes(String roleTypes) {
        if (roleTypes == null || roleTypes.trim().isEmpty()) {
            return false;
        }
        return Arrays.stream(roleTypes.split(","))
                .map(String::trim)
                .allMatch(RoleType::isValid);
    }

    public boolean validateDataScope(String dataScope) {
        return DataScope.isValid(dataScope);
    }

    private Claims parseClaims(String token) {
        return Jwts.parser()
                .verifyWith(secretKey)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    private String buildSignedToken(String username, long expirationMs, Map<String, Object> claims) {
        long now = System.currentTimeMillis();
        Date expirationDate = new Date(now + expirationMs);
        var builder = Jwts.builder()
                .subject(username)
                .issuedAt(new Date(now))
                .expiration(expirationDate);
        if (claims != null) {
            claims.forEach(builder::claim);
        }
        return builder.signWith(secretKey).compact();
    }

    private List<String> normalizeRoleCodes(String roleCodes) {
        if (roleCodes == null) {
            return List.of();
        }
        return Arrays.stream(roleCodes.split(","))
                .map(code -> code.trim().toUpperCase(Locale.ROOT))
                .filter(code -> !code.isEmpty())
                .collect(Collectors.toList());
    }

    private void putOptionalClaim(Map<String, Object> claims, String key, String value) {
        if (claims == null || key == null || value == null || value.trim().isEmpty()) {
            return;
        }
        claims.put(key, value.trim());
    }

    private boolean isRoleDefined(String roleCode) {
        return ROLE_SCHEMA.containsKey(roleCode);
    }

    @Getter
    private static final class RoleMetadata {
        private final RoleType roleType;
        private final DataScope dataScope;

        private RoleMetadata(RoleType roleType, DataScope dataScope) {
            this.roleType = roleType;
            this.dataScope = dataScope;
        }
    }
}
