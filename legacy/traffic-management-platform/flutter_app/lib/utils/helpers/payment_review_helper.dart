class FinancePaymentReview {
  final String reviewResult;
  final String? reviewer;
  final DateTime? reviewTime;
  final String? reviewOpinion;

  const FinancePaymentReview({
    required this.reviewResult,
    this.reviewer,
    this.reviewTime,
    this.reviewOpinion,
  });
}

const String _financeReviewPrefix = '[FINANCE_REVIEW]|';

FinancePaymentReview? parseLatestFinancePaymentReview(String? remarks) {
  if (remarks == null || remarks.trim().isEmpty) {
    return null;
  }
  final segments = remarks
      .split(';')
      .map((segment) => segment.trim())
      .where((segment) => segment.isNotEmpty)
      .toList();
  for (final segment in segments.reversed) {
    if (!segment.startsWith(_financeReviewPrefix)) {
      continue;
    }
    final payload = segment.substring(_financeReviewPrefix.length);
    final parts = payload.split('|');
    if (parts.isEmpty || parts.first.trim().isEmpty) {
      continue;
    }
    return FinancePaymentReview(
      reviewResult: parts.first.trim().toUpperCase(),
      reviewer: parts.length > 1 && parts[1].trim().isNotEmpty
          ? parts[1].trim()
          : null,
      reviewTime: parts.length > 2 && parts[2].trim().isNotEmpty
          ? DateTime.tryParse(parts[2].trim())
          : null,
      reviewOpinion: parts.length > 3 && parts[3].trim().isNotEmpty
          ? parts[3].trim()
          : null,
    );
  }
  return null;
}

String? stripFinancePaymentReviews(String? remarks) {
  if (remarks == null || remarks.trim().isEmpty) {
    return null;
  }
  final segments = remarks
      .split(';')
      .map((segment) => segment.trim())
      .where(
        (segment) =>
            segment.isNotEmpty && !segment.startsWith(_financeReviewPrefix),
      )
      .toList();
  if (segments.isEmpty) {
    return null;
  }
  return segments.join('; ');
}
