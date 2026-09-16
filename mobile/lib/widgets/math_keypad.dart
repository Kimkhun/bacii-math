import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

class MathKeypad extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback? onSubmitted;

  const MathKeypad({
    super.key,
    required this.controller,
    this.onSubmitted,
  });

  void _insert(String text) {
    final selection = controller.selection;
    final current = controller.text;

    if (selection.isValid) {
      final newText = current.replaceRange(selection.start, selection.end, text);
      controller.value = TextEditingValue(
        text: newText,
        selection: TextSelection.collapsed(offset: selection.start + text.length),
      );
    } else {
      controller.text = current + text;
      controller.selection = TextSelection.collapsed(offset: controller.text.length);
    }
  }

  void _backspace() {
    final selection = controller.selection;
    final current = controller.text;

    if (selection.isValid && selection.start > 0) {
      if (selection.isCollapsed) {
        final newText = current.replaceRange(selection.start - 1, selection.start, '');
        controller.value = TextEditingValue(
          text: newText,
          selection: TextSelection.collapsed(offset: selection.start - 1),
        );
      } else {
        final newText = current.replaceRange(selection.start, selection.end, '');
        controller.value = TextEditingValue(
          text: newText,
          selection: TextSelection.collapsed(offset: selection.start),
        );
      }
    } else if (current.isNotEmpty) {
      controller.text = current.substring(0, current.length - 1);
      controller.selection = TextSelection.collapsed(offset: controller.text.length);
    }
  }

  @override
  Widget build(BuildContext context) {
    final keys = [
      ['x', 'y', 'z', 'i', 'e', r'\pi'],
      ['+', '-', r'\times', '/', '=', r'\pm'],
      ['^2', '^{}', r'\sqrt{}', r'\frac{}{}', '(', ')'],
      [r'\lim', r'\int', r'\infty', r'\theta', r'\le', r'\ge'],
    ];

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppTheme.slate100,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.slate200),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final row in keys) ...[
            Row(
              children: [
                for (final k in row) ...[
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(2.0),
                      child: InkWell(
                        onTap: () => _insert(k),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: AppTheme.slate300),
                          ),
                          child: Center(
                            child: Text(
                              k.replaceAll(r'\', ''),
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                fontFamily: 'monospace',
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _backspace,
                  icon: const Icon(Icons.backspace_outlined, size: 16),
                  label: const Text('Delete'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    backgroundColor: Colors.white,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: onSubmitted,
                  icon: const Icon(Icons.check_circle_outline, size: 16),
                  label: const Text('Done'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    backgroundColor: AppTheme.primaryNavy,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
