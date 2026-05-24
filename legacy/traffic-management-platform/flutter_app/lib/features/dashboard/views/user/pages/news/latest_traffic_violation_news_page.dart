import 'package:final_assignment_front/features/api/traffic_news_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/views/user/widgets/news_page_layout.dart';
import 'package:final_assignment_front/features/model/traffic_news_article.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/news_localizers.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class LatestTrafficViolationNewsPage extends StatefulWidget {
  const LatestTrafficViolationNewsPage({super.key});

  @override
  State<LatestTrafficViolationNewsPage> createState() =>
      _LatestTrafficViolationNewsPageState();
}

class _LatestTrafficViolationNewsPageState
    extends State<LatestTrafficViolationNewsPage> {
  final TrafficNewsControllerApi _newsApi = TrafficNewsControllerApi();

  List<TrafficNewsArticleModel> _articles = const [];
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadTrafficNews();
  }

  Future<void> _loadTrafficNews() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      await _newsApi.initializeWithJwt();
      final articles = await _newsApi.apiNewsTrafficGet(limit: 12);
      if (!mounted) {
        return;
      }
      setState(() {
        _articles = articles;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = 'news.latest.loadFailed'.trParams({
          'error': localizeApiErrorDetail(error),
        });
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return NewsPageLayout(
      title: 'news.latest.title'.tr,
      accentColor: Colors.blueAccent,
      trailing: [
        IconButton(
          tooltip: 'news.latest.action.refresh'.tr,
          onPressed: _loadTrafficNews,
          icon: const Icon(Icons.refresh, color: Colors.white),
        ),
      ],
      contentBuilder: (context, theme) {
        if (_isLoading) {
          return SizedBox(
            height: MediaQuery.of(context).size.height * 0.5,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CupertinoActivityIndicator(
                    color: theme.colorScheme.primary,
                    radius: 16,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'news.latest.loading'.tr,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          );
        }

        if (_errorMessage.isNotEmpty) {
          return _buildErrorState(context, theme);
        }

        if (_articles.isEmpty) {
          return _buildEmptyState(context, theme);
        }

        final headline = _articles.first;
        final others = _articles.skip(1).toList();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionTitle(context, 'news.latest.heroLabel'.tr),
            _buildHeadlineCard(context, headline),
            const SizedBox(height: 16),
            _buildSectionTitle(context, 'news.latest.section.liveFeed'.tr),
            ...others.map((article) => _buildNewsCard(context, article)),
          ],
        );
      },
    );
  }

  Widget _buildErrorState(BuildContext context, ThemeData theme) {
    return Center(
      child: Card(
        elevation: 2,
        color: theme.colorScheme.errorContainer,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.newspaper,
                color: theme.colorScheme.onErrorContainer,
                size: 32,
              ),
              const SizedBox(height: 12),
              Text(
                _errorMessage,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onErrorContainer,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _loadTrafficNews,
                icon: const Icon(Icons.refresh),
                label: Text('news.latest.action.retry'.tr),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, ThemeData theme) {
    return Center(
      child: Card(
        elevation: 2,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.feed_outlined,
                color: theme.colorScheme.onSurfaceVariant,
                size: 32,
              ),
              const SizedBox(height: 12),
              Text(
                'news.latest.emptyRealtime'.tr,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(BuildContext context, String title) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: theme.textTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.bold,
          color: theme.colorScheme.onSurface,
        ),
      ),
    );
  }

  Widget _buildHeadlineCard(
    BuildContext context,
    TrafficNewsArticleModel article,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final imageUrl = article.image;

    return Card(
      elevation: 5,
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (imageUrl != null && imageUrl.isNotEmpty)
            AspectRatio(
              aspectRatio: 16 / 9,
              child: Image.network(
                imageUrl,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: colorScheme.surfaceContainerHighest,
                  alignment: Alignment.center,
                  child: Icon(
                    Icons.image_not_supported_outlined,
                    color: colorScheme.onSurfaceVariant,
                    size: 36,
                  ),
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _buildMetaChip(
                      context,
                      'news.latest.field.source'.trParams({
                        'value': article.sourceName ??
                            'news.latest.source.unknown'.tr,
                      }),
                    ),
                    _buildMetaChip(
                      context,
                      'news.latest.field.publishedAt'.trParams({
                        'value': formatNewsDate(
                          article.publishedAt ?? DateTime.now(),
                        ),
                      }),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  article.title ?? 'common.unknown'.tr,
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: colorScheme.onSurface,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  _articleSummary(article),
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                    height: 1.45,
                  ),
                ),
                if ((article.url ?? '').isNotEmpty) ...[
                  const SizedBox(height: 14),
                  SelectableText(
                    article.url!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.primary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNewsCard(
    BuildContext context,
    TrafficNewsArticleModel article,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      elevation: 3,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              article.title ?? 'common.unknown'.tr,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _articleSummary(article),
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                Text(
                  'news.latest.field.source'.trParams({
                    'value':
                        article.sourceName ?? 'news.latest.source.unknown'.tr,
                  }),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                Text(
                  'news.latest.field.publishedAt'.trParams({
                    'value': formatNewsDate(
                      article.publishedAt ?? DateTime.now(),
                    ),
                  }),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            if ((article.url ?? '').isNotEmpty) ...[
              const SizedBox(height: 10),
              SelectableText(
                article.url!,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.primary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMetaChip(BuildContext context, String text) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        text,
        style: theme.textTheme.bodySmall?.copyWith(
          color: theme.colorScheme.onSurfaceVariant,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  String _articleSummary(TrafficNewsArticleModel article) {
    final candidates = [
      article.description,
      article.content,
    ];
    for (final candidate in candidates) {
      final trimmed = candidate?.trim() ?? '';
      if (trimmed.isNotEmpty) {
        return trimmed;
      }
    }
    return 'news.latest.emptyRealtime'.tr;
  }
}
