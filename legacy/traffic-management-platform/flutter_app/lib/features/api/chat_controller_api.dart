import 'dart:convert';
import 'dart:developer' as developer;

import 'package:final_assignment_front/features/model/agent_skill_info.dart';
import 'package:final_assignment_front/features/model/agent_stream_event.dart';
import 'package:final_assignment_front/features/model/chat_action_response.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:web_socket_channel/io.dart';

final ApiClient defaultApiClient = ApiClient();

class ChatControllerApi {
  final ApiClient apiClient;

  ChatControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  String _errorMessageOrHttpStatus(int statusCode, String body) {
    return body.isNotEmpty ? body : localizeHttpStatusError(statusCode);
  }

  Future<List<AgentSkillInfo>> apiAiSkillsGet() async {
    final response = await apiClient.invokeAPI(
      '/api/ai/skills',
      'GET',
      const [],
      null,
      await _authHeaders(),
      const {},
      null,
      const [],
    );

    final decodedBody = utf8.decode(response.bodyBytes, allowMalformed: true);
    if (response.statusCode >= 400) {
      throw ApiException(
        response.statusCode,
        _errorMessageOrHttpStatus(response.statusCode, decodedBody),
      );
    }

    final raw = jsonDecode(decodedBody);
    if (raw is! List) {
      return const [];
    }

    return raw
        .whereType<Map<String, dynamic>>()
        .map(AgentSkillInfo.fromJson)
        .toList();
  }

  Future<ChatActionResponse?> apiAiChatActionsGet(
    String message,
    bool webSearch,
  ) async {
    final response = await apiClient.invokeAPI(
      '/api/ai/chat/actions',
      'GET',
      [
        QueryParam('message', message),
        QueryParam('webSearch', webSearch.toString()),
      ],
      null,
      await _authHeaders(),
      const {},
      null,
      const [],
    );

    final decodedBody = utf8.decode(response.bodyBytes, allowMalformed: true);
    if (response.statusCode >= 400) {
      throw ApiException(
        response.statusCode,
        _errorMessageOrHttpStatus(response.statusCode, decodedBody),
      );
    }

    if (decodedBody.isEmpty) {
      return null;
    }

    final raw = jsonDecode(decodedBody);
    return raw is Map<String, dynamic>
        ? ChatActionResponse.fromJson(raw)
        : null;
  }

  Stream<AgentStreamEvent> apiAiChatStream(
    String message,
    bool webSearch,
  ) async* {
    final token = await AuthTokenStore.instance.getJwtToken();
    final channel = IOWebSocketChannel.connect(
      Uri.parse(apiClient.resolveWebSocketUrl('/eventbus/ai-chat')),
      headers: {
        ...await _authHeaders(),
      },
    );

    try {
      channel.sink.add(
        jsonEncode({
          'token': token ?? '',
          'service': 'ChatAgent',
          'action': 'chatStream',
          'idempotencyKey': 'ai-chat-${DateTime.now().microsecondsSinceEpoch}',
          'args': [message, webSearch],
        }),
      );

      await for (final raw in channel.stream) {
        if (raw is! String || raw.trim().isEmpty) {
          continue;
        }

        final parsed = _parseWebSocketMessage(raw);
        if (parsed != null) {
          if (parsed.type == 'complete') {
            break;
          }
          if (parsed.type == 'error') {
            throw ApiException(
              500,
              parsed.content ?? 'chat.error.requestBody',
            );
          }
          yield parsed;
        }
      }
    } finally {
      await channel.sink.close();
    }
  }

  AgentStreamEvent? _parseWebSocketMessage(String raw) {
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        if (decoded['error'] != null) {
          return AgentStreamEvent(
            type: 'error',
            content: decoded['error'].toString(),
          );
        }

        final payload = decoded['result'];
        if (payload is Map<String, dynamic>) {
          return AgentStreamEvent.fromJson(payload);
        }

        return AgentStreamEvent.fromJson(decoded);
      }
    } catch (error) {
      developer.log(
        'Failed to parse WebSocket message: $raw, error: $error',
        name: 'ChatControllerApi',
      );
    }
    return null;
  }

  Future<Map<String, String>> _authHeaders() async {
    final headers = <String, String>{};
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken != null && jwtToken.isNotEmpty) {
      headers['Authorization'] = 'Bearer $jwtToken';
    }
    return headers;
  }
}
