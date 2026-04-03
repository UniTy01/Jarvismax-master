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

// ── Mission task types (shared with HomeScreen) ───────────────────────────────
// Same 16 business skill definitions — key, French label, icon code, hint
const List<Map<String, dynamic>> _kMissionTaskTypes = [
  {'key': 'libre',                  'label': 'Libre',               'icon': 0xe3c9, 'hint': 'Décrivez votre mission...'},
  {'key': 'market_research',        'label': 'Recherche marché',    'icon': 0xe8b6, 'hint': 'Ex : Analysez le marché des outils IA pour PME en France…'},
  {'key': 'competitor_analysis',    'label': 'Concurrents',         'icon': 0xe14f, 'hint': 'Ex : Analysez les concurrents de [votre produit/service]…'},
  {'key': 'positioning',            'label': 'Positionnement',      'icon': 0xe1e0, 'hint': 'Ex : Définissez le positionnement de [votre offre]…'},
  {'key': 'pricing_strategy',       'label': 'Stratégie prix',      'icon': 0xe263, 'hint': 'Ex : Proposez une grille tarifaire pour [votre produit]…'},
  {'key': 'growth_plan',            'label': 'Plan de croissance',  'icon': 0xe6de, 'hint': 'Ex : Créez un plan de croissance sur 6 mois pour [votre entreprise]…'},
  {'key': 'acquisition_strategy',   'label': 'Acquisition',         'icon': 0xe7fe, 'hint': 'Ex : Définissez une stratégie d\'acquisition pour [cible client]…'},
  {'key': 'value_proposition',      'label': 'Valeur client',       'icon': 0xe838, 'hint': 'Ex : Formulez la proposition de valeur de [votre offre]…'},
  {'key': 'offer_design',           'label': 'Design offre',        'icon': 0xe19c, 'hint': 'Ex : Concevez une offre commerciale pour [votre marché cible]…'},
  {'key': 'customer_persona',       'label': 'Persona client',      'icon': 0xe7fd, 'hint': 'Ex : Créez des personas clients pour [votre produit]…'},
  {'key': 'copywriting',            'label': 'Copywriting',         'icon': 0xe22b, 'hint': 'Ex : Rédigez un texte de vente percutant pour [votre offre]…'},
  {'key': 'funnel_design',          'label': 'Funnel',              'icon': 0xef4f, 'hint': 'Ex : Concevez un funnel de conversion pour [votre offre]…'},
  {'key': 'landing_structure',      'label': 'Landing page',        'icon': 0xe051, 'hint': 'Ex : Structurez une landing page pour [votre produit]…'},
  {'key': 'spec_writing',           'label': 'Rédaction spec',      'icon': 0xe873, 'hint': 'Ex : Rédigez les spécifications de [votre fonctionnalité]…'},
  {'key': 'automation_opportunity', 'label': 'Automatisation',      'icon': 0xe553, 'hint': 'Ex : Identifiez les opportunités d\'automatisation dans [votre activité]…'},
  {'key': 'strategy_reasoning',     'label': 'Conseil stratégique', 'icon': 0xe90f, 'hint': 'Ex : Donnez un conseil stratégique sur [ma situation actuelle]…'},
];

class _MissionScreenState extends State<MissionScreen> {
  final _controller = TextEditingController();
  final _focus       = FocusNode();
  bool      _sending      = false;
  Mission?  _lastMission;
  List<ActionModel> _missionActions = [];
  bool _loadingActions = false;
  String _selectedTaskKey = 'libre';

  Map<String, dynamic> get _currentTypeData =>
      _kMissionTaskTypes.firstWhere((t) => t['key'] == _selectedTaskKey,
          orElse: () => _kMissionTaskTypes.first);
  String get _currentHint => _currentTypeData['hint'] as String;

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
                          : _currentHint,
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

            const SectionLabel('Type de mission'),
            _MissionTypeBar(
              selected: _selectedTaskKey,
              onSelect: (key) => setState(() => _selectedTaskKey = key),
            ),
            const SizedBox(height: 8),

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

    // Prefix skill domain key so the backend can route to the right business skill
    final goal = (_selectedTaskKey != 'libre') ? '[$_selectedTaskKey] $input' : input;

    setState(() { _sending = true; _lastMission = null; _missionActions = []; });
    _focus.unfocus();

    final api    = context.read<ApiService>();
    final result = await api.submitMission(goal);
    if (!mounted) return;
    setState(() => _sending = false);

    if (result.ok && result.data != null) {
      final mission = result.data!;
      setState(() { _lastMission = mission; _loadingActions = true; _selectedTaskKey = 'libre'; });
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

// ── Mission Type Bar ──────────────────────────────────────────────────────────

class _MissionTypeBar extends StatelessWidget {
  final String selected;
  final ValueChanged<String> onSelect;

  const _MissionTypeBar({required this.selected, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: _kMissionTaskTypes.map((t) {
          final key    = t['key']   as String;
          final label  = t['label'] as String;
          final code   = t['icon']  as int;
          final isSel  = key == selected;

          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: GestureDetector(
              onTap: () => onSelect(key),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(
                  color: isSel
                      ? JvColors.cyan.withValues(alpha: 0.12)
                      : JvColors.card,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isSel ? JvColors.cyan : JvColors.border,
                    width: isSel ? 1.5 : 1,
                  ),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(
                    IconData(code, fontFamily: 'MaterialIcons'),
                    size: 13,
                    color: isSel ? JvColors.cyan : JvColors.textMut,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isSel ? FontWeight.w600 : FontWeight.w400,
                      color: isSel ? JvColors.cyan : JvColors.textSec,
                    ),
                  ),
                ]),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
