import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/components/ai_chat.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/agent_dashboard_shell.dart';
import 'package:final_assignment_front/shared_components/responsive_builder.dart';
import 'package:final_assignment_front/utils/navigation/page_resolver.dart';

class UserDashboard extends GetView<UserDashboardController> {
  const UserDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    controller.pageResolver ??= resolveDashboardPage;

    return Obx(() {
      final theme = controller.currentBodyTheme.value;
      final profile = controller.currentProfile;

      return AgentDashboardShell(
        scaffoldKey: controller.scaffoldKey,
        theme: theme,
        title: 'user.title'.tr,
        subtitle: 'user.subtitle'.tr,
        profile: profile,
        navigationItems: _navigationItems(),
        chatPanel: const AiChat(),
        onToggleTheme: controller.toggleBodyTheme,
        body: controller.selectedPage.value != null
            ? _SelectedPageFrame(
                title: 'user.pageTitle'.tr,
                onBack: controller.exitSidebarContent,
                child: controller.selectedPage.value!,
              )
            : _UserHome(
                controller: controller,
                onOpenAgent: () => Get.toNamed(Routes.aiChat),
              ),
      );
    });
  }

  List<AgentDashboardNavItem> _navigationItems() {
    final homeActive = controller.selectedPage.value == null;

    return [
      AgentDashboardNavItem(
        label: 'common.home'.tr,
        icon: Icons.home_rounded,
        active: homeActive,
        onTap: controller.exitSidebarContent,
      ),
      AgentDashboardNavItem(
        label: 'user.nav.progress'.tr,
        icon: Icons.timeline_rounded,
        onTap: () => controller.navigateToPage(Routes.businessProgress),
      ),
      AgentDashboardNavItem(
        label: 'user.nav.records'.tr,
        icon: Icons.fact_check_outlined,
        onTap: () => controller.navigateToPage(Routes.userOffenseListPage),
      ),
      AgentDashboardNavItem(
        label: 'common.profile'.tr,
        icon: Icons.perm_identity_rounded,
        onTap: () => controller.navigateToPage(Routes.personalMain),
      ),
      AgentDashboardNavItem(
        label: 'user.nav.news'.tr,
        icon: Icons.newspaper_rounded,
        onTap: () =>
            controller.navigateToPage(Routes.latestTrafficViolationNewsPage),
      ),
      AgentDashboardNavItem(
        label: 'user.nav.support'.tr,
        icon: Icons.support_agent_rounded,
        onTap: () => controller.navigateToPage(Routes.consultation),
      ),
      AgentDashboardNavItem(
        label: 'common.settings'.tr,
        icon: Icons.tune_rounded,
        onTap: () => controller.navigateToPage(Routes.userSetting),
      ),
    ];
  }
}

class _UserHome extends StatelessWidget {
  const _UserHome({
    required this.controller,
    required this.onOpenAgent,
  });

  final UserDashboardController controller;
  final VoidCallback onOpenAgent;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final metrics = ResponsiveMetrics.of(context);
    final displayName = controller.currentDriverName.value.isNotEmpty
        ? controller.currentDriverName.value
        : controller.currentProfile.name;
    final profileReady = controller.driverLicenseNumber.value.isNotEmpty &&
        controller.idCardNumber.value.isNotEmpty;

