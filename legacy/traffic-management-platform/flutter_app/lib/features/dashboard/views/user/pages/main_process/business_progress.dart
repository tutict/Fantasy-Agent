import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/dashboard/views/user/pages/main_process/fine_information.dart';
import 'package:final_assignment_front/features/dashboard/views/user/pages/main_process/online_processing_progress.dart';
import 'package:final_assignment_front/features/dashboard/views/user/pages/main_process/user_appeal.dart';
import 'package:final_assignment_front/features/dashboard/views/user/pages/main_process/user_offense_list_page.dart';
import 'package:final_assignment_front/features/dashboard/views/user/pages/main_process/vehicle_management.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class BusinessProgressPage extends StatefulWidget {
  const BusinessProgressPage({super.key});

  @override
  State<BusinessProgressPage> createState() => _BusinessProgressPageState();
}

class _BusinessProgressPageState extends State<BusinessProgressPage> {
  final UserDashboardController controller =
      Get.find<UserDashboardController>();

  late final List<_BusinessOption> businessOptions = [
    _BusinessOption(
      '01',
      'business.menu.offenseDetail',
      'business.menu.offenseDetail.subtitle',
      Icons.fact_check_outlined,
      const UserOffenseListPage(),
    ),
    _BusinessOption(
      '02',
      'business.menu.finePayment',
      'business.menu.finePayment.subtitle',
      Icons.account_balance_wallet_outlined,
      const FineInformationPage(),
    ),
    _BusinessOption(
      '03',
      'business.menu.userAppeal',
      'business.menu.userAppeal.subtitle',
      Icons.gavel_rounded,
      const UserAppealPage(),
    ),
    _BusinessOption(
      '04',
      'business.menu.onlineProcessingProgress',
      'business.menu.onlineProcessingProgress.subtitle',
      Icons.timeline_rounded,
      const OnlineProcessingProgress(),
    ),
    _BusinessOption(
      '05',
      'business.menu.vehicleManagement',
      'business.menu.vehicleManagement.subtitle',
      Icons.directions_car_filled_outlined,
      const VehicleManagement(),
    ),
  ];

