import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:percent_indicator/circular_percent_indicator.dart';

class TrafficViolationCard extends StatelessWidget {
  const TrafficViolationCard({
    required this.data,
    super.key,
  });

  final TrafficViolationCardData data;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;

    return Container(
      padding: const EdgeInsets.all(kSpacing),
      height: 220,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            isLight
                ? const Color.fromRGBO(220, 53, 69, 1)
                : const Color.fromRGBO(165, 42, 42, 1),
            isLight
                ? const Color.fromRGBO(245, 90, 107, 1)
                : const Color.fromRGBO(200, 60, 60, 1),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isLight ? 0.1 : 0.2),
            offset: const Offset(0, 4),
            blurRadius: 8,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            flex: 2,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  data.title,
                  style: Theme.of(context).textTheme.titleMedium!.copyWith(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                ),
                const SizedBox(height: 8),
                _ViolationRichText(
                  value1: '${data.totalViolations}',
                  value2: ' ${'shared.trafficViolation.total'.tr}',
                ),
                const SizedBox(height: 6),
                _ViolationRichText(
                  value1: '${data.handledViolations}',
                  value2: ' ${'shared.trafficViolation.handled'.tr}',
                ),
                const SizedBox(height: 6),
                _ViolationRichText(
                  value1: '${data.unhandledViolations}',
                  value2: ' ${'shared.trafficViolation.pending'.tr}',
                ),
              ],
            ),
          ),
          Expanded(
            flex: 1,
            child: _ViolationIndicator(
              total: data.totalViolations,
              handled: data.handledViolations,
              isLight: isLight,
            ),
          ),
        ],
      ),
    );
  }
}

class _ViolationRichText extends StatelessWidget {
  const _ViolationRichText({
    required this.value1,
    required this.value2,
  });

  final String value1;
  final String value2;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;
    return RichText(
      text: TextSpan(
        style: Theme.of(context).textTheme.bodyMedium!.copyWith(
              color: isLight ? Colors.white : Colors.white70,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
        children: [
          TextSpan(text: value1),
          TextSpan(
            text: value2,
            style: Theme.of(context).textTheme.bodyMedium!.copyWith(
                  color: isLight ? Colors.white70 : Colors.white54,
                  fontWeight: FontWeight.normal,
                  fontSize: 14,
                ),
          ),
        ],
      ),
    );
  }
}

class _ViolationIndicator extends StatelessWidget {
  const _ViolationIndicator({
    required this.total,
    required this.handled,
    required this.isLight,
  });

  final int total;
  final int handled;
  final bool isLight;

  @override
  Widget build(BuildContext context) {
    final double percent = total > 0 ? handled / total : 0.0;

    return CircularPercentIndicator(
      radius: 70,
      lineWidth: 8,
      percent: percent,
      circularStrokeCap: CircularStrokeCap.round,
      center: Column(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${(percent * 100).toStringAsFixed(1)} %',
            style: Theme.of(context).textTheme.titleSmall!.copyWith(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
          ),
          Text(
            'shared.trafficViolation.rate'.tr,
            style: Theme.of(context).textTheme.bodySmall!.copyWith(
                  fontSize: 12,
                  fontWeight: FontWeight.normal,
                  color: Colors.white70,
                ),
          ),
        ],
      ),
      progressColor: Colors.white,
      backgroundColor: Colors.white.withAlpha((0.2 * 255).toInt()),
    );
  }
}

class TrafficViolationCardData {
  final int totalViolations;
  final int handledViolations;
  final int unhandledViolations;
  final String title;

  const TrafficViolationCardData({
    required this.totalViolations,
    required this.handledViolations,
    required this.unhandledViolations,
    required this.title,
  });
}
