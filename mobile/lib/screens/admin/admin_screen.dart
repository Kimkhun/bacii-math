import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  final ApiClient _api = ApiClient();
  Map<String, dynamic>? _costSummary;
  bool _isLoading = true;
  String? _error;
  String? _successMessage;

  String _textModel = 'qwen2.5:3b';
  String _visionModel = 'qwen2.5vl:3b';
  String _visionProvider = 'gemini';

  @override
  void initState() {
    super.initState();
    _loadAdminData();
  }

  Future<void> _loadAdminData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final settings = await _api.getAdminModelSettings();
      final costs = await _api.getAdminCostSummary(days: 30);
      setState(() {
        _costSummary = costs;
        _textModel = settings['text_model'] ?? 'qwen2.5:3b';
        _visionModel = settings['vision_model'] ?? 'qwen2.5vl:3b';
        _visionProvider = settings['vision_provider'] ?? 'gemini';
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    setState(() {
      _successMessage = null;
      _error = null;
    });

    try {
      await _api.updateAdminModelSettings({
        'text_model': _textModel,
        'vision_model': _visionModel,
        'vision_provider': _visionProvider,
      });
      setState(() {
        _successMessage = 'Model settings updated successfully';
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Admin Console: AI & Cost Analytics',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
              ),
              const SizedBox(height: 16),

              if (_successMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.successGreenLight,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.successGreen),
                  ),
                  child: Text(_successMessage!, style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(height: 14),
              ],

              if (_error != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.errorRedLight,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.errorRed),
                  ),
                  child: Text(_error!, style: const TextStyle(color: AppTheme.errorRed)),
                ),
                const SizedBox(height: 14),
              ],

              // Model Settings Card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'AI & OCR Inference Engine',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        initialValue: _textModel,
                        decoration: const InputDecoration(labelText: 'Explanation & Hint Model'),
                        onChanged: (val) => _textModel = val,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        initialValue: _visionModel,
                        decoration: const InputDecoration(labelText: 'Vision Handwriting Model'),
                        onChanged: (val) => _visionModel = val,
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: _visionProvider,
                        decoration: const InputDecoration(labelText: 'Vision Provider'),
                        items: const [
                          DropdownMenuItem(value: 'gemini', child: Text('Google Gemini (Cloud)')),
                          DropdownMenuItem(value: 'ollama', child: Text('Ollama / Qwen (Local)')),
                        ],
                        onChanged: (val) {
                          if (val != null) setState(() => _visionProvider = val);
                        },
                      ),
                      const SizedBox(height: 18),
                      ElevatedButton.icon(
                        onPressed: _saveSettings,
                        icon: const Icon(Icons.save_outlined, size: 18),
                        label: const Text('Save Model Configuration'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Cost Analytics Card
              if (_costSummary != null) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Token & Cost Summary (Last 30 Days)',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Total API Calls', style: TextStyle(color: AppTheme.slate600, fontSize: 12)),
                                  const SizedBox(height: 4),
                                  Text(
                                    '${_costSummary!['period']?['calls'] ?? 0}',
                                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Total Tokens', style: TextStyle(color: AppTheme.slate600, fontSize: 12)),
                                  const SizedBox(height: 4),
                                  Text(
                                    '${_costSummary!['period']?['total_tokens'] ?? 0}',
                                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Estimated Cost', style: TextStyle(color: AppTheme.slate600, fontSize: 12)),
                                  const SizedBox(height: 4),
                                  Text(
                                    '\$${(_costSummary!['period']?['cost_usd'] ?? 0.0).toStringAsFixed(4)}',
                                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.successGreen),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
