package com.tutict.finalassignmentbackend.config.product;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Getter
@Setter
@Validated
@ConfigurationProperties(prefix = "app.operations")
public class OperationsProperties {

    @NotBlank
    private String backupDirectory = "./backups";

    @Min(1)
    @Max(3650)
    private int backupRetentionDays = 30;
}
