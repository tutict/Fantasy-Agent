import 'package:final_assignment_front/features/model/chat_action.dart';
import 'package:final_assignment_front/features/model/agent_context_info.dart';

class AgentStreamEvent {
  final String type;
  final String? content;
  final List<String> searchResults;
  final List<ChatAction> actions;
  final AgentContextInfo? agentContext;

  const AgentStreamEvent({
    required this.type,
    this.content,
    this.searchResults = const [],
    this.actions = const [],
    this.agentContext,
  });

  factory AgentStreamEvent.fromJson(Map<String, dynamic> json) {
    final rawSearchResults = json['searchResults'];
    final rawActions = json['actions'];
    final rawAgentContext = json['agentContext'];

    return AgentStreamEvent(
      type: json['type'] as String? ?? 'message',
      content: json['content'] as String?,
      searchResults: rawSearchResults is List
          ? rawSearchResults.map((item) => item.toString()).toList()
          : const [],
      actions: rawActions is List
          ? rawActions
              .whereType<Map<String, dynamic>>()
              .map(ChatAction.fromJson)
              .toList()
          : const [],
      agentContext: rawAgentContext is Map<String, dynamic>
          ? AgentContextInfo.fromJson(rawAgentContext)
          : null,
    );
  }
}