  void _navigateToBusiness(Widget route) {
    Navigator.push(context, MaterialPageRoute(builder: (context) => route));
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final theme = controller.currentBodyTheme.value;
      final profileReady = controller.driverLicenseNumber.value.isNotEmpty &&
          controller.idCardNumber.value.isNotEmpty;
      final displayName = controller.currentDriverName.value.isNotEmpty
          ? controller.currentDriverName.value
          : controller.currentProfile.name;

      return DashboardPageTemplate(
        theme: theme,
        title: 'business.menu.title'.tr,
        pageType: DashboardPageType.user,
        onThemeToggle: controller.toggleBodyTheme,
        backgroundColor: theme.scaffoldBackgroundColor,
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _fade(
              child: _BusinessHero(
                displayName: displayName,
                profileReady: profileReady,
                onOpenProgress: () =>
                    _navigateToBusiness(const OnlineProcessingProgress()),
                onOpenRecords: () =>
                    _navigateToBusiness(const UserOffenseListPage()),
              ),
            ),
            const SizedBox(height: 24),
            _fade(
              delay: 100,
              child: _SectionHeading(
                eyebrow: 'business.menu.signal'.tr,
                title: 'business.menu.sectionTitle'.tr,
                description: 'business.menu.sectionBody'.tr,
              ),
            ),
            const SizedBox(height: 18),
            _fade(
              delay: 180,
              child: _BusinessActionDeck(
                options: businessOptions,
                onTap: _navigateToBusiness,
              ),
            ),
            const SizedBox(height: 24),
            _fade(
              delay: 240,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final stacked = constraints.maxWidth < 920;
                  final left = _InfoPanel(
                    title: 'business.menu.quickStatus'.tr,
                    description: 'business.menu.quickStatusBody'.tr,
                    rows: [
                      _InfoRow(
                        'user.focus.profileStatus'.tr,
                        profileReady
                            ? 'user.focus.profileReady'.tr
                            : 'user.focus.profilePending'.tr,
                      ),
                      _InfoRow(
                        'user.focus.agentPanel'.tr,
                        'user.focus.agentPanelValue'.tr,
                      ),
                      _InfoRow(
                        'common.workspace'.tr,
                        'business.menu.signal'.tr,
                      ),
                    ],
                  );
                  final right = _TipPanel(
                    title: 'business.menu.tipTitle'.tr,
                    items: const [
                      'business.menu.tip1',
                      'business.menu.tip2',
                      'business.menu.tip3',
                    ],
                  );

                  if (stacked) {
                    return Column(
                      children: [
                        left,
                        const SizedBox(height: 18),
                        right,
                      ],
                    );
                  }

                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 5, child: left),
                      const SizedBox(width: 18),
                      Expanded(flex: 4, child: right),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _fade({required Widget child, int delay = 0}) {
    return TweenAnimationBuilder<double>(
      duration: Duration(milliseconds: 360 + delay),
      curve: Curves.easeOutCubic,
      tween: Tween(begin: 0, end: 1),
      builder: (context, value, widget) {
        final delayedValue = delay == 0
            ? value
            : ((value * (360 + delay) - delay) / 360).clamp(0.0, 1.0);
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

class _BusinessOption {
  const _BusinessOption(
    this.index,
    this.titleKey,
    this.subtitleKey,
    this.icon,
    this.route,
  );

  final String index;
  final String titleKey;
  final String subtitleKey;
  final IconData icon;
  final Widget route;
}

class _BusinessHero extends StatelessWidget {
  const _BusinessHero({
    required this.displayName,
    required this.profileReady,
    required this.onOpenProgress,
    required this.onOpenRecords,
  });

  final String displayName;
  final bool profileReady;
  final VoidCallback onOpenProgress;
  final VoidCallback onOpenRecords;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final readyColor =
        profileReady ? const Color(0xFF1F9D68) : const Color(0xFFC28B2C);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF071A24), Color(0xFF0B2B39), Color(0xFF145566)],
        ),
        borderRadius: BorderRadius.circular(30),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 920;
          final lead = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _HeroBadge('business.menu.signal'.tr.toUpperCase()),
                  _HeroBadge(
                    (profileReady
                            ? 'business.menu.ready'
                            : 'business.menu.statusReview')
                        .tr
                        .toUpperCase(),
                    accent: readyColor,
                    filled: true,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                displayName,
                style: theme.textTheme.displayMedium?.copyWith(
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 10),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 560),
                child: Text(
                  'business.menu.subtitle'.tr,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: Colors.white.withValues(alpha: 0.82),
                  ),
                ),
              ),
              const SizedBox(height: 22),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  FilledButton.icon(
                    onPressed: onOpenProgress,
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: const Color(0xFF0C2734),
                    ),
                    icon: const Icon(Icons.timeline_rounded),
                    label: Text('business.menu.onlineProcessingProgress'.tr),
                  ),
                  OutlinedButton.icon(
                    onPressed: onOpenRecords,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: BorderSide(
                        color: Colors.white.withValues(alpha: 0.16),
                      ),
                    ),
                    icon: const Icon(Icons.fact_check_outlined),
                    label: Text('business.menu.offenseDetail'.tr),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              _HeroSignals(profileReady: profileReady),
            ],
          );

          final side = _HeroTips(profileReady: profileReady);
          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [lead, const SizedBox(height: 22), side],
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

class _HeroBadge extends StatelessWidget {
  const _HeroBadge(this.label,
      {this.accent = Colors.white, this.filled = false});

