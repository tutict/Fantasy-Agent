package com.tutict.finalassignmentbackend.config.docker;

import com.redis.testcontainers.RedisContainer;
import org.springframework.context.ApplicationContextInitializer;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.MutablePropertySources;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.elasticsearch.ElasticsearchContainer;
import org.testcontainers.redpanda.RedpandaContainer;
import org.testcontainers.utility.DockerImageName;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

public class RunDocker implements ApplicationContextInitializer<ConfigurableApplicationContext> {

    private static final Logger log = Logger.getLogger(RunDocker.class.getName());
    private static final String PROPERTY_SOURCE_NAME = "docker";
    private static final String DEFAULT_MANTICORE_IMAGE = "manticoresearch/manticore:dev";
    private static final String DEFAULT_ELASTICSEARCH_IMAGE = "final-assignment-elasticsearch:9.2.6";
    private static final String DEFAULT_ELASTICSEARCH_COMPATIBLE_IMAGE = "docker.elastic.co/elasticsearch/elasticsearch";
    private static volatile boolean shutdownHookRegistered = false;

    private static RedisContainer redisContainer;
    private static RedpandaContainer redpandaContainer;
    private static ElasticsearchContainer elasticsearchContainer;
    private static GenericContainer<?> manticoreContainer;

    @Override
    public void initialize(ConfigurableApplicationContext applicationContext) {
        boolean bootstrapContainers = applicationContext.getEnvironment()
                .getProperty("app.runtime.bootstrap-containers", Boolean.class, false);
        if (!bootstrapContainers) {
            log.log(Level.INFO, "Runtime container bootstrap is disabled by app.runtime.bootstrap-containers=false");
            return;
        }

        startRedis(applicationContext);
        startRedpanda(applicationContext);
        startElasticsearch(applicationContext);
        // startManticoreSearch(applicationContext);
        registerShutdownHook();
    }

    private void startRedis(ConfigurableApplicationContext applicationContext) {
        try {
            if (redisContainer == null || !redisContainer.isRunning()) {
                redisContainer = new RedisContainer("redis:7");
                redisContainer.start();
            }
            String redisHost = redisContainer.getHost();
            int redisPort = redisContainer.getFirstMappedPort();
            log.log(Level.INFO, "Redis container started successfully at {0}:{1}", new Object[]{redisHost, redisPort});
            setProperty(applicationContext, "spring.data.redis.host", redisHost);
            setProperty(applicationContext, "spring.data.redis.port", String.valueOf(redisPort));
            log.log(Level.INFO, "Redis properties set: host={0}, port={1}", new Object[]{redisHost, redisPort});
        } catch (Exception e) {
            log.log(Level.SEVERE, "Failed to start Redis container: {0}", new Object[]{e.getMessage()});
        }
    }

    private void startRedpanda(ConfigurableApplicationContext applicationContext) {
        try {
            if (redpandaContainer == null || !redpandaContainer.isRunning()) {
                redpandaContainer = new RedpandaContainer("redpandadata/redpanda:v24.1.2");
                redpandaContainer.start();
            }
            String bootstrapServers = redpandaContainer.getBootstrapServers();
            log.log(Level.INFO, "Redpanda container started successfully with bootstrap servers: {0}", new Object[]{bootstrapServers});
            setProperty(applicationContext, "spring.kafka.bootstrap-servers", bootstrapServers);
            log.log(Level.INFO, "Kafka bootstrap-servers set: {0}", new Object[]{bootstrapServers});
        } catch (Exception e) {
            log.log(Level.SEVERE, "Failed to start Redpanda container: {0}", new Object[]{e.getMessage(), e});
        }
    }

