package com.tutict.finalassignmentbackend.service.agent;

import com.tutict.finalassignmentbackend.model.ai.ChatAction;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class WorkflowSkill implements AgentSkill {

    private static final List<RouteRule> ROUTE_RULES = List.of(
            new RouteRule(List.of("罚款", "缴费", "支付", "罚单"), new ChatAction("NAVIGATE", "打开罚款信息", "/fineInformation", "")),
            new RouteRule(List.of("进度", "流程", "状态", "跟踪"), new ChatAction("NAVIGATE", "打开业务进度", "/businessProgress", "")),
            new RouteRule(List.of("申诉", "复核", "异议"), new ChatAction("NAVIGATE", "打开申诉管理", "/appealManagement", "")),
            new RouteRule(List.of("车辆", "车牌"), new ChatAction("NAVIGATE", "打开车辆管理", "/vehicleManagement", "")),
            new RouteRule(List.of("违法", "违章", "记录"), new ChatAction("NAVIGATE", "打开违法记录", "/userOffenseListPage", "")),
            new RouteRule(List.of("咨询", "帮助", "客服"), new ChatAction("NAVIGATE", "打开咨询反馈", "/consultation", "")),
            new RouteRule(List.of("新闻", "资讯", "最新"), new ChatAction("NAVIGATE", "打开资讯页", "/latestTrafficViolationNewsPage", "")),
            new RouteRule(List.of("日志", "审计"), new ChatAction("NAVIGATE", "打开操作日志", "/operationLogPage", ""))
    );

    @Override
    public String id() {
        return "workflow";
    }

    @Override
    public String displayName() {
        return "页面动作规划";
    }

    @Override
    public String description() {
        return "根据用户意图匹配前端路由，生成可直接执行的页面动作。";
    }

    @Override
    public AgentSkillResult execute(AgentSkillContext context) {
        String message = context.normalizedMessage();
        List<ChatAction> actions = new ArrayList<>();

        for (RouteRule rule : ROUTE_RULES) {
            if (rule.matches(message)) {
                actions.add(rule.action());
            }
        }

        String summary = actions.isEmpty() ? "" : "已为当前意图匹配到页面跳转动作。";
        List<String> highlights = actions.stream()
                .map(action -> "可跳转到「" + action.getLabel() + "」继续处理。")
                .toList();

        return new AgentSkillResult(id(), summary, highlights, List.of(), actions, !actions.isEmpty());
    }

    private record RouteRule(List<String> keywords, ChatAction action) {
        boolean matches(String message) {
            for (String keyword : keywords) {
                if (message.contains(keyword)) {
                    return true;
                }
            }
            return false;
        }
    }
}
