package com.tutict.finalassignmentbackend.service;

import com.tutict.finalassignmentbackend.model.news.TrafficNewsArticle;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TrafficNewsServiceTest {

    @Test
    void shouldAppendDaysBackAndCustomKeywordToQuery() {
        TrafficNewsService service = new TrafficNewsService();
        ReflectionTestUtils.setField(service, "defaultQuery", "traffic OR accident");
        ReflectionTestUtils.setField(service, "daysBack", 3);

        String query = ReflectionTestUtils.invokeMethod(service, "buildQuery", "\u9152\u9a7e");

        assertEquals("(traffic OR accident) OR (\u9152\u9a7e) when:3d", query);
    }

    @Test
    void shouldTreatChineseTrafficKeywordsAsTrafficNews() {
        TrafficNewsService service = new TrafficNewsService();
        TrafficNewsArticle article = new TrafficNewsArticle(
                "\u4ea4\u8b66\u67e5\u5904\u9152\u9a7e\u8fdd\u6cd5\u884c\u4e3a",
                "\u672c\u5730\u5f00\u5c55\u4ea4\u901a\u5b89\u5168\u6574\u6cbb",
                null,
                "https://example.com/news",
                null,
                null,
                "\u4ea4\u901a\u65b0\u95fb",
                null
        );

        Boolean trafficRelated = ReflectionTestUtils.invokeMethod(service, "isTrafficRelated", article);

        assertTrue(Boolean.TRUE.equals(trafficRelated));
    }
}
