package com.tutict.finalassignmentbackend.config.tenant;

public record TenantRequestContext(
        String tenantId,
        String organizationCode,
        String regionCode,
        String departmentCode,
        Source source
) {
    public enum Source {
        HEADER,
        TOKEN,
        SYSTEM
    }
}
