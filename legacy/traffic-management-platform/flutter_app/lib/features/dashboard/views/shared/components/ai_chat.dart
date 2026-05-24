import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'package:final_assignment_front/features/dashboard/controllers/chat_controller.dart';
import 'package:final_assignment_front/features/model/agent_context_info.dart';
import 'package:final_assignment_front/features/model/chat_action.dart';

class AiChat extends StatefulWidget {
  const AiChat({super.key});

  @override
  State<AiChat> createState() => _AiChatState();
}

class _AiChatState extends State<AiChat> {
  final ScrollController _scrollController = ScrollController();
  late final ChatController _controller;
  late final List<Worker> _autoScrollWorkers;
  bool _autoScrollQueued = false;

  @override
  void initState() {
    super.initState();
    _controller = Get.find<ChatController>();
    _autoScrollWorkers = [
      ever<List<ChatMessage>>(
        _controller.messages,
        (_) => _scheduleAutoScroll(),
      ),
      ever<List<String>>(
        _controller.searchResults,
        (_) => _scheduleAutoScroll(),
      ),
      ever<AgentContextInfo?>(
        _controller.agentContext,
        (_) => _scheduleAutoScroll(),
      ),
      ever<bool>(_controller.isSending, (_) => _scheduleAutoScroll()),
    ];
  }

  @override
  void dispose() {
    for (final worker in _autoScrollWorkers) {
      worker.dispose();
    }
    _scrollController.dispose();
    super.dispose();
  }

  void _scheduleAutoScroll() {
    if (_autoScrollQueued) return;
    _autoScrollQueued = true;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _autoScrollQueued = false;
      if (!mounted || !_scrollController.hasClients) return;

      final position = _scrollController.position;
      final distanceToBottom = position.maxScrollExtent - position.pixels;
      if (position.pixels > 0 && distanceToBottom > 160) {
        return;
      }

      final target = position.maxScrollExtent;
      if ((target - position.pixels).abs() < 1) return;

      _scrollController.animateTo(
        target,
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final palette = _ChatPalette.of(context);

    return DecoratedBox(
      decoration: BoxDecoration(color: palette.background),
      child: SafeArea(
        child: Column(
          children: [
            _Header(controller: _controller, palette: palette),
            Expanded(
              child: Obx(() {
                if (_controller.messages.isEmpty) {
                  return _EmptyState(
                    palette: palette,
                    suggestions: _controller.suggestions,
                    onSuggestionTap: _controller.sendMessage,
                  );
                }

                return ListView(
                  controller: _scrollController,
                  padding: const EdgeInsets.fromLTRB(18, 10, 18, 18),
                  children: [
                    if (_controller.agentContext.value != null)
                      _ContextPanel(
                        palette: palette,
                        contextInfo: _controller.agentContext.value!,
                      ),
                    if (_controller.searchResults.isNotEmpty)
                      _SearchPanel(
                        palette: palette,
                        results: _controller.searchResults,
                      ),
                    ..._controller.messages.map(
                      (message) => _MessageBlock(
                        palette: palette,
                        message: message,
                        onActionTap: _controller.executeAction,
                      ),
                    ),
                  ],
                );
              }),
            ),
            _Composer(controller: _controller, palette: palette),
          ],
        ),
      ),
    );
  }
}

class _ContextPanel extends StatelessWidget {
  const _ContextPanel({
    required this.palette,
    required this.contextInfo,
  });

  final _ChatPalette palette;
  final AgentContextInfo contextInfo;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: contextInfo.privilegedOperator
            ? palette.highlightSurface
            : palette.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: contextInfo.privilegedOperator
              ? palette.highlightOutline
              : palette.outline,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'chat.contextTitle'.tr,
            style: TextStyle(
              color: palette.muted,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          _ContextLine(
            palette: palette,
            label: 'chat.context.operator'.tr,
            value: contextInfo.operatorLabel ?? 'common.unknown'.tr,
          ),
          const SizedBox(height: 8),
          _ContextLine(
            palette: palette,
            label: 'chat.context.scope'.tr,
            value: contextInfo.accessScopeLabel ?? 'common.unknown'.tr,
          ),
        ],
      ),
    );
  }
}

