package com.tutict.finalassignmentbackend.config.tenant;

public final class TenantContextHolder {

    private static final ThreadLocal<TenantRequestContext> CONTEXT = new ThreadLocal<>();

    private TenantContextHolder() {
    }

    public static void set(TenantRequestContext context) {
        if (context == null) {
            CONTEXT.remove();
            return;
        }
        CONTEXT.set(context);
    }

    public static TenantRequestContext get() {
        return CONTEXT.get();
    }

    public static String getTenantId() {
        TenantRequestContext context = get();
        return context == null ? null : context.tenantId();
    }

    public static String getOrganizationCode() {
        TenantRequestContext context = get();
        return context == null ? null : context.organizationCode();
    }

    public static String getRegionCode() {
        TenantRequestContext context = get();
        return context == null ? null : context.regionCode();
    }

    public static String getDepartmentCode() {
        TenantRequestContext context = get();
        return context == null ? null : context.departmentCode();
    }

    public static boolean hasContext() {
        return CONTEXT.get() != null;
    }

    public static void clear() {
        CONTEXT.remove();
    }
}
