package com.tutict.finalassignmentbackend.config.tenant;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Getter
@Setter
@Validated
@ConfigurationProperties(prefix = "app.tenant")
public class TenantIsolationProperties {

    @NotBlank
    private String tenantIdHeader = "X-Tenant-Id";

    @NotBlank
    private String organizationCodeHeader = "X-Organization-Code";

    @NotBlank
    private String regionCodeHeader = "X-Region-Code";

    @NotBlank
    private String departmentCodeHeader = "X-Department-Code";

    @NotBlank
    private String platformTenantId = "platform";
}
