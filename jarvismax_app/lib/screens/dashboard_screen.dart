import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../services/uncensored_notifier.dart';
import '../models/mission.dart';
import '../models/action_model.dart';
import '../theme/app_theme.dart';
import '../widgets/cyber_card.dart';
import '../widgets/status_badge.dart';
import '../widgets/score_chart.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    // Initialisation déléguée à main.dart (autoLogin + checkHealth + refresh)
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('JARVIS MAX'),
        actions: [
          _UncensoredPill(),
          _OnlineIndicator(),
          IconButton(
            icon: const Icon(Icons.refresh, color: JvColors.cyan),
            onPressed: () => context.read<ApiService>().refresh(),
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined, color: JvColors.textSec),
            onPressed: () => _showSettings(context),
          ),
        ],
      ),
      body: Consumer<ApiService>(
        builder: (_, api, __) {
          // Spinner pendant le check initial — AVANT tout le reste (évite le flash "HORS LIGNE")
          if (api.isChecking) {
            return const Center(child: CircularProgressIndicator());
          }

          if (api.loading && api.missions.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }

          // Offline banner with retry when no data at all
          if (!api.status.isOnline && api.missions.isEmpty && api.actions.isEmpty) {
            return _OfflineState(onRetry: api.refresh);
          }

          return RefreshIndicator(
            color: JvColors.cyan,
            backgroundColor: JvColors.card,
            onRefresh: api.refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Offline warning banner (but still show cached data)
                if (!api.status.isOnline)
                  _OfflineBanner(onRetry: api.refresh),
                _StatusRow(api),
                const SectionLabel('Statistiques'),
                _StatsGrid(api),
                const SectionLabel('Score Advisory'),
                _ScoreSection(api),
                const SectionLabel('Missions récentes'),
                if (api.missions.isEmpty)
                  const _EmptyState('Aucune mission. Envoyez votre première commande.')
                else
                  ...api.missions.take(5).map((m) => _MissionTile(m)),
                const SectionLabel('Actions en attente'),
                if (api.pendingActions.isEmpty)
                  const _EmptyState('Aucune action en attente.')
                else
                  ...api.pendingActions.take(3).map((a) => _ActionTile(a)),
                const SizedBox(height: 40),
              ],
            ),
          );
        },
      ),
    );
  }

  void _showSettings(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: JvColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      isScrollControlled: true,
      builder: (_) => const _SettingsSheet(),
    );
  }
}

// ── Offline full-screen state ─────────────────────────────────────────────────

class _OfflineState extends StatelessWidget {
  final Future<void> Function() onRetry;
  const _OfflineState({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.wifi_off_rounded, color: JvColors.red, size: 56),
            const SizedBox(height: 16),
            const Text(
              'HORS LIGNE',
              style: TextStyle(
                color: JvColors.red,
                fontSize: 20,
                fontWeight: FontWeight.w800,
                letterSpacing: 2,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Impossible de joindre le serveur Jarvis.\nVérifiez l\'IP et que l\'API est démarrée.',
              textAlign: TextAlign.center,
              style: TextStyle(color: JvColors.textSec, fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('RÉESSAYER'),
            ),
          ],
        ),
      ),
    );
  }
}

class _OfflineBanner extends StatelessWidget {
  final Future<void> Function() onRetry;
  const _OfflineBanner({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: JvColors.red.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: JvColors.red.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.wifi_off_rounded, color: JvColors.red, size: 18),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              'HORS LIGNE — données en cache',
              style: TextStyle(color: JvColors.red, fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ),
          GestureDetector(
            onTap: onRetry,
            child: const Text(
              'Retry',
              style: TextStyle(color: JvColors.cyan, fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Uncensored pill ───────────────────────────────────────────────────────────

class _UncensoredPill extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final isOn = context.watch<UncensoredModeNotifier>().isUncensored;
    if (!isOn) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: const Color(0xFFf43f5e).withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFFf43f5e).withValues(alpha: 0.6)),
        ),
        child: const Text(
          '🔓 UNCENSORED',
          style: TextStyle(
            color: Color(0xFFf43f5e),
            fontSize: 10,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.8,
          ),
        ),
      ),
    );
  }
}

// ── Online indicator ──────────────────────────────────────────────────────────

