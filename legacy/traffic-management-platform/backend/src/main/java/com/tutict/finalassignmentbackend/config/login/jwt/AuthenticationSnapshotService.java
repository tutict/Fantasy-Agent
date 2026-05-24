package com.tutict.finalassignmentbackend.config.login.jwt;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.tutict.finalassignmentbackend.config.tenant.TenantAwareSupport;
import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.SysUserRole;
import com.tutict.finalassignmentbackend.mapper.SysRoleMapper;
import com.tutict.finalassignmentbackend.mapper.SysUserMapper;
import com.tutict.finalassignmentbackend.mapper.SysUserRoleMapper;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;

@Service
public class AuthenticationSnapshotService {

    public static final String CACHE_NAME = "authSnapshotCache";

    private final SysUserMapper sysUserMapper;
    private final SysUserRoleMapper sysUserRoleMapper;
    private final SysRoleMapper sysRoleMapper;
    private final CacheManager caffeineCacheManager;
    private final TenantAwareSupport tenantAwareSupport;

    public AuthenticationSnapshotService(SysUserMapper sysUserMapper,
                                         SysUserRoleMapper sysUserRoleMapper,
                                         SysRoleMapper sysRoleMapper,
                                         @Qualifier("caffeineCacheManager") CacheManager caffeineCacheManager,
                                         TenantAwareSupport tenantAwareSupport) {
        this.sysUserMapper = sysUserMapper;
        this.sysUserRoleMapper = sysUserRoleMapper;
        this.sysRoleMapper = sysRoleMapper;
        this.caffeineCacheManager = caffeineCacheManager;
        this.tenantAwareSupport = tenantAwareSupport;
    }

    @Transactional(readOnly = true)
    @Cacheable(
            cacheNames = CACHE_NAME,
            key = "@tenantCacheKeySupport.scope('authSnapshot', #username)",
            cacheManager = "caffeineCacheManager",
            unless = "#result == null")
    public AuthenticationSnapshot findActiveSnapshotByUsername(String username) {
        String normalizedUsername = normalizeUsername(username);
        if (normalizedUsername == null) {
            return null;
        }

        QueryWrapper<SysUser> userQuery = new QueryWrapper<>();
        userQuery.eq("username", normalizedUsername).last("limit 1");
        if (tenantAwareSupport != null) {
            tenantAwareSupport.applyTenantScope(userQuery);
        }
        SysUser user = sysUserMapper.selectOne(userQuery);
        if (user == null || !isUserActive(user)) {
            return null;
        }

        return new AuthenticationSnapshot(
                user.getUserId(),
                user.getUsername(),
                resolveAuthorities(user.getUserId())
        );
    }

    public void evictAll() {
        Cache cache = caffeineCacheManager.getCache(CACHE_NAME);
        if (cache != null) {
            cache.clear();
        }
    }

    private List<String> resolveAuthorities(Long userId) {
        if (userId == null) {
            return List.of();
        }

        QueryWrapper<SysUserRole> relationQuery = new QueryWrapper<>();
        relationQuery.select("role_id").eq("user_id", userId);
        List<SysUserRole> relations = sysUserRoleMapper.selectList(relationQuery);
        if (relations == null || relations.isEmpty()) {
            return List.of();
        }

        Set<Integer> roleIds = relations.stream()
                .map(SysUserRole::getRoleId)
                .filter(Objects::nonNull)
                .collect(LinkedHashSet::new, Set::add, Set::addAll);
        if (roleIds.isEmpty()) {
            return List.of();
        }

        return sysRoleMapper.selectBatchIds(roleIds).stream()
                .filter(Objects::nonNull)
                .filter(this::isRoleActive)
                .map(SysRole::getRoleCode)
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(roleCode -> !roleCode.isEmpty())
                .map(roleCode -> "ROLE_" + roleCode.toUpperCase(Locale.ROOT))
                .distinct()
                .toList();
    }

    private boolean isUserActive(SysUser user) {
        String status = user.getStatus();
        return status == null || status.isBlank() || "active".equalsIgnoreCase(status.trim());
    }

    private boolean isRoleActive(SysRole role) {
        if (role.getDeletedAt() != null) {
            return false;
        }
        String status = role.getStatus();
        return status == null || status.isBlank() || "active".equalsIgnoreCase(status.trim());
    }

    private String normalizeUsername(String username) {
        if (username == null) {
            return null;
        }
        String normalized = username.trim();
        return normalized.isEmpty() ? null : normalized;
    }
}
