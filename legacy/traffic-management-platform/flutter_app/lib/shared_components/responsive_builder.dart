import 'package:flutter/material.dart';

enum ResponsiveTier {
  phone,
  tablet,
  desktop,
  wide,
}

class ResponsiveMetrics {
  const ResponsiveMetrics._({
    required this.width,
    required this.tier,
  });

  factory ResponsiveMetrics.of(BuildContext context) {
    return ResponsiveMetrics.fromWidth(MediaQuery.of(context).size.width);
  }

  factory ResponsiveMetrics.fromWidth(double width) {
    return ResponsiveMetrics._(
      width: width,
      tier: _tierForWidth(width),
    );
  }

  final double width;
  final ResponsiveTier tier;

  bool get isPhone => tier == ResponsiveTier.phone;
  bool get isTablet => tier == ResponsiveTier.tablet;
  bool get isDesktop => tier == ResponsiveTier.desktop;
  bool get isWide => tier == ResponsiveTier.wide;

  double get pagePadding {
    switch (tier) {
      case ResponsiveTier.phone:
        return 16;
      case ResponsiveTier.tablet:
        return 20;
      case ResponsiveTier.desktop:
        return 24;
      case ResponsiveTier.wide:
        return 32;
    }
  }

  double get sectionGap {
    switch (tier) {
      case ResponsiveTier.phone:
        return 12;
      case ResponsiveTier.tablet:
        return 16;
      case ResponsiveTier.desktop:
        return 18;
      case ResponsiveTier.wide:
        return 24;
    }
  }

  double get contentMaxWidth {
    switch (tier) {
      case ResponsiveTier.phone:
        return width;
      case ResponsiveTier.tablet:
        return 960;
      case ResponsiveTier.desktop:
        return 1280;
      case ResponsiveTier.wide:
        return 1480;
    }
  }

  static ResponsiveTier _tierForWidth(double width) {
    if (width >= 1440) return ResponsiveTier.wide;
    if (width >= 1100) return ResponsiveTier.desktop;
    if (width >= 700) return ResponsiveTier.tablet;
    return ResponsiveTier.phone;
  }
}

class ResponsiveBuilder extends StatelessWidget {
  const ResponsiveBuilder({
    required this.mobileBuilder,
    required this.tabletBuilder,
    required this.desktopBuilder,
    this.wideBuilder,
    super.key,
  });

  final Widget Function(
    BuildContext context,
    BoxConstraints constraints,
  ) mobileBuilder;

  final Widget Function(
    BuildContext context,
    BoxConstraints constraints,
  ) tabletBuilder;

  final Widget Function(
    BuildContext context,
    BoxConstraints constraints,
  ) desktopBuilder;

  final Widget Function(
    BuildContext context,
    BoxConstraints constraints,
  )? wideBuilder;

  static bool isMobile(BuildContext context) =>
      ResponsiveMetrics.of(context).isPhone;

  static bool isTablet(BuildContext context) =>
      ResponsiveMetrics.of(context).isTablet;

  static bool isDesktop(BuildContext context) =>
      ResponsiveMetrics.of(context).isDesktop ||
      ResponsiveMetrics.of(context).isWide;

  static bool isWideDesktop(BuildContext context) =>
      ResponsiveMetrics.of(context).isWide;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      transitionBuilder: (child, animation) => FadeTransition(
        opacity: animation,
        child: child,
      ),
      child: LayoutBuilder(
        key: ValueKey(MediaQuery.of(context).size.width),
        builder: (context, constraints) {
          final metrics = ResponsiveMetrics.fromWidth(constraints.maxWidth);

          switch (metrics.tier) {
            case ResponsiveTier.wide:
              return wideBuilder?.call(context, constraints) ??
                  desktopBuilder(context, constraints);
            case ResponsiveTier.desktop:
              return desktopBuilder(context, constraints);
            case ResponsiveTier.tablet:
              return tabletBuilder(context, constraints);
            case ResponsiveTier.phone:
              return mobileBuilder(context, constraints);
          }
        },
      ),
    );
  }
}
