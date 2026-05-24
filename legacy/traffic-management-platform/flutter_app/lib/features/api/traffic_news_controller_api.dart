import 'dart:convert';

import 'package:final_assignment_front/features/model/traffic_news_article.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

final ApiClient defaultApiClient = ApiClient();

class TrafficNewsControllerApi {
  final ApiClient apiClient;

  TrafficNewsControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  Future<void> initializeWithJwt() async {
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken == null || jwtToken.isEmpty) {
      throw Exception('api.error.notAuthenticated');
    }
    apiClient.setJwtToken(jwtToken);
  }

  Future<List<TrafficNewsArticleModel>> apiNewsTrafficGet({
    int limit = 10,
    String? keyword,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/news/traffic',
      'GET',
      [
        QueryParam('limit', '$limit'),
        if (keyword != null && keyword.trim().isNotEmpty)
          QueryParam('keyword', keyword.trim()),
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
        decodedBody.isNotEmpty
            ? decodedBody
            : localizeHttpStatusError(response.statusCode),
      );
    }

    if (decodedBody.isEmpty) {
      return const [];
    }

    final raw = jsonDecode(decodedBody);
    if (raw is! List) {
      return const [];
    }

    return raw
        .whereType<Map<String, dynamic>>()
        .map(TrafficNewsArticleModel.fromJson)
        .toList();
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
