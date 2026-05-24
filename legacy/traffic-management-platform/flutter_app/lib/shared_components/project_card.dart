import 'dart:async';

import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:final_assignment_front/i18n/project_card_localizers.dart';
import 'package:flutter/material.dart';
import 'package:get/Get.dart';
import 'package:percent_indicator/percent_indicator.dart';

class ProjectCardData {
  final double percent;
  final ImageProvider projectImage;
  final String projectName;
  final DateTime releaseTime;

  const ProjectCardData({
    required this.projectImage,
    required this.projectName,
    required this.releaseTime,
    required this.percent,
  });
}

class ProjectCard extends StatefulWidget {
  const ProjectCard({
    required this.data,
    super.key,
  });

  final ProjectCardData data;

  @override
  State<ProjectCard> createState() => _ProjectCardState();
}

class _ProjectCardState extends State<ProjectCard> {
  late Timer _timer;
  DateTime _currentTime = DateTime.now();

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _currentTime = DateTime.now();
      });
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        _ProgressIndicator(
          percent: widget.data.percent,
          center: _ProfileImage(image: widget.data.projectImage),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _TitleText(widget.data.projectName),
              const SizedBox(height: 8),
              Row(
                children: [
                  _SubtitleText('chart.currentTimeLabel'.tr),
                  _ReleaseTimeText(_currentTime),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProgressIndicator extends StatelessWidget {
  const _ProgressIndicator({
    required this.percent,
    required this.center,
  });

  final double percent;
  final Widget center;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;
    final Color progressColor =
        isLight ? Theme.of(context).primaryColor : Colors.blueAccent;
    return CircularPercentIndicator(
      radius: 45,
      lineWidth: 4.0,
      percent: percent,
      center: center,
      circularStrokeCap: CircularStrokeCap.round,
      backgroundColor: Colors.grey.shade300,
      progressColor: progressColor,
    );
  }
}

class _ProfileImage extends StatelessWidget {
  const _ProfileImage({required this.image});

  final ImageProvider image;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;
    return ClipOval(
      child: Container(
        width: 40,
        height: 40,
        color: isLight ? Colors.grey.shade200 : Colors.grey.shade800,
        child: Image(
          image: image,
          fit: BoxFit.cover,
        ),
      ),
    );
  }
}

class _TitleText extends StatelessWidget {
  const _TitleText(this.data);

  final String data;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;
    final Color textColor = isLight ? Colors.black87 : Colors.white;
    return Text(
      data.tr,
      style: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: textColor,
        letterSpacing: 1.0,
      ),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }
}

class _SubtitleText extends StatelessWidget {
  const _SubtitleText(this.data);

  final String data;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;
    final Color textColor = isLight ? Colors.black54 : Colors.white70;
    return Text(
      data,
      style: TextStyle(
        fontSize: 12,
        color: textColor,
      ),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }
}

class _ReleaseTimeText extends StatelessWidget {
  const _ReleaseTimeText(this.date);

  final DateTime date;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;
    final Color bgColor = isLight
        ? kNotifColor.withAlpha((0.8 * 255).toInt())
        : kNotifColor.withAlpha((0.6 * 255).toInt());
    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Text(
        formatProjectCardTime(date),
        style: const TextStyle(
          fontSize: 10,
          color: Colors.white,
          fontWeight: FontWeight.w500,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}
