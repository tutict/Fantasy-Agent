import 'package:final_assignment_front/features/dashboard/views/user/widgets/news_page_layout.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class AccidentEvidencePage extends StatelessWidget {
  const AccidentEvidencePage({super.key});

  @override
  Widget build(BuildContext context) {
    return NewsPageLayout(
      title: 'news.accidentEvidence.title'.tr,
      accentColor: Colors.orangeAccent,
      contentBuilder: (context, theme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle(
              context, 'news.accidentEvidence.section.required'.tr),
          _buildContentCard(
            context,
            'news.accidentEvidence.photo.title'.tr,
            'news.accidentEvidence.photo.body'.tr,
          ),
          _buildContentCard(
            context,
            'news.accidentEvidence.video.title'.tr,
            'news.accidentEvidence.video.body'.tr,
          ),
          _buildContentCard(
            context,
            'news.accidentEvidence.detail.title'.tr,
            'news.accidentEvidence.detail.body'.tr,
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