    private void startElasticsearch(ConfigurableApplicationContext applicationContext) {
        try {
            String configuredUris = applicationContext.getEnvironment().getProperty("spring.elasticsearch.uris");
            if (configuredUris != null && !configuredUris.isBlank()) {
                log.log(Level.INFO, "Detected existing spring.elasticsearch.uris={0}, skipping Elasticsearch container startup", configuredUris);
                return;
            }

            boolean elasticsearchEnabled = applicationContext.getEnvironment()
                    .getProperty("app.docker.elasticsearch.enabled", Boolean.class, true);
            if (!elasticsearchEnabled) {
                log.log(Level.INFO, "Elasticsearch container startup disabled by app.docker.elasticsearch.enabled=false");
                return;
            }

            String elasticsearchImage = applicationContext.getEnvironment()
                    .getProperty("app.docker.elasticsearch.image", DEFAULT_ELASTICSEARCH_IMAGE);
            String compatibleImage = applicationContext.getEnvironment()
                    .getProperty("app.docker.elasticsearch.compatible-image", DEFAULT_ELASTICSEARCH_COMPATIBLE_IMAGE);

            // Allow custom plugin images while keeping Testcontainers compatibility with Elasticsearch.
            DockerImageName myImage = DockerImageName.parse(elasticsearchImage)
                    .asCompatibleSubstituteFor(compatibleImage);

            // Start the custom image in single-node mode when the container is not already running.
            if (elasticsearchContainer == null || !elasticsearchContainer.isRunning()) {
                elasticsearchContainer = new ElasticsearchContainer(myImage)
                        .withEnv("xpack.security.enabled", "false")
                        .withEnv("discovery.type", "single-node"); // Enable single-node discovery mode.
                elasticsearchContainer.start();
            }

            String elasticsearchUrl = elasticsearchContainer.getHttpHostAddress();
            setProperty(applicationContext, "spring.elasticsearch.uris", "http://" + elasticsearchUrl);
            log.log(Level.INFO, "Elasticsearch started at: http://{0}", elasticsearchUrl);
        } catch (Exception e) {
            log.log(Level.SEVERE, "Failed to start Elasticsearch container: {0}", e.getMessage());
        }
    }

    public void startManticoreSearch(ConfigurableApplicationContext applicationContext) {
        String manticoreImage = applicationContext.getEnvironment()
                .getProperty("manticore.image", DEFAULT_MANTICORE_IMAGE);
        try {
            if (manticoreContainer == null || !manticoreContainer.isRunning()) {
                manticoreContainer = new GenericContainer<>(DockerImageName.parse(manticoreImage))
                        .withExposedPorts(9306, 9308)
                        .withEnv("EXTRA", "1")
                        .waitingFor(Wait.forHttp("/search")
                                .forPort(9308)
                                .withStartupTimeout(Duration.ofSeconds(120)));
                manticoreContainer.start();
            }
            String manticoreHost = manticoreContainer.getHost();
            Integer httpPort = manticoreContainer.getMappedPort(9308);
            String manticoreUrl = String.format("http://%s:%d", manticoreHost, httpPort);

            setProperty(applicationContext, "manticore.host", manticoreUrl);
            log.log(Level.INFO, "Manticore container started successfully at {0}", new Object[]{manticoreUrl});
        } catch (Exception e) {
            log.log(Level.SEVERE, "Failed to start Manticore container: {0}", new Object[]{e.getMessage()});
            throw new RuntimeException("Manticore startup failed", e);
        }
    }

    private static void registerShutdownHook() {
        if (shutdownHookRegistered) {
            return;
        }
        synchronized (RunDocker.class) {
            if (shutdownHookRegistered) {
                return;
            }
            Runtime.getRuntime().addShutdownHook(new Thread(RunDocker::stopContainers, "docker-shutdown"));
            shutdownHookRegistered = true;
        }
    }

    private static void stopContainers() {
        if (redisContainer != null && redisContainer.isRunning()) {
            redisContainer.stop();
            log.log(Level.INFO, "Redis container stopped");
        }
        if (redpandaContainer != null && redpandaContainer.isRunning()) {
            redpandaContainer.stop();
            log.log(Level.INFO, "Redpanda container stopped");
        }
        if (elasticsearchContainer != null && elasticsearchContainer.isRunning()) {
            elasticsearchContainer.stop();
            log.log(Level.INFO, "Elasticsearch container stopped");
        }
        if (manticoreContainer != null && manticoreContainer.isRunning()) {
            manticoreContainer.stop();
            log.log(Level.INFO, "Manticore container stopped and closed");
        }
    }

    private static void setProperty(ConfigurableApplicationContext applicationContext, String key, String value) {
        ConfigurableEnvironment environment = applicationContext.getEnvironment();
        MutablePropertySources sources = environment.getPropertySources();
        MapPropertySource source = (MapPropertySource) sources.get(PROPERTY_SOURCE_NAME);
        if (source == null) {
            Map<String, Object> map = new HashMap<>();
            source = new MapPropertySource(PROPERTY_SOURCE_NAME, map);
            sources.addFirst(source);
        }
        source.getSource().put(key, value);
    }
}
