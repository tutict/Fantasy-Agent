import 'package:flutter/material.dart';

typedef NewsContentBuilder = Widget Function(
    BuildContext context, ThemeData theme);

class NewsPageLayout extends StatelessWidget {
  const NewsPageLayout({
    super.key,
    required this.title,
    required this.contentBuilder,
    this.accentColor = Colors.blue,
    this.gradient,
    this.leading,
    this.trailing,
  });

  final String title;
  final NewsContentBuilder contentBuilder;
  final Color accentColor;
  final LinearGradient? gradient;
  final Widget? leading;
  final List<Widget>? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;
    final effectiveGradient = gradient ??
        LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _darken(accentColor, isDark ? 0.1 : 0.0),
            colorScheme.surface,
          ],
        );

    return Scaffold(
      backgroundColor: colorScheme.surface,
      body: Container(
        decoration: BoxDecoration(gradient: effectiveGradient),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(context, theme),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: contentBuilder(context, theme),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, ThemeData theme) {
    const textColor = Colors.white;
    final leadingWidget = leading ??
        IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).maybePop(),
        );
    final actions = trailing ?? const <Widget>[];

    return LayoutBuilder(
      builder: (context, constraints) {
        final textScale = MediaQuery.textScalerOf(context).scale(1);
        final isCompact = constraints.maxWidth < 560 || textScale > 1.15;
        final titleWidget = Text(
          title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: isCompact ? 22 : 26,
            fontWeight: FontWeight.bold,
            color: textColor,
            height: 1.1,
          ),
        );

        if (isCompact) {
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    leadingWidget,
                    const SizedBox(width: 8),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: titleWidget,
                      ),
                    ),
                  ],
                ),
                if (actions.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(left: 56, top: 12),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: actions,
                    ),
                  ),
              ],
            ),
          );
        }

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              leadingWidget,
              const SizedBox(width: 8),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: titleWidget,
                ),
              ),
              if (actions.isNotEmpty) ...[
                const SizedBox(width: 12),
                Flexible(
                  child: Align(
                    alignment: Alignment.topRight,
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      alignment: WrapAlignment.end,
                      children: actions,
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Color _darken(Color color, double amount) {
    assert(amount >= 0 && amount <= 1);
    final hsl = HSLColor.fromColor(color);
    final darker = hsl.withLightness((hsl.lightness - amount).clamp(0.0, 1.0));
    return darker.toColor();
  }
}