    return SingleChildScrollView(
      padding: EdgeInsets.all(metrics.pagePadding),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: metrics.contentMaxWidth),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _RevealIn(
                delay: const Duration(milliseconds: 40),
                child: _WorkspaceOverview(
                  eyebrow: 'common.userWorkspace'.tr,
                  title: displayName,
                  summary: profileReady
                      ? 'user.metric.identityReadyDetail'.tr
                      : 'user.metric.identityPendingDetail'.tr,
                  metrics: [
                    _OverviewMetric(
                      label: 'user.metric.identity'.tr,
                      value: profileReady
                          ? 'user.metric.identityReady'.tr
                          : 'user.metric.identityPending'.tr,
                      accent: profileReady
                          ? const Color(0xFF1D7E5D)
                          : const Color(0xFFB8852E),
                    ),
                    _OverviewMetric(
                      label: 'common.theme'.tr,
                      value: controller.currentTheme.value == 'Dark'
                          ? 'common.dark'.tr
                          : 'common.light'.tr,
                      accent: theme.colorScheme.primary,
                    ),
                    _OverviewMetric(
                      label: 'common.agent'.tr,
                      value: controller.isLoadingUser.value
                          ? 'user.metric.agentSyncing'.tr
                          : 'common.online'.tr,
                      accent: const Color(0xFF2F6FD6),
                    ),
                  ],
                  queue: [
                    'user.today.line1'.tr,
                    'user.today.line2'.tr,
                    'user.today.line3'.tr,
                  ],
                  primaryLabel: 'common.openAgent'.tr,
                  secondaryLabel: 'user.hero.secondary'.tr,
                  onPrimaryPressed: onOpenAgent,
                  onSecondaryPressed: () =>
                      controller.navigateToPage(Routes.businessProgress),
                ),
              ),
              SizedBox(height: metrics.sectionGap + 8),
              _RevealIn(
                delay: const Duration(milliseconds: 120),
                child: _SectionTitleBlock(
                  eyebrow: 'common.workspace'.tr,
                  title: 'user.quickAccess'.tr,
                  description: 'user.metric.agentDetail'.tr,
                ),
              ),
              SizedBox(height: metrics.sectionGap),
              _RevealIn(
                delay: const Duration(milliseconds: 180),
                child: _ActionDeck(
                  actions: [
                    _DeckAction(
                      index: '01',
                      title: 'user.card.progress.title'.tr,
                      subtitle: 'user.card.progress.subtitle'.tr,
                      onTap: () =>
                          controller.navigateToPage(Routes.businessProgress),
                    ),
                    _DeckAction(
                      index: '02',
                      title: 'user.card.records.title'.tr,
                      subtitle: 'user.card.records.subtitle'.tr,
                      onTap: () =>
                          controller.navigateToPage(Routes.userOffenseListPage),
                    ),
                    _DeckAction(
                      index: '03',
                      title: 'user.card.profile.title'.tr,
                      subtitle: 'user.card.profile.subtitle'.tr,
                      onTap: () =>
                          controller.navigateToPage(Routes.personalMain),
                    ),
                    _DeckAction(
                      index: '04',
                      title: 'user.card.news.title'.tr,
                      subtitle: 'user.card.news.subtitle'.tr,
                      onTap: () => controller.navigateToPage(
                          Routes.latestTrafficViolationNewsPage),
                    ),
                    _DeckAction(
                      index: '05',
                      title: 'user.card.support.title'.tr,
                      subtitle: 'user.card.support.subtitle'.tr,
                      onTap: () =>
                          controller.navigateToPage(Routes.consultation),
                    ),
                    _DeckAction(
                      index: '06',
                      title: 'user.card.preferences.title'.tr,
                      subtitle: 'user.card.preferences.subtitle'.tr,
                      onTap: () =>
                          controller.navigateToPage(Routes.userSetting),
                    ),
                  ],
                ),
              ),
              SizedBox(height: metrics.sectionGap + 8),
              _RevealIn(
                delay: const Duration(milliseconds: 240),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final stacked = constraints.maxWidth < 920;
                    final left = _UtilityPanel(
                      title: 'common.today'.tr,
                      description: 'user.metric.agentDetail'.tr,
                      rows: [
                        _UtilityRow(
                          label: 'user.focus.profileStatus'.tr,
                          value: profileReady
                              ? 'user.focus.profileReady'.tr
                              : 'user.focus.profilePending'.tr,
                        ),
                        _UtilityRow(
                          label: 'user.focus.agentPanel'.tr,
                          value: 'user.focus.agentPanelValue'.tr,
                        ),
                        _UtilityRow(
                          label: 'user.focus.workspace'.tr,
                          value: 'user.focus.workspaceValue'.tr,
                        ),
                      ],
                    );
                    final right = _PlainChecklist(
                      title: 'common.focus'.tr,
                      items: const [
                        'user.today.line1',
                        'user.today.line2',
                        'user.today.line3',
                      ],
                    );

                    if (stacked) {
                      return Column(
                        children: [
                          left,
                          SizedBox(height: metrics.sectionGap),
                          right,
                        ],
                      );
                    }

                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(flex: 5, child: left),
                        SizedBox(width: metrics.sectionGap),
                        Expanded(flex: 4, child: right),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SelectedPageFrame extends StatelessWidget {
  const _SelectedPageFrame({
    required this.title,
    required this.onBack,
    required this.child,
  });

  final String title;
  final VoidCallback onBack;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.92),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 18, 22, 16),
            child: Row(
              children: [
                IconButton.filledTonal(
                  onPressed: onBack,
                  icon: const Icon(Icons.arrow_back_rounded),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.titleLarge,
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(child: child),
        ],
      ),
    );
  }
}

