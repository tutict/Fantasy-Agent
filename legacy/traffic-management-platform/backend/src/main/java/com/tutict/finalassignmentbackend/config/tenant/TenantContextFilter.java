package com.tutict.finalassignmentbackend.config.tenant;

import com.tutict.finalassignmentbackend.config.login.jwt.TokenProvider;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.jetbrains.annotations.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Set;

public class TenantContextFilter extends OncePerRequestFilter {

    private static final Set<String> EXCLUDED_PREFIXES = Set.of(
            "/actuator",
            "/swagger-ui",
            "/v3/api-docs",
            "/error"
    );

    private final ProductGovernanceProperties productGovernanceProperties;
    private final TenantIsolationProperties tenantIsolationProperties;
    private final TokenProvider tokenProvider;

    public TenantContextFilter(ProductGovernanceProperties productGovernanceProperties,
                               TenantIsolationProperties tenantIsolationProperties,
                               TokenProvider tokenProvider) {
        this.productGovernanceProperties = productGovernanceProperties;
        this.tenantIsolationProperties = tenantIsolationProperties;
        this.tokenProvider = tokenProvider;
    }

    @Override
    protected void doFilterInternal(@NotNull HttpServletRequest request,
                                    @NotNull HttpServletResponse response,
                                    @NotNull FilterChain filterChain) throws ServletException, IOException {
        try {
            TenantRequestContext resolved;
            try {
                resolved = resolveContext(request);
            } catch (IllegalStateException ex) {
                response.setStatus(HttpStatus.FORBIDDEN.value());
                response.setContentType("application/json;charset=UTF-8");
                response.getWriter().write(("""
                        {"message":"%s","status":403}
                        """).formatted(sanitizeForJson(ex.getMessage())));
                return;
            }

            if (resolved != null) {
                TenantContextHolder.set(resolved);
            }

            if (requiresTenantContext(request) && !StringUtils.hasText(TenantContextHolder.getTenantId())) {
                response.setStatus(HttpStatus.BAD_REQUEST.value());
                response.setContentType("application/json;charset=UTF-8");
                response.getWriter().write("""
                        {"message":"Missing tenant context for SaaS request","status":400}
                        """.trim());
                return;
            }

            filterChain.doFilter(request, response);
        } finally {
            TenantContextHolder.clear();
        }
    }

    private TenantRequestContext resolveContext(HttpServletRequest request) {
        String headerTenantId = normalize(request.getHeader(tenantIsolationProperties.getTenantIdHeader()));
        String headerOrganizationCode = normalize(request.getHeader(tenantIsolationProperties.getOrganizationCodeHeader()));
        String headerRegionCode = normalize(request.getHeader(tenantIsolationProperties.getRegionCodeHeader()));
        String headerDepartmentCode = normalize(request.getHeader(tenantIsolationProperties.getDepartmentCodeHeader()));

        String token = getJwtFromRequest(request);
        if (StringUtils.hasText(token) && tokenProvider.validateToken(token) && tokenProvider.isAccessToken(token)) {
            String tokenTenantId = normalize(tokenProvider.getTenantId(token));
            if (StringUtils.hasText(tokenTenantId)) {
                TenantRequestContext tokenContext = new TenantRequestContext(
                        tokenTenantId,
                        normalize(tokenProvider.getOrganizationCode(token)),
                        normalize(tokenProvider.getRegionCode(token)),
                        normalize(tokenProvider.getDepartmentCode(token)),
                        TenantRequestContext.Source.TOKEN
                );
                validateHeaderOverrides(tokenContext,
                        headerTenantId,
                        headerOrganizationCode,
                        headerRegionCode,
                        headerDepartmentCode);
                return tokenContext;
            }
        }

        if (StringUtils.hasText(headerTenantId)) {
            return new TenantRequestContext(
                    headerTenantId,
                    headerOrganizationCode,
                    headerRegionCode,
                    headerDepartmentCode,
                    TenantRequestContext.Source.HEADER
            );
        }

        return null;
    }

    private void validateHeaderOverrides(TenantRequestContext tokenContext,
                                         String headerTenantId,
                                         String headerOrganizationCode,
                                         String headerRegionCode,
                                         String headerDepartmentCode) {
        if (tokenContext == null) {
            return;
        }
        ensureNoConflict("tenant",
                tokenContext.tenantId(),
                headerTenantId);
        ensureNoConflict("organization",
                tokenContext.organizationCode(),
                headerOrganizationCode);
        ensureNoConflict("region",
                tokenContext.regionCode(),
                headerRegionCode);
        ensureNoConflict("department",
                tokenContext.departmentCode(),
                headerDepartmentCode);
    }

    private void ensureNoConflict(String dimension, String tokenValue, String headerValue) {
        if (StringUtils.hasText(headerValue)
                && StringUtils.hasText(tokenValue)
                && !tokenValue.equals(headerValue)) {
            throw new IllegalStateException("Tenant context header does not match authenticated " + dimension + " scope");
        }
    }

    private boolean requiresTenantContext(HttpServletRequest request) {
        return productGovernanceProperties.getEditionMode() == ProductGovernanceProperties.EditionMode.SAAS
                && productGovernanceProperties.isTenantIsolationEnabled()
                && !isExcluded(request.getRequestURI());
    }

    private boolean isExcluded(String requestUri) {
        if (!StringUtils.hasText(requestUri)) {
            return true;
        }
        return EXCLUDED_PREFIXES.stream().anyMatch(requestUri::startsWith);
    }

    private String getJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }

    private String normalize(String value) {
        return StringUtils.hasText(value) ? value.trim() : null;
    }

    private String sanitizeForJson(String value) {
        if (!StringUtils.hasText(value)) {
            return "Forbidden";
        }
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
