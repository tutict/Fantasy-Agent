import 'package:final_assignment_front/features/dashboard/views/user/widgets/news_page_layout.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class AccidentProgressPage extends StatelessWidget {
  const AccidentProgressPage({super.key});

  @override
  Widget build(BuildContext context) {
    return NewsPageLayout(
      title: 'news.accidentProgress.title'.tr,
      accentColor: Colors.deepPurple,
      contentBuilder: (context, theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle(context, 'news.accidentProgress.section.howTo'.tr),
          _buildStepCard(
            context,
            1,
            'news.accidentProgress.step1.title'.tr,
            'news.accidentProgress.step1.body'.tr,
          ),
          _buildStepCard(
            context,
            2,
            'news.accidentProgress.step2.title'.tr,
            'news.accidentProgress.step2.body'.tr,
          ),
          _buildStepCard(
            context,
            3,
            'news.accidentProgress.step3.title'.tr,
            'news.accidentProgress.step3.body'.tr,
          ),
          const SizedBox(height: 16),
          _buildSectionTitle(context, 'news.accidentProgress.section.tips'.tr),
          _buildContentCard(
            context,
            'news.accidentProgress.tip1.title'.tr,
            'news.accidentProgress.tip1.body'.tr,
          ),
          _buildContentCard(
            context,
            'news.accidentProgress.tip2.title'.tr,
            'news.accidentProgress.tip2.body'.tr,
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

  Widget _buildContentCard(
    BuildContext context,
    String title,
    String description,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    return Card(
      color: colorScheme.surfaceContainerHighest,
      elevation: 2,
      margin: const EdgeInsets.symmetric(vertical: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              description,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
