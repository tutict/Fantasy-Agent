import 'package:final_assignment_front/features/dashboard/views/user/widgets/news_page_layout.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class AccidentQuickGuidePage extends StatelessWidget {
  const AccidentQuickGuidePage({super.key});

  @override
  Widget build(BuildContext context) {
    return NewsPageLayout(
      title: 'news.accidentQuickGuide.title'.tr,
      accentColor: Colors.teal,
      contentBuilder: (context, theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle(
              context, 'news.accidentQuickGuide.section.steps'.tr),
          _buildStepCard(
            context,
            1,
            'news.accidentQuickGuide.step1.title'.tr,
            'news.accidentQuickGuide.step1.body'.tr,
          ),
          _buildStepCard(
            context,
            2,
            'news.accidentQuickGuide.step2.title'.tr,
            'news.accidentQuickGuide.step2.body'.tr,
          ),
          _buildStepCard(
            context,
            3,
            'news.accidentQuickGuide.step3.title'.tr,
            'news.accidentQuickGuide.step3.body'.tr,
          ),
          _buildSectionTitle(
              context, 'news.accidentQuickGuide.section.notice'.tr),
          _buildStepCard(
            context,
            4,
            'news.accidentQuickGuide.step4.title'.tr,
            'news.accidentQuickGuide.step4.body'.tr,
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(BuildContext context, String title) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        title,
        style: theme.textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.bold,
          color: theme.colorScheme.onSurface,
        ),
      ),
    );
  }

  Widget _buildStepCard(
    BuildContext context,
    int stepNumber,
    String title,
    String content,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    return Card(
      elevation: 4,
      margin: const EdgeInsets.symmetric(vertical: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: colorScheme.primary,
          child: Text(
            '$stepNumber',
            style: const TextStyle(color: Colors.white),
          ),
        ),
        title: Text(
          title,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: colorScheme.onSurface,
          ),
        ),
        subtitle: Text(
          content,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }
}
