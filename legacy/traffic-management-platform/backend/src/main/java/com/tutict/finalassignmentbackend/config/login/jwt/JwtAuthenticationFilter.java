package com.tutict.finalassignmentbackend.config.login.jwt;

import org.jetbrains.annotations.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger logger = LoggerFactory.getLogger(JwtAuthenticationFilter.class);

    private final TokenProvider tokenProvider;
    private final AuthenticationSnapshotService authenticationSnapshotService;

    public JwtAuthenticationFilter(TokenProvider tokenProvider,
                                   AuthenticationSnapshotService authenticationSnapshotService) {
        this.tokenProvider = tokenProvider;
        this.authenticationSnapshotService = authenticationSnapshotService;
    }

    @Override
    protected void doFilterInternal(@NotNull HttpServletRequest request, @NotNull HttpServletResponse response, @NotNull FilterChain filterChain)
            throws ServletException, IOException {
        String jwt = getJwtFromRequest(request);

        if (jwt != null && tokenProvider.validateToken(jwt) && tokenProvider.isAccessToken(jwt)) {
            String username = tokenProvider.getUsernameFromToken(jwt);
            AuthenticationSnapshot snapshot = authenticationSnapshotService.findActiveSnapshotByUsername(username);
            if (snapshot != null) {
                UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(snapshot.username(), null, snapshot.grantedAuthorities());
                SecurityContextHolder.getContext().setAuthentication(authentication);
            } else {
                SecurityContextHolder.clearContext();
                logger.warn("Rejected JWT for missing or inactive user: {}", username);
            }
        } else if (jwt != null) {
            SecurityContextHolder.clearContext();
            logger.warn("Invalid or missing JWT in request: {}", request.getRequestURI());
        }

        filterChain.doFilter(request, response);
    }

    private String getJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}
