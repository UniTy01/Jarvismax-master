import 'package:flutter/material.dart';

// ── JarvisMax Color Palette ──────────────────────────────────────────────────
class JvColors {
  JvColors._();

  static const bg       = Color(0xFF0A0E1A);
  static const surface  = Color(0xFF121929);
  static const card     = Color(0xFF1A2438);
  static const border   = Color(0xFF1E3050);
  static const cyan     = Color(0xFF00E5FF);
  static const cyanDark = Color(0xFF0097A7);
  static const green    = Color(0xFF00E676);
  static const orange   = Color(0xFFFF9100);
  static const red      = Color(0xFFFF1744);
  static const textPrim = Color(0xFFE8F4FD);
  static const textSec  = Color(0xFF7A9BB5);
  static const textMut  = Color(0xFF3D5470);

  // Semantic aliases (for screens that reference these names)
  static const text    = textPrim;
  static const error   = red;
  static const success = green;
  static const warning = orange;
}

class AppTheme {
  AppTheme._();

  static ThemeData get darkTheme => ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: JvColors.bg,
    colorScheme: const ColorScheme.dark(
      primary:   JvColors.cyan,
      secondary: JvColors.cyanDark,
      surface:   JvColors.surface,
      error:     JvColors.red,
      onPrimary: JvColors.bg,
      onSurface: JvColors.textPrim,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: JvColors.surface,
      foregroundColor: JvColors.textPrim,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontFamily: 'monospace',
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: JvColors.cyan,
        letterSpacing: 1.2,
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: JvColors.surface,
      selectedItemColor: JvColors.cyan,
      unselectedItemColor: JvColors.textMut,
      selectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
      unselectedLabelStyle: TextStyle(fontSize: 11),
      elevation: 8,
    ),
    cardTheme: CardThemeData(
      color: JvColors.card,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: JvColors.border, width: 1),
      ),
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 0),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: JvColors.card,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: JvColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: JvColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: JvColors.cyan, width: 1.5),
      ),
      hintStyle: const TextStyle(color: JvColors.textMut),
      labelStyle: const TextStyle(color: JvColors.textSec),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: JvColors.cyan,
        foregroundColor: JvColors.bg,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: const TextStyle(
          fontWeight: FontWeight.w700,
          fontSize: 14,
          letterSpacing: 0.8,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: JvColors.cyan,
        side: const BorderSide(color: JvColors.cyan),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    textTheme: const TextTheme(
      headlineMedium: TextStyle(
        color: JvColors.textPrim, fontSize: 24, fontWeight: FontWeight.w700,
      ),
      titleLarge: TextStyle(
        color: JvColors.textPrim, fontSize: 18, fontWeight: FontWeight.w600,
      ),
      titleMedium: TextStyle(
        color: JvColors.textPrim, fontSize: 15, fontWeight: FontWeight.w500,
      ),
      bodyLarge: TextStyle(color: JvColors.textPrim, fontSize: 14),
      bodyMedium: TextStyle(color: JvColors.textSec, fontSize: 13),
      bodySmall: TextStyle(color: JvColors.textMut, fontSize: 11),
      labelLarge: TextStyle(
        color: JvColors.cyan, fontSize: 12, fontWeight: FontWeight.w700,
        letterSpacing: 1.0,
      ),
    ),
    dividerTheme: const DividerThemeData(
      color: JvColors.border,
      thickness: 1,
      space: 1,
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: JvColors.card,
      contentTextStyle: const TextStyle(color: JvColors.textPrim),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      behavior: SnackBarBehavior.floating,
    ),
    chipTheme: ChipThemeData(
      backgroundColor: JvColors.border,
      labelStyle: const TextStyle(color: JvColors.textPrim, fontSize: 11),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      side: BorderSide.none,
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: JvColors.cyan,
    ),
  );
}
