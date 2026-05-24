package com.tutict.finalassignmentbackend.config.ai.chat;

import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

@Component
public class GraalPyContext {

    private final Context context;

    public GraalPyContext() {
        try {
            String os = System.getProperty("os.name").toLowerCase();
            Path venvDir = locateExistingPath(List.of(
                    Path.of(System.getProperty("user.dir"), "target", "classes", "GRAALPY-VFS", "com.tutict", "finalAssignmentBackend", "venv"),
                    Path.of(System.getProperty("user.dir"), "backend", "target", "classes", "GRAALPY-VFS", "com.tutict", "finalAssignmentBackend", "venv"),
                    Path.of(System.getProperty("user.dir"), "target", "classes", "org.graalvm.python.vfs", "venv"),
                    Path.of(System.getProperty("user.dir"), "backend", "target", "classes", "org.graalvm.python.vfs", "venv")
            ), "GraalPy virtual environment");

            Path pythonDir = locateExistingPath(List.of(
                    Path.of(System.getProperty("user.dir"), "src", "main", "resources", "python"),
                    Path.of(System.getProperty("user.dir"), "backend", "src", "main", "resources", "python")
            ), "Python skill resources");

            String sitePackagesPath = resolveSitePackagesPath(venvDir, os).toString();
            String executablePath = resolveExecutablePath(venvDir, os).toString();
            String pythonPath = sitePackagesPath + File.pathSeparator + pythonDir;

            context = Context.newBuilder("python")
                    .option("python.PythonPath", pythonPath)
                    .option("python.Executable", executablePath)
                    .allowAllAccess(true)
                    .build();
        } catch (Exception e) {
            throw new RuntimeException("Failed to initialize GraalPy context: " + e.getMessage(), e);
        }
    }

    private static Path locateExistingPath(List<Path> candidates, String label) {
        return candidates.stream()
                .filter(Files::exists)
                .findFirst()
                .orElseThrow(() -> new RuntimeException(label + " not found. Checked: " + candidates));
    }

    private static Path resolveSitePackagesPath(Path venvDir, String os) {
        List<Path> candidates = os.startsWith("windows")
                ? List.of(venvDir.resolve("Lib").resolve("site-packages"))
                : List.of(
                venvDir.resolve("lib").resolve("python3.11").resolve("site-packages"),
                venvDir.resolve("lib").resolve("python3.12").resolve("site-packages"),
                venvDir.resolve("lib").resolve("python3.13").resolve("site-packages")
        );
        return locateExistingPath(candidates, "GraalPy site-packages");
    }

    private static Path resolveExecutablePath(Path venvDir, String os) {
        List<Path> candidates = os.startsWith("windows")
                ? List.of(venvDir.resolve("Scripts").resolve("graalpy.exe"))
                : List.of(
                venvDir.resolve("bin").resolve("graalpy"),
                venvDir.resolve("Scripts").resolve("graalpy.sh")
        );
        return locateExistingPath(candidates, "GraalPy executable");
    }

    public Value eval(String source) {
        return context.eval("python", source);
    }
}