class _OnlineIndicator extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final isOnline = context.watch<ApiService>().status.isOnline;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isOnline ? JvColors.green : JvColors.red,
              boxShadow: isOnline
                  ? [BoxShadow(color: JvColors.green.withValues(alpha: 0.6), blurRadius: 6)]
                  : null,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            isOnline ? 'EN LIGNE' : 'HORS LIGNE',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: isOnline ? JvColors.green : JvColors.red,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  final ApiService api;
  const _StatusRow(this.api);

  @override
  Widget build(BuildContext context) {
    final mode = api.status.mode;
    final modeColor = switch (mode) {
      'AUTO'       => JvColors.cyan,
      'SUPERVISED' => JvColors.orange,
      'MANUAL'     => JvColors.textSec,
      _            => JvColors.textMut,
    };
    return CyberCard(
      accentColor: modeColor,
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('MODE ACTUEL', style: TextStyle(
                fontSize: 9, color: JvColors.textMut,
                fontWeight: FontWeight.w700, letterSpacing: 1.5,
              )),
              const SizedBox(height: 4),
              Text(
                mode,
                style: TextStyle(
                  fontSize: 22, fontWeight: FontWeight.w800,
                  color: modeColor, letterSpacing: 1.5,
                ),
              ),
            ],
          ),
          const Spacer(),
          if (api.pendingActions.isNotEmpty)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: JvColors.orange.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: JvColors.orange.withValues(alpha: 0.4)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.pending_actions, color: JvColors.orange, size: 16),
                  const SizedBox(width: 6),
                  Text(
                    '${api.pendingActions.length} en attente',
                    style: const TextStyle(
                      color: JvColors.orange, fontSize: 12, fontWeight: FontWeight.w700,
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

class _StatsGrid extends StatelessWidget {
  final ApiService api;
  const _StatsGrid(this.api);

  @override
  Widget build(BuildContext context) {
    final s = api.status;
    final items = [
      ('Terminées',  s.doneMissions.toString(),     Icons.check_circle_outline,  JvColors.green),
      ('En cours',   s.approvedMissions.toString(),  Icons.rocket_launch_outlined, JvColors.cyan),
      ('Exécutées',  s.executedActions.toString(),   Icons.bolt_outlined,          JvColors.orange),
      ('Rejetées',   s.rejectedMissions.toString(),  Icons.cancel_outlined,        JvColors.red),
    ];

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 10,
      mainAxisSpacing: 10,
      childAspectRatio: 2.2,
      children: items.map((item) => _StatCard(
        label: item.$1,
        value: item.$2,
        icon: item.$3,
        color: item.$4,
      )).toList(),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color color;
  const _StatCard({required this.label, required this.value, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: JvColors.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: JvColors.border),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(value, style: TextStyle(
                color: color, fontSize: 20, fontWeight: FontWeight.w800,
              )),
              Text(label, style: const TextStyle(
                color: JvColors.textMut, fontSize: 10, fontWeight: FontWeight.w600,
              )),
            ],
          ),
        ],
      ),
    );
  }
}

class _MissionTile extends StatelessWidget {
  final Mission mission;
  const _MissionTile(this.mission);

