import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../services/uncensored_notifier.dart';
import '../services/websocket_service.dart';
import '../models/mission.dart';
import '../models/action_model.dart';
import '../theme/app_theme.dart';
import '../widgets/cyber_card.dart';
import '../widgets/status_badge.dart';

class MissionScreen extends StatefulWidget {
  const MissionScreen({super.key});

  @override
  State<MissionScreen> createState() => _MissionScreenState();
}

class _MissionScreenState extends State<MissionScreen> {
  final _controller = TextEditingController();
  final _focus       = FocusNode();
  bool      _sending      = false;
  Mission?  _lastMission;
  List<ActionModel> _missionActions = [];
  bool _loadingActions = false;

  static const _suggestions = [
    'Analyser les logs du système',
    'Créer un rapport de performance',
    'Vérifier l\'état des agents',
    'Optimiser la mémoire vault',
    'Planifier une revue de code',
    'Rechercher les erreurs récentes',
  ];

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final isUncensored = context.watch<UncensoredModeNotifier>().isUncensored;
    final sendColor    = isUncensored ? const Color(0xFFf43f5e) : JvColors.cyan;

    return Scaffold(
      appBar: AppBar(
        title: const Text('NOUVELLE MISSION'),
        actions: [
          Consumer<WebSocketService>(
            builder: (_, ws, __) {
              final state = ws.connectionState;
              final Color dotColor;
              final String label;
              switch (state) {
                case WsConnectionState.connected:
                  dotColor = JvColors.green;
                  label = 'WS';
                case WsConnectionState.connecting:
                case WsConnectionState.reconnecting:
                  dotColor = JvColors.orange;
                  label = 'WS…';
                case WsConnectionState.authExpired:
                  dotColor = JvColors.orange;
                  label = 'AUTH';
                case WsConnectionState.offline:
                  dotColor = JvColors.textMut;
                  label = 'OFF';
                case WsConnectionState.disconnected:
                  dotColor = JvColors.textMut;
                  label = 'WS';
              }
              return Padding(
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: dotColor,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 9,
                      color: dotColor,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
      body: GestureDetector(
        onTap: () => _focus.unfocus(),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Uncensored banner (visible seulement si actif)
            if (isUncensored)
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFf43f5e).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFf43f5e).withValues(alpha: 0.4)),
                ),
                child: const Row(children: [
                  Text('🔓', style: TextStyle(fontSize: 13)),
                  SizedBox(width: 8),
                  Text(
                    'Uncensored • Local only',
                    style: TextStyle(
                      color: Color(0xFFf43f5e),
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ]),
              ),

            Container(
              decoration: BoxDecoration(
                color: JvColors.card,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: isUncensored
                      ? const Color(0xFFf43f5e).withValues(alpha: 0.4)
                      : JvColors.border,
                ),
              ),
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('COMMANDE', style: TextStyle(
                    color: sendColor, fontSize: 10,
                    fontWeight: FontWeight.w700, letterSpacing: 1.5,
                  )),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _controller,
                    focusNode: _focus,
                    maxLines: 4,
                    minLines: 3,
                    style: const TextStyle(color: JvColors.textPrim, fontSize: 15, height: 1.5),
                    decoration: InputDecoration(
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      filled: false,
                      hintText: isUncensored
                          ? 'Mode uncensored — Jarvis sans filtres...'
                          : 'Décrivez votre mission...',
                      hintStyle: const TextStyle(color: JvColors.textMut, fontSize: 14),
                    ),
                  ),
                  const Divider(height: 20),
                  SizedBox(
                    width: double.infinity,
                    child: _sending
                        ? const Center(child: Padding(
                            padding: EdgeInsets.all(8),
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ))
                        : ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: sendColor,
                              foregroundColor: Colors.black,
                            ),
                            onPressed: _send,
                            icon: const Icon(Icons.send, size: 18),
                            label: const Text('ENVOYER LA MISSION'),
                          ),
                  ),
                ],
              ),
            ),

            const SectionLabel('Suggestions rapides'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _suggestions.map((s) => ActionChip(
                label: Text(s, style: const TextStyle(fontSize: 12)),
                onPressed: () => _controller.text = s,
                backgroundColor: JvColors.card,
                side: const BorderSide(color: JvColors.border),
                labelStyle: const TextStyle(color: JvColors.textSec),
              )).toList(),
            ),

            if (_lastMission != null) ...[
              const SectionLabel('Résultat'),
              _MissionResult(
                mission: _lastMission!,
                actions: _missionActions,
                loadingActions: _loadingActions,
              ),
            ],

            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Future<void> _send() async {
    final input = _controller.text.trim();
    if (input.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Entrez une commande')),
      );
      return;
    }
    setState(() { _sending = true; _lastMission = null; _missionActions = []; });
    _focus.unfocus();

    final api    = context.read<ApiService>();
    final result = await api.submitMission(input);
    if (!mounted) return;
    setState(() => _sending = false);

    if (result.ok && result.data != null) {
      final mission = result.data!;
      setState(() { _lastMission = mission; _loadingActions = true; });
      _controller.clear();

      // Attendre que l'executor traite la mission (poll léger)
      await Future.delayed(const Duration(seconds: 2));
      if (!mounted) return;

      await api.loadActions();
      if (!mounted) return;

      final missionActions = api.actions
          .where((a) => a.missionId == mission.id)
          .toList();

      setState(() { _missionActions = missionActions; _loadingActions = false; });

      final doneCount = missionActions.where((a) => a.isExecuted).length;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(doneCount > 0
            ? 'Mission exécutée — $doneCount action${doneCount > 1 ? "s" : ""} réalisée${doneCount > 1 ? "s" : ""}'
            : 'Mission soumise: ${mission.status}'),
        backgroundColor: JvColors.green.withValues(alpha: 0.9),
        duration: const Duration(seconds: 3),
      ));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(result.error ?? 'Erreur inconnue'),
        backgroundColor: JvColors.red.withValues(alpha: 0.9),
      ));
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focus.dispose();
    super.dispose();
  }
}