  final String label;
  final Color accent;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: filled
            ? accent.withValues(alpha: 0.18)
            : Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: filled ? accent.withValues(alpha: 0.28) : Colors.white10,
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: filled ? accent : Colors.white.withValues(alpha: 0.82),
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _HeroSignals extends StatelessWidget {
  const _HeroSignals({required this.profileReady});

  final bool profileReady;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final items = [
      (
        'user.focus.profileStatus'.tr,
        (profileReady ? 'business.menu.ready' : 'business.menu.statusReview').tr
      ),
      ('common.agent'.tr, 'common.online'.tr),
      ('common.workspace'.tr, 'business.menu.signal'.tr),
    ];
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Row(
        children: [
          for (var i = 0; i < items.length; i++) ...[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    items[i].$1,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: Colors.white.withValues(alpha: 0.56),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    items[i].$2,
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            if (i != items.length - 1)
              Container(
                width: 1,
                height: 34,
                color: Colors.white.withValues(alpha: 0.10),
                margin: const EdgeInsets.symmetric(horizontal: 18),
              ),
          ],
        ],
      ),
    );
  }
}

class _HeroTips extends StatelessWidget {
  const _HeroTips({required this.profileReady});

  final bool profileReady;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'business.menu.tipTitle'.tr.toUpperCase(),
            style: theme.textTheme.labelMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.62),
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 14),
          for (var i = 1; i <= 3; i++) ...[
            _TipLine(i, 'business.menu.tip$i'.tr),
            if (i != 3) const SizedBox(height: 14),
          ],
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Text(
              profileReady
                  ? 'business.menu.ready'.tr
                  : 'business.menu.statusReview'.tr,
              style: theme.textTheme.labelLarge?.copyWith(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}

class _TipLine extends StatelessWidget {
  const _TipLine(this.index, this.text);

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

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({
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

class _BusinessActionDeck extends StatelessWidget {
  const _BusinessActionDeck({
    required this.options,
    required this.onTap,
  });

  final List<_BusinessOption> options;
  final ValueChanged<Widget> onTap;

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
        children: options.asMap().entries.map((entry) {
          final option = entry.value;
          return Column(
            children: [
              _BusinessActionRow(
                  option: option, onTap: () => onTap(option.route)),
              if (entry.key != options.length - 1)
                Divider(
                  height: 1,
                  color:
                      theme.colorScheme.outlineVariant.withValues(alpha: 0.22),
                ),
            ],
          );
        }).toList(),
      ),
    );
  }
}

class _BusinessActionRow extends StatefulWidget {
  const _BusinessActionRow({required this.option, required this.onTap});

  final _BusinessOption option;
  final VoidCallback onTap;

  @override
  State<_BusinessActionRow> createState() => _BusinessActionRowState();
}

class _BusinessActionRowState extends State<_BusinessActionRow> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: InkWell(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          transform: Matrix4.translationValues(_hovered ? 4 : 0, 0, 0),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
          color: _hovered
              ? theme.colorScheme.primary.withValues(alpha: 0.04)
              : Colors.transparent,
          child: Row(
            children: [
              SizedBox(
                width: 42,
                child: Text(
                  widget.option.index,
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: theme.colorScheme.primary.withValues(alpha: 0.78),
                  ),
                ),
              ),
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(14),
                ),
                child:
                    Icon(widget.option.icon, color: theme.colorScheme.primary),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(widget.option.titleKey.tr,
                        style: theme.textTheme.titleMedium),
                    const SizedBox(height: 5),
                    Text(widget.option.subtitleKey.tr,
                        style: theme.textTheme.bodyMedium),
                  ],
                ),
              ),
              Icon(Icons.arrow_outward_rounded,
                  color: theme.colorScheme.primary),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoPanel extends StatelessWidget {
  const _InfoPanel({
    required this.title,
    required this.description,
    required this.rows,
  });

  final String title;
  final String description;
  final List<_InfoRow> rows;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.72),
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
          for (final row in rows) ...[
            Row(
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
                    child: Text(row.value, style: theme.textTheme.bodyLarge)),
              ],
            ),
            if (row != rows.last) const SizedBox(height: 14),
          ],
        ],
      ),
    );
  }
}

class _InfoRow {
  const _InfoRow(this.label, this.value);

  final String label;
  final String value;
}

class _TipPanel extends StatelessWidget {
  const _TipPanel({
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
        color: theme.colorScheme.surface.withValues(alpha: 0.72),
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
                      child: Text(item.tr, style: theme.textTheme.bodyLarge)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