class _WorkspaceOverview extends StatelessWidget {
  const _WorkspaceOverview({
    required this.eyebrow,
    required this.title,
    required this.summary,
    required this.metrics,
    required this.queue,
    required this.primaryLabel,
    required this.secondaryLabel,
    required this.onPrimaryPressed,
    required this.onSecondaryPressed,
  });

  final String eyebrow;
  final String title;
  final String summary;
  final List<_OverviewMetric> metrics;
  final List<String> queue;
  final String primaryLabel;
  final String secondaryLabel;
  final VoidCallback onPrimaryPressed;
  final VoidCallback onSecondaryPressed;

  String profileReadyLabel(List<_OverviewMetric> metrics) {
    if (metrics.isEmpty) {
      return 'common.online'.tr;
    }
    return metrics.first.value;
  }

  Color _resolveStatusAccent(List<_OverviewMetric> metrics) {
    if (metrics.isEmpty) {
      return const Color(0xFF2F6FD6);
    }
    return metrics.first.accent;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF071924),
            Color(0xFF0D2B38),
            Color(0xFF16404C),
          ],
        ),
        borderRadius: BorderRadius.circular(30),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 920;
          final narrow = constraints.maxWidth < 420;
          final signalBand = _SignalBand(metrics: metrics);
          final lead = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _WorkspaceBadge(label: eyebrow.toUpperCase()),
                  _WorkspaceBadge(
                    label: profileReadyLabel(metrics).toUpperCase(),
                    accent: _resolveStatusAccent(metrics),
                    filled: true,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                title,
                style: (narrow
                        ? theme.textTheme.headlineMedium
                        : theme.textTheme.displayMedium)
                    ?.copyWith(
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 10),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 520),
                child: Text(
                  summary,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: Colors.white.withValues(alpha: 0.78),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Text(
                'common.focus'.tr.toUpperCase(),
                style: theme.textTheme.labelMedium?.copyWith(
                  color: Colors.white.withValues(alpha: 0.56),
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 10),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 560),
                child: Text(
                  'user.card.progress.subtitle'.tr,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: Colors.white.withValues(alpha: 0.88),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  FilledButton(
                    onPressed: onPrimaryPressed,
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: const Color(0xFF0D2936),
                    ),
                    child: Text(primaryLabel),
                  ),
                  OutlinedButton(
                    onPressed: onSecondaryPressed,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: BorderSide(
                        color: Colors.white.withValues(alpha: 0.16),
                      ),
                    ),
                    child: Text(secondaryLabel),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              signalBand,
            ],
          );
          final side = _PriorityLane(
            queue: queue,
            syncLabel: metrics.last.value,
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                lead,
                const SizedBox(height: 22),
                side,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 7, child: lead),
              const SizedBox(width: 28),
              Expanded(flex: 4, child: side),
            ],
          );
        },
      ),
    );
  }
}

