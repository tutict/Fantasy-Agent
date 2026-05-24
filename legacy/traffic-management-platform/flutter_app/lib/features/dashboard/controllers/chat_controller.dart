import 'package:final_assignment_front/features/api/chat_controller_api.dart';
import 'package:final_assignment_front/features/model/agent_skill_info.dart';
import 'package:final_assignment_front/features/model/agent_stream_event.dart';
import 'package:final_assignment_front/features/model/agent_context_info.dart';
import 'package:final_assignment_front/features/model/chat_action.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final bool isStatus;
  final List<ChatAction> actions;

  const ChatMessage({
    required this.text,
    required this.isUser,
    this.isStatus = false,
    this.actions = const [],
  });

  factory ChatMessage.user(String text) =>
      ChatMessage(text: text, isUser: true);

  factory ChatMessage.assistant(String text,
          {List<ChatAction> actions = const []}) =>
      ChatMessage(text: text, isUser: false, actions: actions);

  factory ChatMessage.status(String text) =>
      ChatMessage(text: text, isUser: false, isStatus: true);

  ChatMessage copyWith({
    String? text,
    bool? isUser,
    bool? isStatus,
    List<ChatAction>? actions,
  }) {
    return ChatMessage(
      text: text ?? this.text,
      isUser: isUser ?? this.isUser,
      isStatus: isStatus ?? this.isStatus,
      actions: actions ?? this.actions,
    );
  }
}

class ChatController extends GetxController {
  static ChatController get to => Get.find();

  final messages = <ChatMessage>[].obs;
  final searchResults = <String>[].obs;
  final availableSkills = <AgentSkillInfo>[].obs;
  final agentContext = Rxn<AgentContextInfo>();
  final textController = TextEditingController();
  final chatApi = ChatControllerApi();

  final userRole = 'USER'.obs;
  final webSearchEnabled = false.obs;
  final isSending = false.obs;

  final List<String> _userSuggestionKeys = const [
    'questions.user.item2',
    'questions.user.item1',
    'questions.user.item3',
    'news.menu.quickGuide.title',
  ];

  final List<String> _adminSuggestionKeys = const [
    'questions.admin.item4',
    'admin.card.logs.title',
    'admin.card.users.title',
    'admin.card.business.title',
  ];

  List<String> get suggestions =>
      (userRole.value == 'USER' ? _userSuggestionKeys : _adminSuggestionKeys)
          .map((key) => key.tr)
          .toList();

  @override
  void onInit() {
    super.onInit();
    loadSkills();
  }

  Future<void> loadSkills() async {
    try {
      availableSkills.assignAll(await chatApi.apiAiSkillsGet());
    } catch (_) {
      availableSkills.clear();
    }
  }

  void setUserRole(String role) {
    userRole.value = role.toUpperCase();
  }

  void toggleWebSearch(bool enable) {
    webSearchEnabled.value = enable;
  }

  Future<void> sendMessage([String? preset]) async {
    final text = (preset ?? textController.text).trim();
    if (text.isEmpty || isSending.value) return;

    searchResults.clear();
    agentContext.value = null;
    messages.add(ChatMessage.user(text));
    textController.clear();
    isSending.value = true;

    int? assistantIndex;
    _showStatus('chat.status.preparing'.tr);

    try {
      await for (final AgentStreamEvent event
          in chatApi.apiAiChatStream(text, webSearchEnabled.value)) {
        switch (event.type) {
          case 'status':
            _showStatus(event.content ?? 'chat.status.processing'.tr);
            break;
          case 'complete':
            break;
          case 'error':
            throw Exception(event.content ?? 'chat.error.requestBody'.tr);
          case 'search':
            for (final result in event.searchResults) {
              if (!searchResults.contains(result)) {
                searchResults.add(result);
              }
            }
            break;
          case 'context':
            agentContext.value = event.agentContext;
            break;
          case 'actions':
            if (assistantIndex != null) {
              _attachActions(assistantIndex, event.actions);
            }
            break;
          case 'message':
          default:
            assistantIndex = _appendAssistantChunk(
              assistantIndex,
              event.content ?? '',
            );
            break;
        }
      }

      _removeTrailingStatus();
      if (assistantIndex == null) {
        messages.add(ChatMessage.assistant('chat.error.noContent'.tr));
      }
    } catch (error) {
      _removeTrailingStatus();
      messages.add(ChatMessage.assistant('chat.error.requestBody'.tr));
      Get.snackbar(
        'chat.error.requestTitle'.tr,
        localizeApiErrorDetail(error),
        snackPosition: SnackPosition.BOTTOM,
        duration: const Duration(seconds: 4),
      );
    } finally {
      isSending.value = false;
    }
  }

  void executeAction(ChatAction action) {
    final type = action.type?.toUpperCase();
    if (type == 'NAVIGATE' &&
        action.target != null &&
        action.target!.isNotEmpty) {
      Get.toNamed(action.target!);
      return;
    }

    Get.snackbar(
      'chat.error.actionUnavailableTitle'.tr,
      action.label ?? 'chat.error.actionUnavailableBody'.tr,
      snackPosition: SnackPosition.BOTTOM,
      duration: const Duration(seconds: 3),
    );
  }

  void clearMessages() {
    messages.clear();
    searchResults.clear();
    agentContext.value = null;
    textController.clear();
  }

  int? _appendAssistantChunk(int? assistantIndex, String chunk) {
    if (chunk.trim().isEmpty) {
      return assistantIndex;
    }

    _removeTrailingStatus();

    if (assistantIndex == null ||
        assistantIndex < 0 ||
        assistantIndex >= messages.length) {
      messages.add(ChatMessage.assistant(chunk));
      return messages.length - 1;
    }

    final current = messages[assistantIndex];
    messages[assistantIndex] = current.copyWith(text: current.text + chunk);
    messages.refresh();
    return assistantIndex;
  }

  void _attachActions(int assistantIndex, List<ChatAction> actions) {
    if (assistantIndex < 0 || assistantIndex >= messages.length) return;
    final current = messages[assistantIndex];
    messages[assistantIndex] = current.copyWith(actions: actions);
    messages.refresh();
  }

  void _showStatus(String text) {
    if (messages.isNotEmpty && messages.last.isStatus) {
      messages[messages.length - 1] = ChatMessage.status(text);
      messages.refresh();
      return;
    }
    messages.add(ChatMessage.status(text));
  }

  void _removeTrailingStatus() {
    if (messages.isNotEmpty && messages.last.isStatus) {
      messages.removeLast();
    }
  }

  @override
  void onClose() {
    textController.dispose();
    super.onClose();
  }
}
