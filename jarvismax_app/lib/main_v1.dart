/// JarvisMax V1 — preserved for rollback purposes.
/// This is the original main.dart before V2 redesign.
import 'package:flutter/material.dart';

// V1 entry point — do not modify, kept for reference
void main() => runApp(const JarvisAppV1());

class JarvisAppV1 extends StatelessWidget {
  const JarvisAppV1({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JarvisMax V1',
      home: const DashboardScreen(),
    );
  }
}

/// V1 Dashboard — 10-tab layout (deprecated in V2)
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('JarvisMax')),
      body: const Center(child: Text('V1 Dashboard')),
    );
  }
}
