package com.tutict.finalassignmentbackend.config.nativeimage;

import org.springframework.aot.hint.RuntimeHints;
import org.springframework.aot.hint.RuntimeHintsRegistrar;

public class ApplicationRuntimeHints implements RuntimeHintsRegistrar {

    @Override
    public void registerHints(RuntimeHints hints, ClassLoader classLoader) {
        hints.resources().registerPattern("python/*");
        hints.resources().registerPattern("elasticsearch/*");
        hints.resources().registerPattern("GRAALPY-VFS/**");
        hints.resources().registerPattern("org.graalvm.python.vfs/**");
    }
}