class _OverviewMetric {
  const _OverviewMetric({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;
}

class _MetricRail extends StatelessWidget {
  const _MetricRail({required this.metric});

  final _OverviewMetric metric;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ConstrainedBox(
      constraints: const BoxConstraints(
        minWidth: 132,
        maxWidth: 180,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            metric.label,
            style: theme.textTheme.labelMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.56),
            ),
          ),
          const SizedBox(height: 8),
          Container(
            width: 42,
            height: 3,
            color: metric.accent,
          ),
          const SizedBox(height: 10),
          Text(
            metric.value,
            style: theme.textTheme.titleLarge?.copyWith(
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}

class _SignalBand extends StatelessWidget {
  const _SignalBand({required this.metrics});

  final List<_OverviewMetric> metrics;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.08),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 520;
          if (compact) {
            return Column(
              children: [
                for (var i = 0; i < metrics.length; i++) ...[
                  _MetricRail(metric: metrics[i]),
                  if (i != metrics.length - 1)
                    Divider(
                      color: Colors.white.withValues(alpha: 0.10),
                      height: 22,
                    ),
                ],
              ],
            );
          }

          return Row(
            children: [
              for (var i = 0; i < metrics.length; i++) ...[
                Expanded(child: _MetricRail(metric: metrics[i])),
                if (i != metrics.length - 1)
                  Container(
                    width: 1,
                    height: 44,
                    color: Colors.white.withValues(alpha: 0.10),
                    margin: const EdgeInsets.symmetric(horizontal: 18),
                  ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _WorkspaceBadge extends StatelessWidget {
  const _WorkspaceBadge({
    required this.label,
    this.accent = Colors.white,
    this.filled = false,
  });

  final String label;
  final Color accent;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    final background = filled
        ? accent.withValues(alpha: 0.18)
        : Colors.white.withValues(alpha: 0.08);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: filled ? accent.withValues(alpha: 0.28) : Colors.white10,
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: filled ? accent : Colors.white.withValues(alpha: 0.80),
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
      ),
    );
  }
}

class _PriorityLane extends StatelessWidget {
  const _PriorityLane({
    required this.queue,
    required this.syncLabel,
  });

  final List<String> queue;
  final String syncLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.08),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'common.today'.tr.toUpperCase(),
            style: theme.textTheme.labelMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.62),
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 14),
          ...queue.asMap().entries.map(
                (entry) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: _PriorityEntry(
                    index: entry.key + 1,
                    text: entry.value,
                  ),
                ),
              ),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Row(
              children: [
                Expanded(
                  child: _CompactStatus(
                    label: 'common.agent'.tr,
                    value: syncLabel,
                  ),
                ),
                Container(
                  width: 1,
                  height: 32,
                  color: Colors.white.withValues(alpha: 0.10),
                ),
                Expanded(
                  child: _CompactStatus(
                    label: 'common.workspace'.tr,
                    value: 'user.focus.workspaceValue'.tr,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PriorityEntry extends StatelessWidget {
  const _PriorityEntry({
    required this.index,
    required this.text,
  });

  final int index;
  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 28,
          height: 28,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            index.toString().padLeft(2, '0'),
            style: theme.textTheme.labelMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.80),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.86),
            ),
          ),
        ),
      ],
    );
  }
}

class _CompactStatus extends StatelessWidget {
  const _CompactStatus({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: Colors.white.withValues(alpha: 0.56),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: theme.textTheme.labelLarge?.copyWith(
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitleBlock extends StatelessWidget {
  const _SectionTitleBlock({
    required this.eyebrow,
    required this.title,
    required this.description,
  });

  final String eyebrow;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          eyebrow.toUpperCase(),
          style: theme.textTheme.labelMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 6),
        Text(title, style: theme.textTheme.headlineSmall),
        const SizedBox(height: 6),
        Text(description, style: theme.textTheme.bodyMedium),
      ],
    );
  }
}

