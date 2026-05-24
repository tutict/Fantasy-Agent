package com.tutict.finalassignmentbackend.config.login.jwt;

import org.springframework.security.core.authority.SimpleGrantedAuthority;

import java.util.List;

public record AuthenticationSnapshot(
        Long userId,
        String username,
        List<String> authorities
) {
    public AuthenticationSnapshot {
        authorities = authorities == null ? List.of() : List.copyOf(authorities);
    }

    public List<SimpleGrantedAuthority> grantedAuthorities() {
        return authorities.stream()
                .map(SimpleGrantedAuthority::new)
                .toList();
    }
}
