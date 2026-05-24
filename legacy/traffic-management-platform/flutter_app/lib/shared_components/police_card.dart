import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:get/get.dart';

class PoliceCard extends StatelessWidget {
  const PoliceCard({
    required this.onPressed,
    this.backgroundColor,
    super.key,
  });

  final Color? backgroundColor;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;

    return Material(
      borderRadius: BorderRadius.circular(18),
      color: backgroundColor ?? Colors.transparent,
      elevation: 4.0,
      shadowColor: Colors.black.withValues(alpha: 0.2),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onPressed,
        splashColor: Theme.of(context).primaryColor.withValues(alpha: 0.3),
        highlightColor: Colors.transparent,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeInOut,
          constraints: const BoxConstraints(
            minWidth: 250,
            maxWidth: 350,
            minHeight: 200,
            maxHeight: 200,
          ),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            gradient: LinearGradient(
              colors: [
                isLight
                    ? Colors.blue.shade50.withValues(alpha: 0.9)
                    : Theme.of(context).canvasColor.withValues(alpha: 0.8),
                isLight
                    ? Colors.white.withValues(alpha: 0.95)
                    : Theme.of(context).cardColor.withValues(alpha: 0.9),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(
              color: isLight
                  ? Colors.blue.shade100
                  : Colors.white.withValues(alpha: 0.3),
              width: 1,
            ),
          ),
          child: ClipRect(
            child: Stack(
              children: [
                Positioned(
                  top: -25,
                  right: -25,
                  child: SvgPicture.asset(
                    ImageVectorPath.police,
                    width: 130,
                    height: 130,
                    fit: BoxFit.contain,
                    colorFilter: ColorFilter.mode(
                      Theme.of(context).primaryColor.withValues(alpha: 0.25),
                      BlendMode.srcIn,
                    ),
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: _Info(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Info extends StatelessWidget {
  const _Info();

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;

    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Flexible(
          child: Text(
            'shared.policeCard.title'.tr,
            style: Theme.of(context).textTheme.titleLarge!.copyWith(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: isLight
                  ? Colors.black.withValues(alpha: 0.9)
                  : Colors.white.withValues(alpha: 0.9),
              height: 1.4,
              letterSpacing: 0.6,
              shadows: [
                Shadow(
                  color: Colors.black.withValues(alpha: 0.1),
                  offset: const Offset(0, 1),
                  blurRadius: 2,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Flexible(
          child: Text(
            'shared.policeCard.body'.tr,
            style: Theme.of(context).textTheme.bodyMedium!.copyWith(
                  fontSize: 14,
                  color: isLight
                      ? Colors.black.withValues(alpha: 0.8)
                      : Colors.white.withValues(alpha: 0.8),
                  height: 1.3,
                  fontWeight: FontWeight.w500,
                ),
          ),
        ),
      ],
    );
  }
}