class _ContextLine extends StatelessWidget {
  const _ContextLine({
    required this.palette,
    required this.label,
    required this.value,
  });

  final _ChatPalette palette;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        children: [
          TextSpan(
            text: '$label: ',
            style: TextStyle(
              color: palette.muted,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          TextSpan(
            text: value,
            style: TextStyle(
              color: palette.text,
              fontSize: 13,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.controller,
    required this.palette,
  });

  final ChatController controller;
  final _ChatPalette palette;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 14),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: palette.outline)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: palette.accentSoft,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: palette.outline),
                ),
                child: Icon(
                  Icons.terminal_rounded,
                  size: 18,
                  color: palette.accent,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'app.name'.tr,
                      style: TextStyle(
                        color: palette.text,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'chat.subtitle'.tr,
                      style: TextStyle(
                        color: palette.muted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Obx(
                () => InkWell(
                  onTap: () => controller.toggleWebSearch(
                    !controller.webSearchEnabled.value,
                  ),
                  borderRadius: BorderRadius.circular(14),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: controller.webSearchEnabled.value
                          ? palette.accentSoft
                          : palette.surface,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: palette.outline),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          controller.webSearchEnabled.value
                              ? Icons.language
                              : Icons.language_outlined,
                          size: 14,
                          color: controller.webSearchEnabled.value
                              ? palette.accent
                              : palette.muted,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          controller.webSearchEnabled.value
                              ? 'chat.webOn'.tr
                              : 'chat.webOff'.tr,
                          style: TextStyle(
                            color: controller.webSearchEnabled.value
                                ? palette.text
                                : palette.muted,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Obx(
            () => Align(
              alignment: Alignment.centerLeft,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: controller.availableSkills.isEmpty
                    ? [
                        _TinyPill(
                          palette: palette,
                          label: 'chat.loadingSkills'.tr,
                          icon: Icons.sync_rounded,
                        ),
                      ]
                    : controller.availableSkills
                        .map(
                          (skill) => _TinyPill(
                            palette: palette,
                            label: skill.name,
                            tooltip: skill.description,
                            icon: Icons.hub_outlined,
                          ),
                        )
                        .toList(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TinyPill extends StatelessWidget {
  const _TinyPill({
    required this.palette,
    required this.label,
    required this.icon,
    this.tooltip,
  });

  final _ChatPalette palette;
  final String label;
  final IconData icon;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final child = Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: palette.outline),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: palette.muted),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: palette.muted,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );

    if (tooltip == null || tooltip!.isEmpty) return child;
    return Tooltip(message: tooltip, child: child);
  }
}

class _SearchPanel extends StatelessWidget {
  const _SearchPanel({
    required this.palette,
    required this.results,
  });

  final _ChatPalette palette;
  final List<String> results;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: palette.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'chat.webResults'.tr,
            style: TextStyle(
              color: palette.muted,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          ...results.take(4).map(
                (result) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '> $result',
                    style: TextStyle(
                      color: palette.text,
                      fontSize: 13,
                      height: 1.45,
                    ),
                  ),
                ),
              ),
        ],
      ),
    );
  }
}

class _MessageBlock extends StatelessWidget {
  const _MessageBlock({
    required this.palette,
    required this.message,
    required this.onActionTap,
  });

  final _ChatPalette palette;
  final ChatMessage message;
  final ValueChanged<ChatAction> onActionTap;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    final background = message.isStatus
        ? palette.surface
        : isUser
            ? palette.accentSoft
            : palette.surfaceRaised;

