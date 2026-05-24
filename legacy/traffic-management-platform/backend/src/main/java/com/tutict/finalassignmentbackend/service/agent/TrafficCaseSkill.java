package com.tutict.finalassignmentbackend.service.agent;

import com.tutict.finalassignmentbackend.model.ai.ChatAction;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class TrafficCaseSkill implements AgentSkill {

    private static final List<String> MANAGER_KEYWORDS = List.of(
            "管理员", "管理端", "后台", "审核", "审计", "复核员", "处理员", "执法", "窗口"
    );

    @Override
    public String id() {
        return "traffic-case";
    }

    @Override
    public String displayName() {
        return "交通违法业务编排";
    }

    @Override
    public String description() {
        return "围绕违法核查、罚款处理、申诉复核、进度跟踪和车辆档案等场景，输出办理清单与动作建议。";
    }

    @Override
    public boolean supports(AgentSkillContext context) {
        return Scenario.match(context) != null;
    }

    @Override
    public AgentSkillResult execute(AgentSkillContext context) {
        Scenario scenario = Scenario.match(context);
        if (scenario == null) {
            return AgentSkillResult.empty(id());
        }

        boolean managerIntent = isManagerIntent(context);
        List<ChatAction> actions = new ArrayList<>();
        actions.add(scenario.primaryAction(managerIntent));
        actions.add(new ChatAction(
                "SHOW_MODAL",
                "查看" + scenario.title + "办理清单",
                "",
                scenario.buildChecklist(managerIntent)
        ));

        return new AgentSkillResult(
                id(),
                "已识别为「" + scenario.title + "」场景，Agent 已按交通违法处理流程整理下一步动作。",
                scenario.highlights(managerIntent),
                List.of(),
                actions,
                true
        );
    }

    private boolean isManagerIntent(AgentSkillContext context) {
        return context.isPrivilegedOperator()
                || MANAGER_KEYWORDS.stream().anyMatch(keyword -> context.containsAny(keyword));
    }

    private enum Scenario {
        OFFENSE(
                "违法记录核查",
                List.of("违法", "违章", "抓拍", "处罚决定书", "记录", "offense"),
                "/userOffenseListPage",
                "打开违法记录",
                "/offenseList",
                "打开违法列表",
                List.of(
                        "先核对车牌号、违法时间、违法地点和处罚决定书编号。",
                        "确认当前违法记录是否已进入罚款或申诉阶段。",
                        "如果事实有异议，再准备证据材料进入后续申诉。"
                ),
                List.of(
                        "先检索违法编号、违法类型和当前处理状态。",
                        "核对车辆归属、违法证据和处罚依据是否完整。",
                        "确认是否需要转入罚款处理、申诉审核或作废流程。"
                )
        ),
        FINE(
                "罚款缴纳处理",
                List.of("罚款", "缴费", "支付", "罚单", "fine"),
                "/fineInformation",
                "打开罚款信息",
                "/fineList",
                "打开罚款列表",
                List.of(
                        "先确认罚款金额、截止时间和待缴状态。",
                        "核对对应违法记录是否已经生效且未撤销。",
                        "支付前再次确认支付对象，避免重复缴费。"
                ),
                List.of(
                        "先按罚单编号或违法编号检索罚款记录。",
                        "核对金额、状态、支付时间和支付渠道是否一致。",
                        "如有异常，先排查重复单、撤销单或人工修正记录。"
                )
        ),
        APPEAL(
                "申诉复核办理",
                List.of("申诉", "复核", "异议", "appeal"),
                "/userAppeal",
                "打开申诉页面",
                "/appealManagement",
                "打开申诉管理",
                List.of(
                        "先整理处罚决定书、图片视频和事实说明。",
                        "重点说明对违法事实、时间地点或车辆归属的异议点。",
                        "提交后持续关注受理状态和补充材料要求。"
                ),
                List.of(
                        "先检索申诉编号、原违法编号和当前受理节点。",
                        "核对证据链、审核意见和建议处理结果。",
                        "确认是退回补充、驳回申诉还是进入复核通过流程。"
                )
        ),
        PROGRESS(
                "业务进度跟踪",
                List.of("进度", "流程", "状态", "跟踪", "办理到哪", "节点"),
                "/businessProgress",
                "打开业务进度",
                "/progressManagement",
                "打开进度管理",
                List.of(
                        "先确认案件编号和最近一次更新时间。",
                        "查看当前卡在哪个节点，再判断是否需要补材料。",
                        "如果长时间不推进，优先联系人工处理环节。"
                ),
                List.of(
                        "先按案件编号或用户维度拉取处理进度。",
                        "核查当前节点、责任人和超时情况。",
                        "必要时转派、催办或回退到上一处理节点。"
                )
        ),
        VEHICLE(
                "车辆档案核对",
                List.of("车辆", "车牌", "驾驶证", "司机", "档案", "driver"),
                "/vehicleManagement",
                "打开车辆管理",
                "/vehicleList",
                "打开车辆列表",
                List.of(
                        "先核对车牌号、车主信息和绑定驾驶人是否正确。",
                        "修改资料前确认历史违法记录归属没有问题。",
                        "如为新增车辆，先补全基础档案再办理后续业务。"
                ),
                List.of(
                        "先按车牌号或档案编号查询车辆主档。",
                        "核对车辆、驾驶人和历史违法记录的关联关系。",
                        "确认是否需要修正档案、补录信息或解除错误绑定。"
                )
        ),
        ACCIDENT(
                "事故快处与证据留存",
                List.of("事故", "快处", "证据", "现场", "视频"),
                "/accidentQuickGuidePage",
                "打开事故快处指南",
                "/trafficViolationScreen",
                "打开交通违法总览",
                List.of(
                        "先确保安全，再拍摄现场位置、车辆状态和相关标识。",
                        "保留照片、视频、时间地点和对方信息等关键证据。",
                        "根据情况进入快处指南或后续进度查询页面。"
                ),
                List.of(
                        "先确认事故编号、关联违法记录和证据材料状态。",
                        "核对责任认定、证据留存和后续流转节点。",
                        "必要时补录材料并引导进入对应办理页面。"
                )
        );

        private final String title;
        private final List<String> keywords;
        private final String userTarget;
        private final String userLabel;
        private final String managerTarget;
        private final String managerLabel;
        private final List<String> userSteps;
        private final List<String> managerSteps;

        Scenario(
                String title,
                List<String> keywords,
                String userTarget,
                String userLabel,
                String managerTarget,
                String managerLabel,
                List<String> userSteps,
                List<String> managerSteps
        ) {
            this.title = title;
            this.keywords = keywords;
            this.userTarget = userTarget;
            this.userLabel = userLabel;
            this.managerTarget = managerTarget;
            this.managerLabel = managerLabel;
            this.userSteps = userSteps;
            this.managerSteps = managerSteps;
        }

        static Scenario match(AgentSkillContext context) {
            List<Scenario> priority = List.of(APPEAL, FINE, PROGRESS, VEHICLE, ACCIDENT, OFFENSE);
            for (Scenario scenario : priority) {
                if (scenario.matches(context)) {
                    return scenario;
                }
            }
            return null;
        }

        ChatAction primaryAction(boolean managerIntent) {
            if (managerIntent && managerTarget != null && !managerTarget.isBlank()) {
                return new ChatAction("NAVIGATE", managerLabel, managerTarget, "");
            }
            return new ChatAction("NAVIGATE", userLabel, userTarget, "");
        }

        List<String> highlights(boolean managerIntent) {
            List<String> steps = managerIntent ? managerSteps : userSteps;
            List<String> highlights = new ArrayList<>(steps);
            highlights.add("建议先执行「" + primaryAction(managerIntent).getLabel() + "」，再继续当前办理流程。");
            return highlights;
        }

        String buildChecklist(boolean managerIntent) {
            List<String> steps = managerIntent ? managerSteps : userSteps;
            StringBuilder builder = new StringBuilder();
            builder.append("场景：").append(title).append('\n');
            builder.append("角色：").append(managerIntent ? "管理端" : "用户端").append("\n\n");
            for (int i = 0; i < steps.size(); i++) {
                builder.append(i + 1).append(". ").append(steps.get(i)).append('\n');
            }
            builder.append('\n');
            builder.append("下一步：").append(primaryAction(managerIntent).getLabel());
            return builder.toString().trim();
        }

        boolean matches(AgentSkillContext context) {
            for (String keyword : keywords) {
                if (context.containsAny(keyword)) {
                    return true;
                }
            }
            return false;
        }
    }
}