  @override
  Widget build(BuildContext context) {
    return CyberCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  mission.userInput,
                  style: const TextStyle(
                    color: JvColors.textPrim, fontSize: 13, fontWeight: FontWeight.w500,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              StatusBadge.forStatus(mission.status),
            ],
          ),
          if (mission.planSummary.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              mission.planSummary,
              style: const TextStyle(color: JvColors.textMut, fontSize: 11),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  final ActionModel action;
  const _ActionTile(this.action);

  @override
  Widget build(BuildContext context) {
    return CyberCard(
      accentColor: JvColors.orange,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(action.description, style: const TextStyle(
                  color: JvColors.textPrim, fontSize: 12,
                ), maxLines: 2, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 4),
                StatusBadge.forRisk(action.risk),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Score Section ─────────────────────────────────────────────────────────────

class _ScoreSection extends StatelessWidget {
  final ApiService api;
  const _ScoreSection(this.api);

  @override
  Widget build(BuildContext context) {
    final allScores = api.missions
        .map((m) => m.advisoryScore)
        .toList();

    // 10 derniers scores pour le graphique
    final last10 = allScores.length > 10
        ? allScores.sublist(allScores.length - 10)
        : allScores;

    if (last10.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Text(
          'Aucune donnée de score disponible.',
          style: TextStyle(color: JvColors.textMut, fontSize: 12),
        ),
      );
    }

    // Moyenne des 10 derniers
    final avg10 = last10.reduce((a, b) => a + b) / last10.length;

    // Tendance : comparaison avec les 5 précédents si dispo
    String? trendLabel;
    Color trendColor = JvColors.textSec;
    if (allScores.length >= 6) {
      final prev5Start = (allScores.length - 10).clamp(0, allScores.length - 5);
      final prev5 = allScores.sublist(prev5Start, prev5Start + 5);
      final avg5 = prev5.reduce((a, b) => a + b) / prev5.length;
      final delta = avg10 - avg5;
      final arrow = delta >= 0 ? '↑' : '↓';
      trendColor = delta >= 0 ? JvColors.green : JvColors.red;
      trendLabel = '$arrow ${delta.abs().toStringAsFixed(1)} vs 5 précédentes';
    }

    return CyberCard(
      accentColor: JvColors.cyan,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Score moyen + tendance
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'SCORE MOYEN (10 dernières)',
                    style: TextStyle(
                      color: JvColors.textMut,
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    avg10.toStringAsFixed(1),
                    style: TextStyle(
                      color: avg10 >= 7.5
                          ? JvColors.green
                          : avg10 >= 4.0
                              ? JvColors.orange
                              : JvColors.red,
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              const SizedBox(width: 16),
              if (trendLabel != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    trendLabel,
                    style: TextStyle(
                      color: trendColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          // Graphique
          ScoreChart(scores: last10),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final String text;
  const _EmptyState(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Text(text, style: const TextStyle(color: JvColors.textMut, fontSize: 13)),
    );
  }
}

// ── Settings bottom sheet ─────────────────────────────────────────────────────

class _SettingsSheet extends StatefulWidget {
  const _SettingsSheet();

  @override
  State<_SettingsSheet> createState() => _SettingsSheetState();
}

class _SettingsSheetState extends State<_SettingsSheet> {
  late TextEditingController _hostCtrl;
  late TextEditingController _portCtrl;
  bool _saving = false;

  // IP Tailscale fixe (mise à jour au besoin)
  static const _tailscaleIp = '100.109.1.124';

  @override
  void initState() {
    super.initState();
    // Lire la vraie config persistée — jamais de valeur hardcodée ici
    final config = context.read<ApiConfig>();
    _hostCtrl = TextEditingController(text: config.host);
    _portCtrl = TextEditingController(text: config.port.toString());
  }

  Future<void> _save() async {
    final host = _hostCtrl.text.trim();
    final port = int.tryParse(_portCtrl.text.trim());
    if (host.isEmpty || port == null || port < 1 || port > 65535) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Host ou port invalide'),
          backgroundColor: JvColors.red,
        ),
      );
      return;
    }
    setState(() => _saving = true);
    // Appel réel à update() → SharedPreferences + notifyListeners
    await context.read<ApiConfig>().update(host: host, port: port);
    if (!mounted) return;
    setState(() => _saving = false);
    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Connecté à $host:$port'),
        backgroundColor: JvColors.cyanDark,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _applyProfile(String host, int port) {
    setState(() {
      _hostCtrl.text = host;
      _portCtrl.text = port.toString();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Titre
          const Text('CONFIGURATION API', style: TextStyle(
            color: JvColors.cyan, fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: 1.5,
          )),
          const SizedBox(height: 4),
          // URL actuelle
          Consumer<ApiConfig>(
            builder: (_, cfg, __) => Text(
              'Actuel : ${cfg.baseUrl}',
              style: const TextStyle(color: JvColors.textMut, fontSize: 11),
            ),
          ),
          const SizedBox(height: 16),
          // Champ Host
          TextField(
            controller: _hostCtrl,
            decoration: const InputDecoration(
              labelText: 'Host',
              hintText: '100.x.x.x (Tailscale) ou 192.168.x.x',
            ),
            style: const TextStyle(color: JvColors.textPrim),
            autocorrect: false,
            enableSuggestions: false,
          ),
          const SizedBox(height: 10),
          // Champ Port
          TextField(
            controller: _portCtrl,
            decoration: const InputDecoration(labelText: 'Port'),
            keyboardType: TextInputType.number,
            style: const TextStyle(color: JvColors.textPrim),
          ),
          const SizedBox(height: 20),
          // Boutons raccourcis
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                icon: const Icon(Icons.cloud_outlined, size: 14),
                label: const Text('VPS'),
                onPressed: () => _applyProfile('10.0.2.2', 8000),
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.wifi, size: 14),
                label: const Text('Local'),
                onPressed: () => _applyProfile('192.168.129.20', 8000),
              ),
              ElevatedButton.icon(
                icon: const Icon(Icons.vpn_lock, size: 14),
                label: const Text('Tailscale'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1a2a3a),
                  foregroundColor: JvColors.cyan,
                  side: const BorderSide(color: JvColors.cyan, width: 1),
                ),
                onPressed: () => _applyProfile(_tailscaleIp, 8000),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Bouton Sauvegarder
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _saving ? null : _save,
              style: ElevatedButton.styleFrom(
                backgroundColor: JvColors.cyan,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: _saving
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                    )
                  : const Text('SAUVEGARDER', style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: 1)),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _hostCtrl.dispose();
    _portCtrl.dispose();
    super.dispose();
  }
}
