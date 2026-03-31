import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../services/session_manager.dart';
import '../theme/design_system.dart';

/// Login — premium, calm access gate.
/// Token login (jv-xxx) + admin credentials toggle.
/// Auto-restore via SessionManager.
class LoginScreen extends StatefulWidget {
  final VoidCallback onLoginSuccess;
  const LoginScreen({super.key, required this.onLoginSuccess});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _tokenCtrl = TextEditingController();
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;
  String _error = '';
  String _info = '';
  bool _showAdmin = false;
  bool _rememberMe = true;
  bool _autoLoginAttempted = false;

  @override
  void initState() {
    super.initState();
    _tryAutoLogin();
  }

  Future<void> _tryAutoLogin() async {
    if (_autoLoginAttempted) return;
    _autoLoginAttempted = true;

    final session = await SessionManager.instance.restoreSession();
    if (session == null) return;

    setState(() { _loading = true; _info = 'Restoring session…'; });

    final api = context.read<ApiService>();
    final ok = await api.loginWithToken(session.token);
    if (!mounted) return;

    if (ok) {
      widget.onLoginSuccess();
      return;
    }

    if (session.loginMode == 'admin' && session.rememberMe) {
      final password = await SessionManager.instance.getStoredPassword();
      if (password != null && session.username.isNotEmpty) {
        final reOk = await api.loginWithCredentials(session.username, password);
        if (!mounted) return;
        if (reOk) {
          final newToken = api.currentToken;
          if (newToken != null && newToken.isNotEmpty) {
            await SessionManager.instance.saveSession(
              token: newToken, loginMode: 'admin',
              username: session.username, password: password,
              role: session.role, rememberMe: true,
            );
          }
          widget.onLoginSuccess();
          return;
        }
      }
    }

    await SessionManager.instance.logout();
    setState(() {
      _loading = false; _info = '';
      _error = 'Session expired. Please sign in again.';
      if (session.loginMode == 'admin') {
        _showAdmin = true;
        _userCtrl.text = session.username;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: JDS.bgBase,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(32),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              // ── Brand ──
              Container(
                width: 56, height: 56,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  gradient: const LinearGradient(
                    colors: [JDS.blue, JDS.violet],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: const Center(child: Text('J', style: TextStyle(
                  fontSize: 24, fontWeight: FontWeight.w700, color: Colors.white,
                ))),
              ),
              const SizedBox(height: 20),
              const Text('Jarvis', style: TextStyle(
                fontSize: 28, fontWeight: FontWeight.w700,
                color: JDS.textPrimary, letterSpacing: -0.5,
              )),
              const SizedBox(height: 6),
              const Text('AI Operating System', style: TextStyle(
                fontSize: 12, fontWeight: FontWeight.w500,
                color: JDS.textMuted, letterSpacing: 1,
              )),
              const SizedBox(height: 8),
              const Text('Enter your access token to get started',
                  style: TextStyle(fontSize: 14, color: JDS.textSecondary)),
              const SizedBox(height: 32),

              // ── Restoring indicator ──
              if (_info.isNotEmpty) ...[
                Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  const SizedBox(width: 16, height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: JDS.blue)),
                  const SizedBox(width: 8),
                  Text(_info, style: const TextStyle(color: JDS.textSecondary, fontSize: 13)),
                ]),
                const SizedBox(height: 16),
              ],

              // ── Token input ──
              if (!_loading) ...[
                TextField(
                  controller: _tokenCtrl,
                  obscureText: true,
                  style: const TextStyle(color: JDS.textPrimary, fontSize: 16),
                  decoration: const InputDecoration(
                    hintText: 'Access token (jv-…)',
                    prefixIcon: Icon(Icons.key_rounded, color: JDS.textMuted),
                  ),
                  onSubmitted: (_) => _loginWithToken(),
                ),
                const SizedBox(height: 14),

                SizedBox(
                  width: double.infinity, height: 48,
                  child: ElevatedButton(
                    onPressed: _loginWithToken,
                    child: const Text('Sign in', style: TextStyle(fontSize: 15)),
                  ),
                ),
              ],

              // ── Error ──
              if (_error.isNotEmpty) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: JDS.redSoft,
                    borderRadius: BorderRadius.circular(JDS.radiusSm),
                    border: Border.all(color: JDS.red.withValues(alpha: 0.2)),
                  ),
                  child: Row(children: [
                    const Icon(Icons.error_outline_rounded, size: 16, color: JDS.red),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_error, style: const TextStyle(
                      color: JDS.red, fontSize: 13,
                    ))),
                  ]),
                ),
              ],

              // ── Remember me ──
              if (!_loading)
                Padding(
                  padding: const EdgeInsets.only(top: 14),
                  child: Row(children: [
                    SizedBox(
                      width: 20, height: 20,
                      child: Checkbox(
                        value: _rememberMe,
                        onChanged: (v) => setState(() => _rememberMe = v ?? true),
                        fillColor: WidgetStateProperty.resolveWith((s) =>
                            s.contains(WidgetState.selected) ? JDS.blue : JDS.bgOverlay),
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text('Remember me',
                        style: TextStyle(color: JDS.textSecondary, fontSize: 13)),
                  ]),
                ),

              // ── Admin toggle ──
              if (!_loading) ...[
                const SizedBox(height: 28),
                GestureDetector(
                  onTap: () => setState(() => _showAdmin = !_showAdmin),
                  child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Icon(_showAdmin ? Icons.expand_less : Icons.expand_more,
                        size: 16, color: JDS.textMuted),
                    const SizedBox(width: 4),
                    Text(_showAdmin ? 'Hide admin login' : 'Admin login',
                        style: const TextStyle(color: JDS.textMuted, fontSize: 13)),
                  ]),
                ),

                if (_showAdmin) ...[
                  const SizedBox(height: 16),
                  TextField(
                    controller: _userCtrl,
                    style: const TextStyle(color: JDS.textPrimary),
                    decoration: const InputDecoration(
                      hintText: 'Username',
                      prefixIcon: Icon(Icons.person_rounded, color: JDS.textMuted),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _passCtrl,
                    obscureText: true,
                    style: const TextStyle(color: JDS.textPrimary),
                    decoration: const InputDecoration(
                      hintText: 'Password',
                      prefixIcon: Icon(Icons.lock_rounded, color: JDS.textMuted),
                    ),
                    onSubmitted: (_) => _loginWithCredentials(),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity, height: 48,
                    child: OutlinedButton(
                      onPressed: _loginWithCredentials,
                      child: const Text('Admin sign in'),
                    ),
                  ),
                ],
              ],
            ]),
          ),
        ),
      ),
    );
  }

  Future<void> _loginWithToken() async {
    final token = _tokenCtrl.text.trim();
    if (token.isEmpty) {
      setState(() => _error = 'Please enter your access token.');
      return;
    }
    setState(() { _loading = true; _error = ''; });

    final api = context.read<ApiService>();
    final ok = await api.loginWithToken(token);
    if (!mounted) return;

    if (ok) {
      await SessionManager.instance.saveSession(
        token: token, loginMode: 'token',
        role: 'user', rememberMe: _rememberMe,
      );
      widget.onLoginSuccess();
    } else {
      setState(() {
        _loading = false;
        _error = 'Invalid access token. Please check and try again.';
      });
    }
  }

  Future<void> _loginWithCredentials() async {
    final username = _userCtrl.text.trim();
    final password = _passCtrl.text.trim();
    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = 'Please enter username and password.');
      return;
    }
    setState(() { _loading = true; _error = ''; });

    final api = context.read<ApiService>();
    final ok = await api.loginWithCredentials(username, password);
    if (!mounted) return;

    if (ok) {
      final newToken = api.currentToken;
      await SessionManager.instance.saveSession(
        token: newToken ?? '', loginMode: 'admin',
        username: username, password: password,
        role: 'admin', rememberMe: _rememberMe,
      );
      widget.onLoginSuccess();
    } else {
      setState(() {
        _loading = false;
        _error = 'Invalid credentials. Please try again.';
      });
    }
  }

  @override
  void dispose() {
    _tokenCtrl.dispose();
    _userCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }
}
