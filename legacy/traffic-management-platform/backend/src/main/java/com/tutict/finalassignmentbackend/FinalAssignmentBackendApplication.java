package com.tutict.finalassignmentbackend;

import com.tutict.finalassignmentbackend.config.docker.RunDocker;
import com.tutict.finalassignmentbackend.config.nativeimage.ApplicationRuntimeHints;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.context.annotation.EnableAspectJAutoProxy;
import org.springframework.context.annotation.ImportRuntimeHints;
import org.springframework.scheduling.annotation.EnableAsync;

@EnableAsync
@EnableAspectJAutoProxy
@SpringBootApplication
@ConfigurationPropertiesScan
@MapperScan(
        basePackages = "com.tutict.finalassignmentbackend.mapper",
        sqlSessionTemplateRef = "sqlSessionTemplate"
)
@ImportRuntimeHints(ApplicationRuntimeHints.class)
public class FinalAssignmentBackendApplication {

    public static void main(String[] args) {
        new SpringApplicationBuilder(FinalAssignmentBackendApplication.class)
                .initializers(new RunDocker())
                .run(args);
    }

}
