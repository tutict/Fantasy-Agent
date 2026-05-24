package com.tutict.finalassignmentbackend.service.agent;

import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class KnowledgeSkill implements AgentSkill {

    @Override
    public String id() {
        return "knowledge";
    }

    @Override
    public String displayName() {
        return "业务知识库";
    }

    @Override
    public String description() {
        return "根据交通违法、缴费、申诉和进度等关键词生成稳定的业务建议。";
    }

    @Override
    public AgentSkillResult execute(AgentSkillContext context) {
        Topic topic = Topic.from(context.normalizedMessage());

        return switch (topic) {
            case FINE -> new AgentSkillResult(
                    id(),
                    "当前问题更接近罚款查询或缴费办理。",
                    List.of(
                            "先确认违法记录、罚款金额和处理时限是否一致。",
                            "优先核对车牌号、处罚决定书编号和待缴状态。",
                            "需要线上支付时，建议先进入罚款信息页，再决定是否继续付款。"
                    ),
                    List.of(),
                    List.of(),
                    false
            );
            case APPEAL -> new AgentSkillResult(
                    id(),
                    "当前问题更接近申诉或复核流程。",
                    List.of(
                            "先准备处罚决定书、证据材料和时间地点说明。",
                            "申诉前先核对违法事实、抓拍信息和车辆归属是否准确。",
                            "如需补充说明，尽量用简洁事实链表达，不要只写结论。"
                    ),
                    List.of(),
                    List.of(),
                    false
            );
            case PROGRESS -> new AgentSkillResult(
                    id(),
                    "当前问题更接近进度查询或业务跟踪。",
                    List.of(
                            "优先确认案件编号、当前节点和最近一次更新时间。",
                            "如果状态长时间未变化，再补查材料是否缺失或是否需要人工审核。",
                            "涉及多个案件时，建议按最新更新时间排序逐个核对。"
                    ),
                    List.of(),
                    List.of(),
                    false
            );
            case VEHICLE -> new AgentSkillResult(
                    id(),
                    "当前问题更接近车辆或驾驶人信息管理。",
                    List.of(
                            "先确认车牌号、驾驶证号和绑定关系是否正确。",
                            "修改车辆资料前，先查看当前档案和历史违法记录是否一致。",
                            "如果是新增车辆，建议先补全基本信息再做业务办理。"
                    ),
                    List.of(),
                    List.of(),
                    false
            );
            case NEWS -> new AgentSkillResult(
                    id(),
                    "当前问题更接近资讯查询或事故处理指引。",
                    List.of(
                            "涉及最新政策或新闻时，建议同时开启联网检索。",
                            "事故处理优先保留证据，再按系统流程查看快处指南和进度。",
                            "如需获取公开资讯，优先看官方部门和权威媒体说明。"
                    ),
                    List.of(),
                    List.of(),
                    false
            );
            case GENERAL -> new AgentSkillResult(
                    id(),
                    "当前问题可以先按交通业务咨询处理。",
                    List.of(
                            "先明确你要做的是查询、缴费、申诉还是进度跟踪。",
                            "如果问题涉及最新规定，建议开启联网检索后再判断。",
                            "如果你已经知道目标页面，我可以继续把建议细化成跳转动作。"
                    ),
                    List.of(),
                    List.of(),
                    false
            );
        };
    }

    private enum Topic {
        FINE,
        APPEAL,
        PROGRESS,
        VEHICLE,
        NEWS,
        GENERAL;

        static Topic from(String message) {
            if (containsAny(message, "罚款", "缴费", "支付", "罚单")) {
                return FINE;
            }
            if (containsAny(message, "申诉", "复核", "异议", "appeal")) {
                return APPEAL;
            }
            if (containsAny(message, "进度", "流程", "状态", "办理到哪", "跟踪")) {
                return PROGRESS;
            }
            if (containsAny(message, "车辆", "车牌", "驾驶证", "司机", "driver")) {
                return VEHICLE;
            }
            if (containsAny(message, "新闻", "资讯", "最新", "事故", "快处")) {
                return NEWS;
            }
            return GENERAL;
        }

        private static boolean containsAny(String message, String... keywords) {
            for (String keyword : keywords) {
                if (message.contains(keyword)) {
                    return true;
                }
            }
            return false;
        }
    }
}
