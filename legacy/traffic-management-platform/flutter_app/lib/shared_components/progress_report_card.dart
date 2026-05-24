import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:percent_indicator/percent_indicator.dart';

class ProgressReportCardData {
  final double percent;
  final String title;
  final int task;
  final int doneTask;
  final int undoneTask;

  const ProgressReportCardData({
    required this.percent,
    required this.title,
    required this.task,
    required this.doneTask,
    required this.undoneTask,
  });
}

class ProgressReportCard extends StatelessWidget {
  const ProgressReportCard({
    required this.data,
    super.key,
  });

  final ProgressReportCardData data;

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
                ? const Color.fromRGBO(111, 88, 255, 1)
                : const Color.fromRGBO(63, 40, 207, 1),
            isLight
                ? const Color.fromRGBO(157, 86, 248, 1)
                : const Color.fromRGBO(107, 66, 198, 1),
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
                _RichText(
                  value1: '${data.task}',
                  value2: ' ${'shared.progressReport.appeals'.tr}',
                ),
                const SizedBox(height: 6),
                _RichText(
                  value1: '${data.doneTask}',
                  value2: ' ${'shared.progressReport.appealsHandled'.tr}',
                ),
                const SizedBox(height: 6),
                _RichText(
                  value1: '${data.undoneTask}',
                  value2: ' ${'shared.progressReport.appealsPending'.tr}',
                ),
              ],
            ),
          ),
          Expanded(
            flex: 1,
            child: _Indicator(percent: data.percent, isLight: isLight),
          ),
        ],
      ),
    );
  }
}

class _RichText extends StatelessWidget {
  const _RichText({
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

class _Indicator extends StatelessWidget {
  const _Indicator({required this.percent, required this.isLight});

  final double percent;
  final bool isLight;

  @override
  Widget build(BuildContext context) {
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
            'shared.progressReport.completionRate'.tr,
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
