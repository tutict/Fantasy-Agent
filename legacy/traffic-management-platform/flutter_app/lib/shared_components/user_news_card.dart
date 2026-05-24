import 'package:eva_icons_flutter/eva_icons_flutter.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class UserNewsCard extends StatelessWidget {
  const UserNewsCard({
    super.key,
    required this.onPressed,
    this.onPressedSecond,
    this.onPressedThird,
    this.onPressedFourth,
    this.onPressedFifth,
    this.onPressedSixth,
  });

  final Function()? onPressed;
  final Function()? onPressedSecond;
  final Function()? onPressedThird;
  final Function()? onPressedFourth;
  final Function()? onPressedFifth;
  final Function()? onPressedSixth;

  @override
  Widget build(BuildContext context) {
    final Color cardBackgroundColor = Theme.of(context).cardColor;

    return Card(
      elevation: 2.0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16.0),
      ),
      margin: const EdgeInsets.all(16.0),
      color: cardBackgroundColor,
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _buildHeader(context),
            const Divider(
              thickness: 2,
              indent: 16,
              endIndent: 16,
              color: Colors.blueAccent,
            ),
            const SizedBox(height: 16.0),
            Expanded(
              child: SingleChildScrollView(
                child: _buildNewsList(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0),
      child: Text(
        'news.menu.title'.tr,
        style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: Theme.of(context).colorScheme.onSurface,
            ),
      ),
    );
  }

  Widget _buildNewsList(BuildContext context) {
    final newsItems = <Map<String, dynamic>>[
      {
        'title': 'news.menu.latest.title'.tr,
        'description': 'news.menu.latest.description'.tr,
        'onPressed': onPressed,
        'icon': EvaIcons.fileTextOutline,
      },
      if (onPressedSecond != null)
        {
          'title': 'news.menu.fine.title'.tr,
          'description': 'news.menu.fine.description'.tr,
          'onPressed': onPressedSecond,
          'icon': EvaIcons.creditCardOutline,
        },
      if (onPressedThird != null)
        {
          'title': 'news.menu.quickGuide.title'.tr,
          'description': 'news.menu.quickGuide.description'.tr,
          'onPressed': onPressedThird,
          'icon': EvaIcons.carOutline,
        },
      if (onPressedFourth != null)
        {
          'title': 'news.menu.progress.title'.tr,
          'description': 'news.menu.progress.description'.tr,
          'onPressed': onPressedFourth,
          'icon': EvaIcons.clockOutline,
        },
      if (onPressedFifth != null)
        {
          'title': 'news.menu.evidence.title'.tr,
          'description': 'news.menu.evidence.description'.tr,
          'onPressed': onPressedFifth,
          'icon': EvaIcons.archiveOutline,
        },
      if (onPressedSixth != null)
        {
          'title': 'news.menu.video.title'.tr,
          'description': 'news.menu.video.description'.tr,
          'onPressed': onPressedSixth,
          'icon': EvaIcons.videoOutline,
        },
    ];

    return Column(
      children: newsItems
          .map(
            (item) => _buildNewsItem(
              context,
              onPressed: item['onPressed'],
              title: item['title'],
              description: item['description'],
              icon: item['icon'],
            ),
          )
          .toList(),
    );
  }

  Widget _buildNewsItem(
    BuildContext context, {
    required Function()? onPressed,
    required String title,
    required String description,
    required IconData icon,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(12.0),
        child: Container(
          padding: const EdgeInsets.all(16.0),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12.0),
            color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.8),
            border: Border.all(
              color:
                  Theme.of(context).colorScheme.primary.withValues(alpha: 0.2),
            ),
          ),
          child: Row(
            children: [
              Icon(
                icon,
                color: Theme.of(context).colorScheme.primary,
                size: 32,
              ),
              const SizedBox(width: 16.0),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: Theme.of(context).colorScheme.onSurface,
                            fontWeight: FontWeight.bold,
                          ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4.0),
                    Text(
                      description,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withValues(alpha: 0.7),
                          ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
