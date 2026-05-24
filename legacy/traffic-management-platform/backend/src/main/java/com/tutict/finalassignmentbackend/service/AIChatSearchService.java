package com.tutict.finalassignmentbackend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.ai.chat.GraalPyContext;
import jakarta.annotation.PreDestroy;
import org.graalvm.polyglot.PolyglotException;
import org.graalvm.polyglot.Value;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Service
@ConditionalOnProperty(name = "app.ai.search.enabled", havingValue = "true")
public class AIChatSearchService {

    private static final Logger logger = LoggerFactory.getLogger(AIChatSearchService.class);

    private final GraalPyContext graalPyContext;
    private final ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AIChatSearchService(GraalPyContext context) {
        this.graalPyContext = context;
        try {
            graalPyContext.eval("""
                    import json
                    from baidu_crawler import search
                    """);
            logger.info("GraalPy search skill initialized successfully");
        } catch (PolyglotException e) {
            logger.error("Failed to import baidu_crawler.search: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to initialize AIChatSearchService: " + e.getMessage(), e);
        }
    }

    public List<Map<String, String>> search(String query) {
        if (query == null || query.isBlank()) {
            return Collections.emptyList();
        }

        try {
            return searchWithGraalPy(query.trim());
        } catch (Exception e) {
            logger.warn("Search skill failed for query='{}': {}", query, e.getMessage(), e);
            return Collections.emptyList();
        }
    }

    private List<Map<String, String>> searchWithGraalPy(String query) throws Exception {
        String escapedQuery = objectMapper.writeValueAsString(query);
        String pythonCode = """
                import json
                from baidu_crawler import search
                json.dumps(search(%s, num_results=6, debug=False), ensure_ascii=False)
                """.formatted(escapedQuery);

        Future<Value> future = executor.submit(() -> {
            synchronized (graalPyContext) {
                return graalPyContext.eval(pythonCode);
            }
        });

        try {
            Value pyResult = future.get(60, TimeUnit.SECONDS);
            if (!pyResult.isString()) {
                throw new RuntimeException("Expected JSON string from GraalPy, but got " + pyResult);
            }
            return objectMapper.readValue(pyResult.asString(), new TypeReference<>() {
            });
        } catch (TimeoutException e) {
            future.cancel(true);
            throw new RuntimeException("Search timed out", e);
        } catch (ExecutionException e) {
            throw new RuntimeException("Search execution failed: " + e.getCause().getMessage(), e.getCause());
        }
    }

    @PreDestroy
    public void shutdown() {
        executor.shutdown();
    }
}
