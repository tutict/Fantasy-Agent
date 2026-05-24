package com.tutict.finalassignmentbackend.config;

import com.tutict.finalassignmentbackend.config.login.jwt.JwtAuthenticationFilter;
import com.tutict.finalassignmentbackend.config.login.jwt.AuthenticationSnapshotService;
import com.tutict.finalassignmentbackend.config.login.jwt.TokenProvider;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import com.tutict.finalassignmentbackend.config.tenant.TenantContextFilter;
import com.tutict.finalassignmentbackend.config.tenant.TenantIsolationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AnonymousAuthenticationFilter;

@Configuration
@EnableMethodSecurity(jsr250Enabled = true)
public class SecurityConfig {

    private final TokenProvider tokenProvider;
    private final AuthenticationSnapshotService authenticationSnapshotService;
    private final ProductGovernanceProperties productGovernanceProperties;
    private final TenantIsolationProperties tenantIsolationProperties;

    public SecurityConfig(TokenProvider tokenProvider,
                          AuthenticationSnapshotService authenticationSnapshotService,
                          ProductGovernanceProperties productGovernanceProperties,
                          TenantIsolationProperties tenantIsolationProperties) {
        this.tokenProvider = tokenProvider;
        this.authenticationSnapshotService = authenticationSnapshotService;
        this.productGovernanceProperties = productGovernanceProperties;
        this.tenantIsolationProperties = tenantIsolationProperties;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(authz -> authz
                        .requestMatchers(
                                "/api/auth/register",
                                "/api/auth/login",
                                "/api/auth/refresh",
                                "/actuator/health",
                                "/actuator/info"
                        ).permitAll()
                        .anyRequest().authenticated())
                .addFilterBefore(tenantContextFilter(), AnonymousAuthenticationFilter.class)
                .addFilterBefore(jwtAuthenticationFilter(), AnonymousAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public TenantContextFilter tenantContextFilter() {
        return new TenantContextFilter(productGovernanceProperties, tenantIsolationProperties, tokenProvider);
    }

    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter(tokenProvider, authenticationSnapshotService);
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
