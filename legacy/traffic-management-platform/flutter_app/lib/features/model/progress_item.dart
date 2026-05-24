import 'package:final_assignment_front/i18n/progress_localizers.dart';

class ProgressItem {
  final int? id;
  final String title;
  final String status;
  final DateTime submitTime;
  final String? details;
  final String username;
  final String? businessType;
  final int? businessId;
  final String? requestUrl;
  final String? requestParams;
  final int? userId;
  final int? appealId;
  final int? deductionId;
  final int? driverId;
  final int? fineId;
  final int? vehicleId;
  final int? offenseId;

  ProgressItem({
    this.id,
    required this.title,
    required this.status,
    required this.submitTime,
    this.details,
    required this.username,
    this.businessType,
    this.businessId,
    this.requestUrl,
    this.requestParams,
    this.userId,
    this.appealId,
    this.deductionId,
    this.driverId,
    this.fineId,
    this.vehicleId,
    this.offenseId,
  });

  ProgressItem copyWith({
    int? id,
    String? title,
    String? status,
    DateTime? submitTime,
    String? details,
    String? username,
    String? businessType,
    int? businessId,
    String? requestUrl,
    String? requestParams,
    int? userId,
    int? appealId,
    int? deductionId,
    int? driverId,
    int? fineId,
    int? vehicleId,
    int? offenseId,
  }) {
    return ProgressItem(
      id: id ?? this.id,
      title: title ?? this.title,
      status: status ?? this.status,
      submitTime: submitTime ?? this.submitTime,
      details: details ?? this.details,
      username: username ?? this.username,
      businessType: businessType ?? this.businessType,
      businessId: businessId ?? this.businessId,
      requestUrl: requestUrl ?? this.requestUrl,
      requestParams: requestParams ?? this.requestParams,
      userId: userId ?? this.userId,
      appealId: appealId ?? this.appealId,
      deductionId: deductionId ?? this.deductionId,
      driverId: driverId ?? this.driverId,
      fineId: fineId ?? this.fineId,
      vehicleId: vehicleId ?? this.vehicleId,
      offenseId: offenseId ?? this.offenseId,
    );
  }

  factory ProgressItem.fromJson(Map<String, dynamic> json) {
    final businessType = json['businessType'] as String?;
    final requestUrl = json['requestUrl'] as String?;
    final requestParams = json['requestParams'] as String?;
    final userId = json['userId'] as int?;
    final parsedParams = _parseRequestParams(requestParams);
    return ProgressItem(
      id: json['id'] as int?,
      title: _resolveProgressTitle(json, businessType, requestUrl),
      status: _resolveProgressStatus(json['businessStatus'] ?? json['status']),
      submitTime: _parseSubmitTime(json),
      details: (json['details'] as String?) ?? requestParams ?? requestUrl,
      username: (json['username'] as String?) ?? (userId?.toString() ?? ''),
      businessType: businessType,
      businessId: json['businessId'] as int?,
      requestUrl: requestUrl,
      requestParams: requestParams,
      userId: userId,
      appealId: _resolveRelatedId(json['appealId'], parsedParams['appealId']),
      deductionId:
          _resolveRelatedId(json['deductionId'], parsedParams['deductionId']),
      driverId: _resolveRelatedId(json['driverId'], parsedParams['driverId']),
      fineId: _resolveRelatedId(json['fineId'], parsedParams['fineId']),
      vehicleId:
          _resolveRelatedId(json['vehicleId'], parsedParams['vehicleId']),
      offenseId:
          _resolveRelatedId(json['offenseId'], parsedParams['offenseId']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'status': status,
      'submitTime': submitTime.toIso8601String(),
      'details': details,
      'username': username,
      'businessType': businessType,
      'businessId': businessId,
      'requestUrl': requestUrl,
      'requestParams': requestParams,
      'userId': userId,
      'appealId': appealId,
      'deductionId': deductionId,
      'driverId': driverId,
      'fineId': fineId,
      'vehicleId': vehicleId,
      'offenseId': offenseId,
    };
  }
}

String _resolveProgressStatus(dynamic rawStatus) {
  final normalized = rawStatus?.toString().trim() ?? '';
  switch (normalized.toUpperCase()) {
    case 'PROCESSING':
      return progressStatusProcessing;
    case 'SUCCESS':
      return progressStatusCompleted;
    case 'FAILED':
    case 'ERROR':
      return progressStatusArchived;
    default:
      final localized = normalizeProgressStatusCode(normalized);
      return localized.isEmpty || !kProgressStatusCategories.contains(localized)
          ? progressStatusPending
          : localized;
  }
}

DateTime _parseSubmitTime(Map<String, dynamic> json) {
  final rawValue = json['updatedAt'] ??
      json['modifiedTime'] ??
      json['createdAt'] ??
      json['createdTime'] ??
      json['submitTime'];
  if (rawValue is String) {
    final parsed = DateTime.tryParse(rawValue);
    if (parsed != null) {
      return parsed;
    }
  }
  return DateTime.now();
}

String _resolveProgressTitle(
  Map<String, dynamic> json,
  String? businessType,
  String? requestUrl,
) {
  final rawTitle = json['title'] as String?;
  if (rawTitle != null && rawTitle.trim().isNotEmpty) {
    return rawTitle.trim();
  }
  if (businessType != null && businessType.trim().isNotEmpty) {
    final localizedBusinessType = localizeRefundBusinessType(businessType);
    if (localizedBusinessType != businessType.trim()) {
      return localizedBusinessType;
    }
  }
  final requestMethod = json['requestMethod'] as String?;
  final requestPath = requestUrl?.trim() ?? '';
  if ((requestMethod?.trim().isNotEmpty ?? false) && requestPath.isNotEmpty) {
    return '${requestMethod!.trim().toUpperCase()} $requestPath';
  }
  if (requestPath.isNotEmpty) {
    return requestPath;
  }
  return 'Progress';
}

Map<String, int> _parseRequestParams(String? raw) {
  final params = <String, int>{};
  if (raw == null || raw.trim().isEmpty) {
    return params;
  }
  for (final segment in raw.split(',')) {
    final trimmed = segment.trim();
    if (trimmed.isEmpty) {
      continue;
    }
    final separatorIndex = trimmed.indexOf('=');
    if (separatorIndex <= 0 || separatorIndex == trimmed.length - 1) {
      continue;
    }
    final key = trimmed.substring(0, separatorIndex).trim();
    final value = int.tryParse(trimmed.substring(separatorIndex + 1).trim());
    if (key.isEmpty || value == null) {
      continue;
    }
    params[key] = value;
  }
  return params;
}

int? _resolveRelatedId(dynamic rawValue, int? fallback) {
  if (rawValue is int) {
    return rawValue;
  }
  if (rawValue is num) {
    return rawValue.toInt();
  }
  if (rawValue is String) {
    final parsed = int.tryParse(rawValue.trim());
    if (parsed != null) {
      return parsed;
    }
  }
  return fallback;
}
