package com.tutict.finalassignmentbackend.config.tenant;

import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.Arrays;
import java.util.stream.Collectors;

@Component("tenantCacheKeySupport")
public class TenantCacheKeySupport {

    private static final String GLOBAL_SCOPE = "global";
    private static final String UNKNOWN_SCOPE = "unknown";

    private final TenantAwareSupport tenantAwareSupport;

    public TenantCacheKeySupport(TenantAwareSupport tenantAwareSupport) {
        this.tenantAwareSupport = tenantAwareSupport;
    }

    public String scope(Object... segments) {
        String scope = resolveScope();
        if (segments == null || segments.length == 0) {
            return scope;
        }
        String suffix = Arrays.stream(segments)
                .map(this::normalize)
                .collect(Collectors.joining("::"));
        return scope + "::" + suffix;
    }

    private String resolveScope() {
        if (!tenantAwareSupport.isIsolationEnabled()) {
            return GLOBAL_SCOPE;
        }
        String tenantId = tenantAwareSupport.currentTenantId();
        return StringUtils.hasText(tenantId) ? tenantId.trim() : UNKNOWN_SCOPE;
    }

    private String normalize(Object segment) {
        if (segment == null) {
            return "null";
        }
        String normalized = String.valueOf(segment).trim();
        return normalized.isEmpty() ? "blank" : normalized;
    }
}
