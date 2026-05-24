package com.tutict.finalassignmentbackend.config.shell;

import com.tutict.finalassignmentbackend.service.agent.AgentSkill;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class ShellScriptConfig {

    private static final Logger logger = LoggerFactory.getLogger(ShellScriptConfig.class);

    @Bean
    public CommandLineRunner logRegisteredSkills(List<AgentSkill> skills) {
        return _ -> logger.info("Traffic agent started with skills: {}", skills.stream().map(AgentSkill::id).toList());
    }
}
