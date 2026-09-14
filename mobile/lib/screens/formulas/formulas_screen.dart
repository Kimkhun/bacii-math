import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/api/api_client.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/formula.dart';
import '../../widgets/math_text.dart';

class FormulasScreen extends StatefulWidget {
  const FormulasScreen({super.key});

  @override
  State<FormulasScreen> createState() => _FormulasScreenState();
}

class _FormulasScreenState extends State<FormulasScreen> {
  final ApiClient _api = ApiClient();
  FormulaCatalog? _catalog;
  bool _isLoading = true;
  String? _error;
  String? _selectedTopic;

  @override
  void initState() {
    super.initState();
    _fetchFormulas();
  }

  Future<void> _fetchFormulas() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await _api.getFormulas();
      setState(() {
        _catalog = res;
        _isLoading = false;
        if (res.topics.isNotEmpty) {
          _selectedTopic = res.topics.first.topic;
        }
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);

    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Failed to load formulas: $_error'),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _fetchFormulas, child: const Text('Retry')),
          ],
        ),
      );
    }

    final catalog = _catalog!;
    final currentTopic = catalog.topics.firstWhere(
      (t) => t.topic == _selectedTopic,
      orElse: () => catalog.topics.first,
    );

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Text(
                lang.t('formulas_title'),
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
              ),
              const SizedBox(height: 6),
              Text(
                lang.t('formulas_subtitle'),
                style: const TextStyle(fontSize: 14, color: AppTheme.slate600),
              ),
              const SizedBox(height: 20),

              // Topic Filter Pills
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: catalog.topics.map((t) {
                    final isSelected = t.topic == _selectedTopic;
                    final topicLabel = lang.t('topic_${t.topic}');
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(
                          topicLabel.isNotEmpty ? topicLabel : t.topic,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                            color: isSelected ? Colors.white : AppTheme.slate700,
                          ),
                        ),
                        selected: isSelected,
                        selectedColor: AppTheme.primaryNavy,
                        backgroundColor: Colors.white,
                        showCheckmark: false,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                        side: BorderSide(color: isSelected ? AppTheme.primaryNavy : AppTheme.slate300),
                        onSelected: (_) => setState(() => _selectedTopic = t.topic),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 20),

              // Formula Cards
              for (final entry in currentTopic.entries) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                lang.isKhmer ? entry.nameKm : (entry.nameEn ?? entry.nameKm),
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.primaryNavy),
                              ),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => context.go('/practice?topic=${currentTopic.topic}'),
                              icon: const Icon(Icons.fitness_center_rounded, size: 14),
                              label: Text(lang.t('formulas_practice'), style: const TextStyle(fontSize: 12)),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                visualDensity: VisualDensity.compact,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),

                        // Formula LaTeX display
                        if (entry.latex != null && entry.latex!.isNotEmpty) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppTheme.slate50,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppTheme.slate200),
                            ),
                            child: MathText(
                              text: '\$\$${entry.latex}\$\$',
                              textStyle: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
