/// JarvisMax — Main V2
/// 4-tab navigation: Home, Approvals, History, Settings
library main_v2;

import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/approvals_screen.dart';
import 'screens/history_screen_v2.dart';
import 'screens/settings_screen_v2.dart';
import 'theme/app_theme_v2.dart';

void main() => runApp(const JarvisMaxApp());

class JarvisMaxApp extends StatelessWidget {
  const JarvisMaxApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Jarvis',
      theme: AppThemeV2.theme,
      home: const MainShell(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});
  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  // 4 screens — one per tab
  final List<Widget> _screens = [
    HomeScreen(),
    ApprovalsScreen(),
    HistoryScreenV2(),
    SettingsScreenV2(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        backgroundColor: const Color(0xFF101114),
        selectedItemColor: const Color(0xFF4F8CFF),
        unselectedItemColor: const Color(0xFF9E9EAE),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_outlined),      label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.check_circle_outline), label: 'Approvals'),
          BottomNavigationBarItem(icon: Icon(Icons.history),             label: 'History'),
          BottomNavigationBarItem(icon: Icon(Icons.settings_outlined),   label: 'Settings'),
        ],
      ),
    );
  }
}