// ── Mission Result ────────────────────────────────────────────────────────────

class _MissionResult extends StatelessWidget {
  final Mission mission;
  final List<ActionModel> actions;
  final bool loadingActions;
  const _MissionResult({required this.mission, required this.actions, required this.loadingActions});

  @override
  Widget build(BuildContext context) {
    final m = mission;
    final decisionColor = switch (m.advisoryDecision) {
      'GO'                => JvColors.green,
      'IMPROVE'           => JvColors.orange,
      'NO-GO' || 'NO_GO' => JvColors.red,
      _                   => JvColors.textMut,
    };

    final executedCount = actions.where((a) => a.isExecuted).length;
    final pendingCount  = actions.where((a) => a.isPending || a.isApproved).length;

    return CyberCard(
      accentColor: decisionColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header badges
          Row(
            children: [
              StatusBadge.forStatus(m.status, fontSize: 11),
              const SizedBox(width: 8),
              _Badge(m.advisoryDecision, decisionColor),
              const Spacer(),
              Text('${m.advisoryScore.toStringAsFixed(1)}/10',
                style: const TextStyle(color: JvColors.cyan, fontWeight: FontWeight.w700, fontSize: 14)),
            ],
          ),

          if (m.planSummary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(m.planSummary, style: const TextStyle(color: JvColors.textSec, fontSize: 13)),
          ],

          if (m.planSteps.isNotEmpty) ...[
            const SizedBox(height: 10),
            const Text('ÉTAPES DU PLAN', style: TextStyle(
              color: JvColors.textMut, fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 1.2,
            )),
            const SizedBox(height: 6),
            ...m.planSteps.asMap().entries.map((e) {
              final i    = e.key + 1;
              final step = e.value;
              final task  = _s(step['task'] ?? step['description'] ?? step['name'] ?? 'Étape $i');
              final agent = _s(step['agent']);
              final risk  = _s(step['risk']);
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 20, height: 20,
                      decoration: BoxDecoration(
                        color: JvColors.cyan.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Center(child: Text('$i', style: const TextStyle(
                        color: JvColors.cyan, fontSize: 10, fontWeight: FontWeight.w800,
                      ))),
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(task, style: const TextStyle(color: JvColors.textPrim, fontSize: 12, fontWeight: FontWeight.w500)),
                        if (agent.isNotEmpty || risk.isNotEmpty)
                          Text(
                            [if (agent.isNotEmpty) agent, if (risk.isNotEmpty) risk].join(' · '),
                            style: const TextStyle(color: JvColors.textMut, fontSize: 10),
                          ),
                      ],
                    )),
                  ],
                ),
              );
            }),
          ],

          const SizedBox(height: 10),
          const Divider(height: 1),
          const SizedBox(height: 10),

          if (loadingActions)
            const Row(children: [
              SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: JvColors.cyan)),
              SizedBox(width: 8),
              Text('Jarvis exécute...', style: TextStyle(color: JvColors.cyan, fontSize: 12)),
            ])
          else if (executedCount > 0) ...[
            _Banner(Icons.bolt, JvColors.green,
              '$executedCount action${executedCount > 1 ? "s" : ""} exécutée${executedCount > 1 ? "s" : ""} automatiquement'),
            const SizedBox(height: 8),
            ...actions.take(3).map((a) => _ActionRow(a)),
          ] else if (pendingCount > 0)
            _Banner(Icons.pending_actions, JvColors.orange,
              '$pendingCount action${pendingCount > 1 ? "s" : ""} en attente — onglet Actions')
          else
            const _Banner(Icons.hourglass_empty, JvColors.textMut, 'Traitement en cours...'),
        ],
      ),
    );
  }

  static String _s(dynamic v) => v?.toString() ?? '';
}

class _Badge extends StatelessWidget {
  final String text;
  final Color color;
  const _Badge(this.text, this.color);
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(4),
      border: Border.all(color: color.withValues(alpha: 0.5)),
    ),
    child: Text(text, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700)),
  );
}

class _Banner extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String text;
  const _Banner(this.icon, this.color, this.text);
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(6),
      border: Border.all(color: color.withValues(alpha: 0.3)),
    ),
    child: Row(children: [
      Icon(icon, color: color, size: 15),
      const SizedBox(width: 8),
      Expanded(child: Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500))),
    ]),
  );
}

class _ActionRow extends StatelessWidget {
  final ActionModel a;
  const _ActionRow(this.a);
  @override
  Widget build(BuildContext context) {
    final color = a.isExecuted ? JvColors.green : a.isFailed ? JvColors.red : JvColors.textMut;
    final icon  = a.isExecuted ? Icons.check_circle_outline : a.isFailed ? Icons.error_outline : Icons.circle_outlined;
    final resultPreview = a.result.split('\n')
        .map((l) => l.trim())
        .firstWhere((l) => l.isNotEmpty && !l.startsWith('[') && !l.startsWith('Action') && !l.startsWith('Cible'), orElse: () => '');

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: color, size: 14),
        const SizedBox(width: 6),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(a.description, style: const TextStyle(color: JvColors.textPrim, fontSize: 12),
            maxLines: 1, overflow: TextOverflow.ellipsis),
          if (resultPreview.isNotEmpty)
            Text(resultPreview, style: const TextStyle(color: JvColors.textMut, fontSize: 10),
              maxLines: 1, overflow: TextOverflow.ellipsis),
        ])),
      ]),
    );
  }
}
