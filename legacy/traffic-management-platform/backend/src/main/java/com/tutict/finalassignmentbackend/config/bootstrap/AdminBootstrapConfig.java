package com.tutict.finalassignmentbackend.config.bootstrap;

import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.SysUserRole;
import com.tutict.finalassignmentbackend.enums.RoleType;
import com.tutict.finalassignmentbackend.service.SysRoleService;
import com.tutict.finalassignmentbackend.service.SysUserRoleService;
import com.tutict.finalassignmentbackend.service.SysUserService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.LocalDateTime;
import java.util.List;

@Configuration
public class AdminBootstrapConfig {

    private static final Logger logger = LoggerFactory.getLogger(AdminBootstrapConfig.class);
    private static final String DEFAULT_ROLE_CODE = "ADMIN";
    private static final String DEFAULT_ROLE_NAME = "System Administrator";
    private static final String DEFAULT_USERNAME = "admin";
    private static final String SYSTEM_OPERATOR = "system-bootstrap";

    @Bean
    public CommandLineRunner bootstrapAdminAccount(SysRoleService sysRoleService,
                                                   SysUserService sysUserService,
                                                   SysUserRoleService sysUserRoleService,
                                                   @Value("${app.bootstrap.admin.enabled:false}") boolean enabled,
                                                   @Value("${app.bootstrap.admin.username:" + DEFAULT_USERNAME + "}") String username,
                                                   @Value("${app.bootstrap.admin.password:}") String password) {
        return _ -> {
            if (!enabled) {
                logger.info("Admin bootstrap is disabled");
                return;
            }

            String normalizedUsername = normalize(username, DEFAULT_USERNAME);
            String normalizedPassword = password == null ? "" : password.trim();
            if (normalizedPassword.isEmpty()) {
                logger.warn("Admin bootstrap skipped because configured password is blank");
                return;
            }

            SysRole adminRole = ensureAdminRole(sysRoleService);
            SysUser adminUser = ensureAdminUser(sysUserService, normalizedUsername, normalizedPassword);
            ensureAdminBinding(sysUserRoleService, adminUser, adminRole);

            logger.info("Admin bootstrap ensured account username={} roleCode={}", normalizedUsername, DEFAULT_ROLE_CODE);
        };
    }

    private SysRole ensureAdminRole(SysRoleService sysRoleService) {
        SysRole existing = sysRoleService.findByRoleCode(DEFAULT_ROLE_CODE);
        if (existing != null) {
            return existing;
        }

        SysRole role = new SysRole();
        role.setRoleCode(DEFAULT_ROLE_CODE);
        role.setRoleName(DEFAULT_ROLE_NAME);
        role.setRoleType(RoleType.SYSTEM.getCode());
        role.setRoleDescription("System administrator role");
        role.setDataScope("All");
        role.setStatus("Active");
        role.setSortOrder(1);
        role.setCreatedAt(LocalDateTime.now());
        role.setUpdatedAt(LocalDateTime.now());
        role.setCreatedBy(SYSTEM_OPERATOR);
        role.setUpdatedBy(SYSTEM_OPERATOR);
        role.setRemarks("Bootstrap default admin role");
        return sysRoleService.createSysRole(role);
    }

    private SysUser ensureAdminUser(SysUserService sysUserService, String username, String password) {
        SysUser existing = sysUserService.findByUsername(username);
        if (existing != null) {
            return existing;
        }

        SysUser user = new SysUser();
        user.setUsername(username);
        user.setPassword(password);
        user.setRealName(DEFAULT_ROLE_NAME);
        user.setDepartment("Platform Operations");
        user.setPosition(DEFAULT_ROLE_CODE);
        user.setEmployeeNumber("ADMIN-0001");
        user.setStatus("Active");
        user.setLoginFailures(0);
        user.setPasswordUpdateTime(LocalDateTime.now());
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());
        user.setCreatedBy(SYSTEM_OPERATOR);
        user.setUpdatedBy(SYSTEM_OPERATOR);
        user.setRemarks("Bootstrap default admin account");
        return sysUserService.createSysUser(user);
    }

    private void ensureAdminBinding(SysUserRoleService sysUserRoleService, SysUser adminUser, SysRole adminRole) {
        List<SysUserRole> relations = sysUserRoleService.findByUserIdAndRoleId(
                adminUser.getUserId(), adminRole.getRoleId(), 1, 1);
        if (!relations.isEmpty()) {
            return;
        }

        SysUserRole relation = new SysUserRole();
        relation.setUserId(adminUser.getUserId());
        relation.setRoleId(adminRole.getRoleId());
        relation.setCreatedAt(LocalDateTime.now());
        relation.setCreatedBy(SYSTEM_OPERATOR);
        sysUserRoleService.createRelation(relation);
    }

    private String normalize(String value, String fallback) {
        if (value == null || value.trim().isEmpty()) {
            return fallback;
        }
        return value.trim();
    }
}
