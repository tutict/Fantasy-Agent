package com.tutict.finalassignmentbackend.service.agent;

import java.util.List;
import java.util.Locale;

public record AgentSkillContext(
        String message,
        boolean webSearch,
        boolean authenticated,
        String username,
        Long userId,
        String realName,
        String idCardNumber,
        String department,
        List<String> roles
) {
    private static final List<String> PRIVILEGED_ROLES = List.of(
            "ROLE_SUPER_ADMIN",
            "ROLE_ADMIN",
            "ROLE_TRAFFIC_POLICE",
            "ROLE_FINANCE",
            "ROLE_APPEAL_REVIEWER"
    );

    public AgentSkillContext(String message, boolean webSearch) {
        this(message, webSearch, false, null, null, null, null, null, List.of());
    }

    public AgentSkillContext {
        roles = roles == null ? List.of() : List.copyOf(roles);
    }

    public String normalizedMessage() {
        return message == null ? "" : message.trim().toLowerCase(Locale.ROOT);
    }

    public boolean containsAny(String... keywords) {
        String normalized = normalizedMessage();
        for (String keyword : keywords) {
            if (keyword != null && !keyword.isBlank() && normalized.contains(keyword.toLowerCase(Locale.ROOT))) {
                return true;
            }
        }
        return false;
    }

    public boolean isAuthenticated() {
        return authenticated && username != null && !username.isBlank();
    }

    public boolean hasAnyRole(String... candidates) {
        if (roles.isEmpty() || candidates == null || candidates.length == 0) {
            return false;
        }
        for (String candidate : candidates) {
            if (candidate != null && roles.contains(candidate)) {
                return true;
            }
        }
        return false;
    }

    public boolean isPrivilegedOperator() {
        return PRIVILEGED_ROLES.stream().anyMatch(roles::contains);
    }

    public String operatorLabel() {
        if (!isAuthenticated()) {
            return "未登录访客";
        }
        String name = preferredName();
        return isPrivilegedOperator() ? "管理角色 " + name : "用户 " + name;
    }

    public String accessScopeLabel() {
        if (!isAuthenticated()) {
            return "未登录，不能校验真实业务数据。";
        }
        if (isPrivilegedOperator()) {
            return "当前具备管理权限，可按业务条件查询全局案件。";
        }
        return "当前仅返回本人名下、本人驾驶或本人申诉关联的案件记录。";
    }

    private String preferredName() {
        if (realName != null && !realName.isBlank()) {
            return realName + "(" + username + ")";
        }
        return username == null || username.isBlank() ? "unknown" : username;
    }
}