    final label = message.isStatus
        ? 'chat.status'
        : isUser
            ? 'chat.you'
            : 'chat.agent';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: palette.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.tr,
            style: TextStyle(
              color: palette.muted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            message.text,
            style: TextStyle(
              color: message.isStatus ? palette.muted : palette.text,
              fontSize: 14,
              height: 1.55,
            ),
          ),
          if (message.actions.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: message.actions
                  .map(
                    (action) => OutlinedButton.icon(
                      onPressed: () => onActionTap(action),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: palette.text,
                        side: BorderSide(color: palette.outline),
                        backgroundColor: palette.background,
                      ),
                      icon: const Icon(
                        Icons.subdirectory_arrow_right_rounded,
                        size: 16,
                      ),
                      label: Text(
                        action.label ?? action.target ?? 'chat.runAction'.tr,
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({
    required this.palette,
    required this.suggestions,
    required this.onSuggestionTap,
  });

  final _ChatPalette palette;
  final List<String> suggestions;
  final ValueChanged<String> onSuggestionTap;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: palette.surface,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: palette.outline),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'chat.emptyTitle'.tr,
                style: TextStyle(
                  color: palette.text,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'chat.emptyBody'.tr,
                style: TextStyle(
                  color: palette.muted,
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: suggestions
                    .map(
                      (item) => ActionChip(
                        onPressed: () => onSuggestionTap(item),
                        backgroundColor: palette.accentSoft,
                        side: BorderSide(color: palette.outline),
                        label: Text(
                          item,
                          style: TextStyle(color: palette.text),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.palette,
  });

  final ChatController controller;
  final _ChatPalette palette;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: BoxDecoration(
        color: palette.background,
        border: Border(top: BorderSide(color: palette.outline)),
      ),
      child: Column(
        children: [
          Container(
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: palette.outline),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: TextField(
                    controller: controller.textController,
                    minLines: 1,
                    maxLines: 4,
                    style: TextStyle(
                      color: palette.text,
                      fontSize: 14,
                    ),
                    onSubmitted: (_) => controller.sendMessage(),
                    decoration: InputDecoration(
                      hintText: 'chat.inputHint'.tr,
                      hintStyle: TextStyle(color: palette.muted),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
                    ),
                  ),
                ),
                Obx(
                  () => Padding(
                    padding: const EdgeInsets.only(right: 10, bottom: 10),
                    child: IconButton.filled(
                      onPressed: controller.isSending.value
                          ? null
                          : () => controller.sendMessage(),
                      style: IconButton.styleFrom(
                        backgroundColor: palette.accent,
                        foregroundColor: palette.background,
                      ),
                      icon: controller.isSending.value
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.arrow_upward_rounded),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'chat.footer'.tr,
              style: TextStyle(color: palette.muted, fontSize: 11),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatPalette {
  const _ChatPalette({
    required this.background,
    required this.surface,
    required this.surfaceRaised,
    required this.outline,
    required this.muted,
    required this.text,
    required this.accent,
    required this.accentSoft,
    required this.highlightSurface,
    required this.highlightOutline,
  });

  final Color background;
  final Color surface;
  final Color surfaceRaised;
  final Color outline;
  final Color muted;
  final Color text;
  final Color accent;
  final Color accentSoft;
  final Color highlightSurface;
  final Color highlightOutline;

  static _ChatPalette of(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    return _ChatPalette(
      background: isDark
          ? Color.alphaBlend(
              colorScheme.surfaceTint.withValues(alpha: 0.06),
              colorScheme.surface,
            )
          : colorScheme.surfaceContainerLowest,
      surface: isDark
          ? colorScheme.surfaceContainerHigh.withValues(alpha: 0.92)
          : colorScheme.surface,
      surfaceRaised: isDark
          ? colorScheme.surfaceContainerHighest.withValues(alpha: 0.96)
          : colorScheme.surfaceContainerLow,
      outline:
          colorScheme.outlineVariant.withValues(alpha: isDark ? 0.72 : 0.6),
      muted: colorScheme.onSurfaceVariant,
      text: colorScheme.onSurface,
      accent: colorScheme.primary,
      accentSoft: colorScheme.primaryContainer.withValues(
        alpha: isDark ? 0.42 : 0.82,
      ),
      highlightSurface: Color.alphaBlend(
        colorScheme.primary.withValues(alpha: isDark ? 0.14 : 0.08),
        isDark ? colorScheme.surfaceContainerHigh : colorScheme.surface,
      ),
      highlightOutline:
          colorScheme.primary.withValues(alpha: isDark ? 0.48 : 0.3),
    );
  }
}
