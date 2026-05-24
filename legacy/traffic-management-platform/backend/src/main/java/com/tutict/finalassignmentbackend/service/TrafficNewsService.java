package com.tutict.finalassignmentbackend.service;

import com.tutict.finalassignmentbackend.model.news.TrafficNewsArticle;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.util.UriComponentsBuilder;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.IOException;
import java.io.StringReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Pattern;

@Service
public class TrafficNewsService {

    private static final Logger LOG = Logger.getLogger(TrafficNewsService.class.getName());
    private static final Pattern HTML_TAG_PATTERN = Pattern.compile("<[^>]+>");
    private static final Pattern WHITESPACE_PATTERN = Pattern.compile("\\s+");
    private static final List<String> TRAFFIC_FILTER_KEYWORDS = List.of(
            "\u4ea4\u901a\u8fdd\u6cd5",
            "\u4ea4\u901a\u8fdd\u7ae0",
            "\u4ea4\u8b66",
            "\u9152\u9a7e",
            "\u9189\u9a7e",
            "\u8d85\u901f",
            "\u95ef\u7ea2\u706f",
            "\u8fdd\u505c",
            "\u4ea4\u901a\u4e8b\u6545",
            "\u9ad8\u901f",
            "\u9a7e\u9a76\u8bc1",
            "\u673a\u52a8\u8f66",
            "traffic",
            "speeding",
            "drunk driving",
            "road safety",
            "red light",
            "dui"
    );
    private static final String DEFAULT_TRAFFIC_QUERY =
            "traffic OR traffic police OR traffic violation OR drunk driving OR speeding OR accident OR highway";

    private final HttpClient httpClient;

    @Value("${app.news.rss.base-url:https://news.google.com/rss/search}")
    private String baseUrl;

    @Value("${app.news.rss.language-tag:zh-CN}")
    private String languageTag;

    @Value("${app.news.rss.geo:CN}")
    private String geo;

    @Value("${app.news.rss.ceid:CN:zh-Hans}")
    private String ceid;

    @Value("${app.news.rss.max-results:10}")
    private int maxResults;

    @Value("${app.news.rss.query:" + DEFAULT_TRAFFIC_QUERY + "}")
    private String defaultQuery;

    @Value("${app.news.rss.days-back:7}")
    private int daysBack;

    @Value("${app.news.rss.timeout-seconds:5}")
    private int timeoutSeconds;

    public TrafficNewsService() {
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public List<TrafficNewsArticle> fetchTrafficNews(String keyword, Integer limit) {
        int pageSize = resolveLimit(limit);
        URI uri = buildSearchUri(keyword);
        HttpRequest request = HttpRequest.newBuilder(uri)
                .timeout(Duration.ofSeconds(timeoutSeconds))
                .header("Accept", "application/rss+xml, application/xml, text/xml")
                .header("User-Agent", "FinalAssignmentAgent/1.0")
                .GET()
                .build();

        try {
            HttpResponse<String> response = httpClient.send(
                    request,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8)
            );
            if (response.statusCode() >= 400) {
                throw new IllegalStateException("Traffic news RSS request failed (HTTP " + response.statusCode() + ")");
            }
            return extractArticles(response.body(), pageSize);
        } catch (IOException ex) {
            LOG.log(Level.WARNING, "Traffic news RSS request failed", ex);
            throw new IllegalStateException("Traffic news RSS request failed");
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Traffic news RSS request was interrupted");
        }
    }

    private int resolveLimit(Integer limit) {
        int candidate = limit == null ? maxResults : limit;
        if (candidate <= 0) {
            candidate = maxResults;
        }
        return Math.min(candidate, Math.max(1, maxResults));
    }

    private URI buildSearchUri(String keyword) {
        return UriComponentsBuilder.fromUriString(baseUrl)
                .queryParam("q", buildQuery(keyword))
                .queryParam("hl", languageTag)
                .queryParam("gl", geo)
                .queryParam("ceid", ceid)
                .build()
                .encode()
                .toUri();
    }

