package com.tutict.finalassignmentbackend.config.product;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Getter
@Setter
@Validated
@ConfigurationProperties(prefix = "app.product")
public class ProductGovernanceProperties {

    @NotNull
    private EditionMode editionMode = EditionMode.GOV;

    private boolean tenantIsolationEnabled = true;

    private boolean crossOrganizationAccessEnabled = false;

    @Valid
    private Ai ai = new Ai();

    @Valid
    private Seed seed = new Seed();

    public enum EditionMode {
        GOV,
        SAAS
    }

    @Getter
    @Setter
    public static class Ai {
        private boolean enabled = false;
        private boolean advisoryOnly = true;
        private boolean traceableOutput = true;
        private boolean displaySources = true;
        private boolean redactSensitiveData = true;
        private boolean auditableConfiguration = true;
        private boolean tenantCanDisable = true;
    }

    @Getter
    @Setter
    public static class Seed {
        private boolean standardEnabled = true;
    }
}
