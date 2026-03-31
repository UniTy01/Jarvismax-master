import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Card avec bordure cyber optionnelle et accentuation gauche
class CyberCard extends StatelessWidget {
  final Widget child;
  final Color? accentColor;
  final EdgeInsets? padding;
  final VoidCallback? onTap;

  const CyberCard({
    super.key,
    required this.child,
    this.accentColor,
    this.padding,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 5),
        decoration: BoxDecoration(
          color: JvColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: JvColors.border),
          gradient: accentColor != null
              ? LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [
                    accentColor!.withValues(alpha:0.08),
                    JvColors.card,
                  ],
                )
              : null,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (accentColor != null)
              Container(
                width: 3,
                decoration: BoxDecoration(
                  color: accentColor,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(12),
                    bottomLeft: Radius.circular(12),
                  ),
                ),
              ),
            Expanded(
              child: Padding(
                padding: padding ?? const EdgeInsets.all(14),
                child: child,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Séparateur section avec label
class SectionLabel extends StatelessWidget {
  final String text;
  const SectionLabel(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 20, bottom: 8),
      child: Text(
        text.toUpperCase(),
        style: const TextStyle(
          color: JvColors.textMut,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: 2,
        ),
      ),
    );
  }
}

/// Score bar cyan
class ScoreBar extends StatelessWidget {
  final double score; // 0 → 10
  final double height;

  const ScoreBar(this.score, {super.key, this.height = 6});

  @override
  Widget build(BuildContext context) {
    final pct = (score / 10).clamp(0.0, 1.0);
    final color = score >= 7.5
        ? JvColors.green
        : score >= 4.0
            ? JvColors.orange
            : JvColors.red;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(height),
                child: LinearProgressIndicator(
                  value: pct,
                  backgroundColor: JvColors.border,
                  color: color,
                  minHeight: height,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '${score.toStringAsFixed(1)}/10',
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
