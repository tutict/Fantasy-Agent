package com.tutict.finalassignmentbackend.config.product;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;

@Configuration
public class ProductGovernanceConfig {

    private static final Logger logger = LoggerFactory.getLogger(ProductGovernanceConfig.class);

    @Bean
    public ApplicationRunner validateProductGovernance(ProductGovernanceProperties productGovernanceProperties,
                                                       OperationsProperties operationsProperties,
                                                       Environment environment,
                                                       @Value("${jwt.secret.key:}") String jwtSecret,
                                                       @Value("${app.ai.search.enabled:false}") boolean aiSearchEnabled,
                                                       @Value("${app.bootstrap.admin.enabled:false}") boolean adminBootstrapEnabled,
                                                       @Value("${app.bootstrap.admin.password:}") String adminBootstrapPassword) {
        return _ -> {
            List<String> violations = new ArrayList<>();

            if (productGovernanceProperties.getEditionMode() == ProductGovernanceProperties.EditionMode.SAAS
                    && !productGovernanceProperties.isTenantIsolationEnabled()) {
                violations.add("SaaS edition requires app.product.tenant-isolation-enabled=true");
            }

            if (productGovernanceProperties.isCrossOrganizationAccessEnabled()) {
                violations.add("Cross-organization access must stay disabled for the standard product baseline");
            }

            ProductGovernanceProperties.Ai ai = productGovernanceProperties.getAi();
            if (!ai.isEnabled() && aiSearchEnabled) {
                violations.add("app.ai.search.enabled=true requires app.product.ai.enabled=true");
            }

            if (ai.isEnabled()) {
                if (!ai.isAdvisoryOnly()) {
                    violations.add("AI guardrail violation: app.product.ai.advisory-only must remain true");
                }
                if (!ai.isTraceableOutput()) {
                    violations.add("AI guardrail violation: app.product.ai.traceable-output must remain true");
                }
                if (!ai.isDisplaySources()) {
                    violations.add("AI guardrail violation: app.product.ai.display-sources must remain true");
                }
                if (!ai.isRedactSensitiveData()) {
                    violations.add("AI guardrail violation: app.product.ai.redact-sensitive-data must remain true");
                }
                if (!ai.isAuditableConfiguration()) {
                    violations.add("AI guardrail violation: app.product.ai.auditable-configuration must remain true");
                }
                if (!ai.isTenantCanDisable()) {
                    violations.add("AI guardrail violation: app.product.ai.tenant-can-disable must remain true");
                }
            }

            if (!StringUtils.hasText(operationsProperties.getBackupDirectory())) {
                violations.add("app.operations.backup-directory must not be blank");
            }

            if (environment.acceptsProfiles(Profiles.of("prod"))) {
                if (!StringUtils.hasText(jwtSecret) || jwtSecret.trim().length() < 32) {
                    violations.add("Production profile requires jwt.secret.key with at least 32 characters");
                }
                if (adminBootstrapEnabled && !StringUtils.hasText(adminBootstrapPassword)) {
                    violations.add("Production admin bootstrap requires app.bootstrap.admin.password");
                }
            }

            if (!violations.isEmpty()) {
                throw new IllegalStateException("Invalid product delivery configuration:\n - "
                        + String.join("\n - ", violations));
            }

            logger.info("Validated product governance editionMode={} aiEnabled={} tenantIsolationEnabled={} backupDirectory={}",
                    productGovernanceProperties.getEditionMode(),
                    ai.isEnabled(),
                    productGovernanceProperties.isTenantIsolationEnabled(),
                    operationsProperties.getBackupDirectory());
        };
    }
}
