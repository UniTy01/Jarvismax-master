/// JarvisMax App Theme V2
/// Warm neutral palette — calm blue accent, no neon cyan.
///
/// Palette:
///   Background:  #101114  (warm dark, not hacker blue)
///   Surface:     #1C1D22
///   Accent blue: #4F8CFF  (calm, warm neutral)
///   Success:     #4CAF50
///   Warning:     #FFB74D
///   Error:       #EF5350
library app_theme_v2;

import 'package:flutter/material.dart';

class AppThemeV2 {
  // Accent — calm blue
  static const Color accent     = Color(0xFF4F8CFF);

  // Backgrounds
  static const Color bgDark     = Color(0xFF101114);  // warm dark
  static const Color bgSurface  = Color(0xFF1C1D22);
  static const Color bgCard     = Color(0xFF26272E);

  // Text
  static const Color textPrimary   = Color(0xFFE8EAF6);
  static const Color textSecondary = Color(0xFF9E9EAE);
  static const Color textMuted     = Color(0xFF6B6B7A);

  // Status colors
  static const Color statusDone    = Color(0xFF4CAF50);
  static const Color statusError   = Color(0xFFEF5350);
  static const Color statusWaiting = Color(0xFFFFB74D);
  static const Color statusWorking = Color(0xFF4F8CFF);

  static ThemeData get theme => ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: bgDark,
    colorScheme: const ColorScheme.dark(
      primary: accent,
      surface: bgSurface,
      error: statusError,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: bgDark,
      elevation: 0,
      titleTextStyle: TextStyle(
        color: textPrimary,
        fontSize: 18,
        fontWeight: FontWeight.w600,
      ),
    ),
    cardTheme: const CardThemeData(
      color: bgCard,
      elevation: 0,
    ),
    textTheme: const TextTheme(
      bodyLarge:  TextStyle(color: textPrimary),
      bodyMedium: TextStyle(color: textSecondary),
      bodySmall:  TextStyle(color: textMuted),
    ),
  );
}
