import 'package:final_assignment_front/features/model/chat_action.dart';
import 'package:final_assignment_front/features/model/agent_context_info.dart';

class ChatActionResponse {
  final String? answer;
  final List<ChatAction> actions;
  final bool needConfirm;
  final AgentContextInfo? agentContext;

  ChatActionResponse({
    this.answer,
    List<ChatAction>? actions,
    this.needConfirm = false,
    this.agentContext,
  }) : actions = actions ?? const [];

  factory ChatActionResponse.fromJson(Map<String, dynamic> json) {
    final rawActions = json['actions'];
    final actions = rawActions is List
        ? rawActions
            .whereType<Map<String, dynamic>>()
            .map(ChatAction.fromJson)
            .toList()
        : <ChatAction>[];

    return ChatActionResponse(
      answer: json['answer'] as String?,
      actions: actions,
      needConfirm: json['needConfirm'] == true,
      agentContext: json['agentContext'] is Map<String, dynamic>
          ? AgentContextInfo.fromJson(
              json['agentContext'] as Map<String, dynamic>,
            )
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'answer': answer,
      'actions': actions.map((action) => action.toJson()).toList(),
      'needConfirm': needConfirm,
      'agentContext': agentContext?.toJson(),
    };
  }

  @override
  String toString() {
    return 'ChatActionResponse{ answer: $answer, actions: $actions, needConfirm: $needConfirm, agentContext: $agentContext }';
  }
}
