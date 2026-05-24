package com.tutict.finalassignmentbackend.service.agent;

import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.service.SysUserService;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class AgentUserContextResolver {

    private final SysUserService sysUserService;

    public AgentUserContextResolver(SysUserService sysUserService) {
        this.sysUserService = sysUserService;
    }

    public AgentSkillContext resolve(String message, boolean webSearch) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken) {
            return new AgentSkillContext(message, webSearch);
        }

        String username = authentication.getName();
        List<String> roles = authentication.getAuthorities().stream()
                .map(grantedAuthority -> grantedAuthority == null ? null : grantedAuthority.getAuthority())
                .filter(authority -> authority != null && !authority.isBlank())
                .distinct()
                .toList();

        SysUser sysUser = sysUserService.findByUsername(username);
        if (sysUser == null) {
            return new AgentSkillContext(message, webSearch, true, username, null, null, null, null, roles);
        }

        return new AgentSkillContext(
                message,
                webSearch,
                true,
                username,
                sysUser.getUserId(),
                sysUser.getRealName(),
                sysUser.getIdCardNumber(),
                sysUser.getDepartment(),
                roles
        );
    }
}
