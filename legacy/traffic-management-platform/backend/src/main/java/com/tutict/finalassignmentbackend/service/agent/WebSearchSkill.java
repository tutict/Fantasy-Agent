package com.tutict.finalassignmentbackend.service.agent;

import com.tutict.finalassignmentbackend.service.AIChatSearchService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
@ConditionalOnProperty(name = "app.ai.search.enabled", havingValue = "true")
public class WebSearchSkill implements AgentSkill {

    private final AIChatSearchService searchService;

    public WebSearchSkill(AIChatSearchService searchService) {
        this.searchService = searchService;
    }

    @Override
    public String id() {
        return "web-search";
    }

    @Override
    public String displayName() {
        return "联网检索";
    }

    @Override
    public String description() {
        return "通过 GraalPy 搜索公开网页结果，为回答补充最新参考信息。";
    }

    @Override
    public boolean supports(AgentSkillContext context) {
        return context.webSearch();
    }

    @Override
    public AgentSkillResult execute(AgentSkillContext context) {
        List<Map<String, String>> results = searchService.search(context.message());
        List<String> formatted = results.stream()
                .map(this::formatResult)
                .filter(text -> !text.isBlank())
                .limit(5)
                .toList();

        String summary = formatted.isEmpty()
                ? "本次未检索到可直接引用的公开结果。"
                : "已补充公开网页检索结果，可用于辅助判断最新信息。";

        return new AgentSkillResult(id(), summary, List.of(), formatted, List.of(), false);
    }

    private String formatResult(Map<String, String> item) {
        String title = item.getOrDefault("title", "未命名结果").trim();
        String summary = item.getOrDefault("abstract", "").trim();
        return summary.isEmpty() ? title : title + "： " + summary;
    }
}