class _ActionDeck extends StatelessWidget {
  const _ActionDeck({required this.actions});

  final List<_DeckAction> actions;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.22),
        ),
      ),
      child: Column(
        children: actions
            .asMap()
            .entries
            .map(
              (entry) => Column(
                children: [
                  _ActionRow(action: entry.value),
                  if (entry.key != actions.length - 1)
                    Divider(
                      height: 1,
                      color: theme.colorScheme.outlineVariant.withValues(
                        alpha: 0.22,
                      ),
                    ),
                ],
              ),
            )
            .toList(),
      ),
    );
  }
}

class _DeckAction {
  const _DeckAction({
    required this.index,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final String index;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
}

class _ActionRow extends StatefulWidget {
  const _ActionRow({required this.action});

  final _DeckAction action;

  @override
  State<_ActionRow> createState() => _ActionRowState();
}

class _ActionRowState extends State<_ActionRow> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: InkWell(
        onTap: widget.action.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
          transform: Matrix4.translationValues(_hovered ? 4 : 0, 0, 0),
          color: _hovered
              ? theme.colorScheme.primary.withValues(alpha: 0.04)
              : Colors.transparent,
          child: Row(
            children: [
              SizedBox(
                width: 42,
                child: Text(
                  widget.action.index,
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: theme.colorScheme.primary.withValues(alpha: 0.78),
                  ),
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(widget.action.title,
                        style: theme.textTheme.titleMedium),
                    const SizedBox(height: 5),
                    Text(
                      widget.action.subtitle,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.arrow_outward_rounded,
                color: theme.colorScheme.primary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _UtilityPanel extends StatelessWidget {
  const _UtilityPanel({
    required this.title,
    required this.description,
    required this.rows,
  });

  final String title;
  final String description;
  final List<_UtilityRow> rows;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return LayoutBuilder(
      builder: (context, constraints) {
        final stacked = constraints.maxWidth < 520;

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface.withValues(alpha: 0.78),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(
              color: theme.colorScheme.outlineVariant.withValues(alpha: 0.22),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: theme.textTheme.titleLarge),
              const SizedBox(height: 6),
              Text(description, style: theme.textTheme.bodyMedium),
              const SizedBox(height: 18),
              ...rows.map(
                (row) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: stacked
                      ? Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              row.label,
                              style: theme.textTheme.labelLarge?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(row.value, style: theme.textTheme.bodyLarge),
                          ],
                        )
                      : Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 2,
                              child: Text(
                                row.label,
                                style: theme.textTheme.labelLarge?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ),
                            ),
                            const SizedBox(width: 18),
                            Expanded(
                              flex: 3,
                              child: Text(row.value,
                                  style: theme.textTheme.bodyLarge),
                            ),
                          ],
                        ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _UtilityRow {
  const _UtilityRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;
}

class _PlainChecklist extends StatelessWidget {
  const _PlainChecklist({
    required this.title,
    required this.items,
  });

  final String title;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.78),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.22),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: theme.textTheme.titleLarge),
          const SizedBox(height: 18),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.only(top: 8),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(item.tr, style: theme.textTheme.bodyLarge),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RevealIn extends StatelessWidget {
  const _RevealIn({
    required this.child,
    this.delay = Duration.zero,
  });

  final Widget child;
  final Duration delay;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      duration: const Duration(milliseconds: 360) + delay,
      curve: Curves.easeOutCubic,
      tween: Tween(begin: 0, end: 1),
      builder: (context, value, widget) {
        final delayedValue = delay == Duration.zero
            ? value
            : ((value * (360 + delay.inMilliseconds) - delay.inMilliseconds) /
                    360)
                .clamp(0.0, 1.0);
        return Opacity(
          opacity: delayedValue,
          child: Transform.translate(
            offset: Offset(0, (1 - delayedValue) * 16),
            child: widget,
          ),
        );
      },
      child: child,
    );
  }
}
