import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:get/get.dart';

class PostCard extends StatelessWidget {
  const PostCard({
    required this.onPressed,
    this.backgroundColor,
    super.key,
  });

  final Color? backgroundColor;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Material(
      borderRadius: BorderRadius.circular(kBorderRadius + 4),
      color: backgroundColor ?? Theme.of(context).cardColor,
      elevation: 4.0,
      shadowColor: Colors.black.withValues(alpha: 0.2),
      child: InkWell(
        borderRadius: BorderRadius.circular(kBorderRadius + 4),
        onTap: onPressed,
        child: Container(
          constraints: const BoxConstraints(
            minWidth: 180,
            maxWidth: 300,
            minHeight: 180,
            maxHeight: 300,
          ),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(kBorderRadius + 4),
            gradient: LinearGradient(
              colors: [
                Colors.lightBlueAccent.withValues(alpha: 0.2),
                Colors.blue.withValues(alpha: 0.1),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(
              color: Colors.blueAccent.withValues(alpha: 0.1),
              width: 1,
            ),
          ),
          child: Stack(
            children: [
              Positioned(
                bottom: 8,
                right: 8,
                child: SvgPicture.asset(
                  ImageVectorPath.happy,
                  width: 80,
                  height: 80,
                  colorFilter: ColorFilter.mode(
                    Colors.blueAccent.withValues(alpha: 0.3),
                    BlendMode.srcIn,
                  ),
                  fit: BoxFit.contain,
                ),
              ),
              const Padding(
                padding: EdgeInsets.all(8),
                child: _Info(),
              ),
            ],
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _title(context),
        const SizedBox(height: 12),
        _description(context),
      ],
    );
  }

  Widget _title(BuildContext context) {
    return Text(
      'shared.postCard.title'.tr,
      style: Theme.of(context).textTheme.titleLarge!.copyWith(
            fontSize: 22,
            fontWeight: FontWeight.w600,
            color: Colors.black87,
            letterSpacing: 0.5,
          ),
    );
  }

  Widget _description(BuildContext context) {
    return Text(
      'shared.postCard.body'.tr,
      style: Theme.of(context).textTheme.bodyMedium!.copyWith(
            fontSize: 16,
            color: Colors.black.withValues(alpha: 0.7),
            height: 1.5,
          ),
    );
  }
}