    private String buildQuery(String keyword) {
        StringBuilder queryBuilder = new StringBuilder();
        String normalizedKeyword = keyword == null ? "" : keyword.trim();

        if (normalizedKeyword.isEmpty()) {
            queryBuilder.append(defaultQuery);
        } else {
            queryBuilder.append("(")
                    .append(defaultQuery)
                    .append(") OR (")
                    .append(normalizedKeyword)
                    .append(")");
        }

        queryBuilder.append(" when:")
                .append(Math.max(1, daysBack))
                .append("d");
        return queryBuilder.toString();
    }

    private List<TrafficNewsArticle> extractArticles(String body, int pageSize) {
        Document document = parseXml(body);
        NodeList itemNodes = document.getElementsByTagName("item");
        if (itemNodes.getLength() == 0) {
            return List.of();
        }

        List<TrafficNewsArticle> rawArticles = new ArrayList<>();
        for (int index = 0; index < itemNodes.getLength(); index++) {
            Node node = itemNodes.item(index);
            if (node instanceof Element element) {
                TrafficNewsArticle article = mapArticle(element);
                if (article != null) {
                    rawArticles.add(article);
                }
            }
        }

        List<TrafficNewsArticle> filtered = rawArticles.stream()
                .filter(this::isTrafficRelated)
                .limit(pageSize)
                .toList();

        if (!filtered.isEmpty()) {
            return filtered;
        }

        return rawArticles.stream().limit(pageSize).toList();
    }

    private Document parseXml(String xml) {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setXIncludeAware(false);
            factory.setExpandEntityReferences(false);

            DocumentBuilder builder = factory.newDocumentBuilder();
            return builder.parse(new InputSource(new StringReader(xml)));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Failed to parse traffic news RSS XML", ex);
            throw new IllegalStateException("Traffic news RSS response parsing failed");
        }
    }

    private TrafficNewsArticle mapArticle(Element itemElement) {
        String title = textOf(itemElement, "title");
        if (title.isBlank()) {
            return null;
        }

        String description = sanitizeDescription(textOf(itemElement, "description"));
        String link = textOf(itemElement, "link");
        String publishedAt = normalizePublishedAt(textOf(itemElement, "pubDate"));

        NodeList sourceNodes = itemElement.getElementsByTagName("source");
        String sourceName = null;
        String sourceUrl = null;
        if (sourceNodes.getLength() > 0 && sourceNodes.item(0) instanceof Element sourceElement) {
            sourceName = trimToNull(sourceElement.getTextContent());
            sourceUrl = trimToNull(sourceElement.getAttribute("url"));
        }

        return new TrafficNewsArticle(
                trimToNull(title),
                trimToNull(description),
                trimToNull(description),
                trimToNull(link),
                null,
                publishedAt,
                sourceName,
                sourceUrl
        );
    }

    private String textOf(Element element, String tagName) {
        NodeList nodes = element.getElementsByTagName(tagName);
        if (nodes.getLength() == 0) {
            return "";
        }
        Node node = nodes.item(0);
        return node == null ? "" : node.getTextContent();
    }

    private String sanitizeDescription(String value) {
        String withoutTags = HTML_TAG_PATTERN.matcher(value == null ? "" : value).replaceAll(" ");
        return WHITESPACE_PATTERN.matcher(withoutTags).replaceAll(" ").trim();
    }

    private String normalizePublishedAt(String value) {
        String trimmed = trimToNull(value);
        if (trimmed == null) {
            return null;
        }
        try {
            return OffsetDateTime.parse(trimmed, DateTimeFormatter.RFC_1123_DATE_TIME)
                    .truncatedTo(ChronoUnit.SECONDS)
                    .toString();
        } catch (Exception ignored) {
            return trimmed;
        }
    }

    private boolean isTrafficRelated(TrafficNewsArticle article) {
        String haystack = (
                safe(article.getTitle()) + " " +
                        safe(article.getDescription()) + " " +
                        safe(article.getContent()) + " " +
                        safe(article.getSourceName())
        ).toLowerCase(Locale.ROOT);

        for (String keyword : TRAFFIC_FILTER_KEYWORDS) {
            if (haystack.contains(keyword.toLowerCase(Locale.ROOT))) {
                return true;
            }
        }
        return false;
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
