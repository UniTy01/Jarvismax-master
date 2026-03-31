/// JarvisMax — Settings Screen V2
/// Simple vs Advanced mode separation.
/// Advanced mode shows technical details hidden from default view.
library settings_screen_v2;

import 'package:flutter/material.dart';

class SettingsScreenV2 extends StatefulWidget {
  const SettingsScreenV2({super.key});
  @override
  State<SettingsScreenV2> createState() => _SettingsScreenV2State();
}

class _SettingsScreenV2State extends State<SettingsScreenV2> {
  bool _advancedMode = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          // Simple mode — always visible
          SwitchListTile(
            title: const Text('Advanced mode'),
            subtitle: const Text('Show technical details'),
            value: _advancedMode,
            onChanged: (v) => setState(() => _advancedMode = v),
          ),

          // Advanced-only section
          if (_advancedMode) ...[
            const Divider(),
            const ListTile(title: Text('Advanced settings')),
            ListTile(
              leading: const Icon(Icons.route),
              title: const Text('View model routing'),
              onTap: () {},
            ),
            ListTile(
              leading: const Icon(Icons.bar_chart),
              title: const Text('View metrics'),
              onTap: () {},
            ),
            ListTile(
              leading: const Icon(Icons.auto_fix_high),
              title: const Text('Self-improvement status'),
              onTap: () {},
            ),
            ListTile(
              leading: const Icon(Icons.memory),
              title: const Text('Memory overview'),
              onTap: () {},
            ),
          ],
        ],
      ),
    );
  }
}
