/// Port of formatLocalizedPrompt from web/src/lib/i18n.ts. Localizes a
/// generated problem statement into Khmer (or passes English through),
/// following the Khmer-vs-LaTeX segregation rule.

class LocalizedPrompt {
  final String prompt;
  final String? promptLatex;
  LocalizedPrompt(this.prompt, this.promptLatex);
}

String _complexLiteral(dynamic a, dynamic b) {
  if (a is! num || b is! num) return '';
  if (b == 0) return '$a';
  if (b == 1) return a == 0 ? 'i' : '$a + i';
  if (b == -1) return a == 0 ? '-i' : '$a - i';
  if (b > 0) return a == 0 ? '${b}i' : '$a + ${b}i';
  return a == 0 ? '${b}i' : '$a - ${b.abs()}i';
}

String _latexGiven(String? rawPromptLatex) {
  if (rawPromptLatex == null || rawPromptLatex.isEmpty) return '';
  final given = RegExp(r'\\text\{Given \}\s*z\s*=\s*([\s\S]+?)\\text\{')
      .firstMatch(rawPromptLatex);
  if (given != null) return given.group(1)!.trim();
  final root = RegExp(r'w\^\{[^}]*\}\s*=\s*([\s\S]+?)\.?\s*$')
      .firstMatch(rawPromptLatex);
  if (root != null) return root.group(1)!.trim();
  return '';
}

const Map<String, Map<String, String>> _complexOpKm = {
  'add': {'name': 'ផលបូក', 'expr': 'z_1 + z_2'},
  'subtract': {'name': 'ផលដក', 'expr': 'z_1 - z_2'},
  'multiply': {'name': 'ផលគុណ', 'expr': 'z_1 \\cdot z_2'},
  'divide': {'name': 'ផលចែក', 'expr': '\\dfrac{z_1}{z_2}'},
};

final RegExp _khmerRe = RegExp(r'[ក-៿]');

LocalizedPrompt formatLocalizedPrompt({
  required String topic,
  required String questionType,
  required Map<String, dynamic>? params,
  required String? rawPrompt,
  required String? rawPromptLatex,
  required String lang,
  String? zDisplay,
}) {
  if (lang == 'en' || params == null) {
    return LocalizedPrompt(rawPrompt ?? '', rawPromptLatex);
  }

  if (rawPrompt != null && _khmerRe.hasMatch(rawPrompt)) {
    return LocalizedPrompt(rawPrompt, rawPromptLatex);
  }

  switch (topic) {
    case 'complex':
      {
        final zExpr = _complexLiteral(params['a'], params['b']).isNotEmpty
            ? _complexLiteral(params['a'], params['b'])
            : (_latexGiven(rawPromptLatex).isNotEmpty
                ? _latexGiven(rawPromptLatex)
                : (zDisplay ?? '').trim());
        final mathZ = zExpr.isNotEmpty ? '\$z = $zExpr\$' : '\$z\$';
        final n = params['n'];
        switch (questionType) {
          case 'modulus':
            return LocalizedPrompt(
                'គណនាម៉ូឌុល \$|z|\$ នៃចំនួនកុំផ្លិច $mathZ ៖', null);
          case 'argument':
            return LocalizedPrompt(
                'រកអាគុយម៉ង់ \$\\arg(z)\$ គិតជារ៉ាដ្យង់ នៃចំនួនកុំផ្លិច $mathZ ៖',
                null);
          case 'conjugate':
            return LocalizedPrompt(
                'រកចំនួនកុំផ្លិចឆ្លាស់ \$\\bar{z}\$ នៃចំនួនកុំផ្លិច $mathZ ៖',
                null);
          case 'real_part':
            return LocalizedPrompt(
                'រកផ្នែកពិត \$\\operatorname{Re}(z)\$ នៃចំនួនកុំផ្លិច $mathZ ៖',
                null);
          case 'imaginary_part':
            return LocalizedPrompt(
                'រកផ្នែកនិម្មិត \$\\operatorname{Im}(z)\$ នៃចំនួនកុំផ្លិច $mathZ ៖',
                null);
          case 'complex_arithmetic':
            {
              final z1 = _complexLiteral(params['a1'], params['b1']);
              final z2 = _complexLiteral(params['a2'], params['b2']);
              final op = _complexOpKm[params['operation']?.toString()];
              if (z1.isNotEmpty && z2.isNotEmpty && op != null) {
                return LocalizedPrompt(
                    'គេឱ្យ \$z_1 = $z1\$ និង \$z_2 = $z2\$។ ចូររក${op['name']} \$${op['expr']}\$ ៖',
                    null);
              }
              break;
            }
          case 'complex_power':
          case 'de_moivre_power':
            {
              if (zExpr.isNotEmpty && n != null) {
                final via = questionType == 'de_moivre_power'
                    ? ' ដោយប្រើរូបមន្តដឺម័រ (De Moivre)'
                    : '';
                return LocalizedPrompt(
                    'គេឱ្យ $mathZ។ ចូរគណនា \$z^{$n}\$$via ៖', null);
              }
              break;
            }
          case 'nth_roots':
            {
              if (zExpr.isNotEmpty && n != null) {
                return LocalizedPrompt(
                    'ចូររកតម្លៃ \$w\$ មួយ ដែល \$w^{$n} = $zExpr\$ ៖', null);
              }
              break;
            }
        }
        return LocalizedPrompt(rawPrompt ?? '', rawPromptLatex);
      }
    case 'limit':
      {
        if (rawPromptLatex != null && rawPromptLatex.isNotEmpty) {
          final clean = rawPromptLatex
              .replaceFirst(RegExp(r'^\\text\{Find\s*\}\s*'), '')
              .replaceFirst(RegExp(r'^\\text\{Compute\s*\}\s*'), '');
          return LocalizedPrompt('គណនាលីមីត \$$clean\$ ៖', null);
        }
        return LocalizedPrompt('គណនាលីមីតខាងក្រោម ៖\n${rawPrompt ?? ''}', null);
      }
    case 'integral':
      {
        if (rawPromptLatex != null && rawPromptLatex.isNotEmpty) {
          final clean =
              rawPromptLatex.replaceFirst(RegExp(r'^\\text\{Compute\s*\}\s*'), '');
          final isIndef = questionType == 'indefinite_integral';
          final title = isIndef ? 'គណនាព្រីមីទីវ' : 'គណនាអាំងតេក្រាលកំណត់';
          return LocalizedPrompt('$title \$$clean\$ ៖', null);
        }
        return LocalizedPrompt(
            'គណនាអាំងតេក្រាលខាងក្រោម ៖\n${rawPrompt ?? ''}', null);
      }
    case 'derivatives':
      {
        final order = params['order'] == 2
            ? 'ដេរីវេទីពីរ \$y\'\'\$'
            : 'ដេរីវេ \$y\'\$';
        if (rawPromptLatex != null && rawPromptLatex.isNotEmpty) {
          final m = RegExp(r'y\s*=\s*(.+?)(?:\.|$)').firstMatch(rawPromptLatex);
          final expr = m != null ? m.group(1) ?? '' : '';
          if (expr.isNotEmpty) {
            return LocalizedPrompt(
                'គណនា$order នៃអនុគមន៍ \$y = $expr\$ ៖', null);
          }
        }
        return LocalizedPrompt('គណនា$order ៖\n${rawPrompt ?? ''}', null);
      }
    case 'continuity':
      {
        final point =
            params['point'] != null ? '\$x = ${params['point']}\$' : '';
        if (params['unknown'] != null) {
          return LocalizedPrompt(
              'រកតម្លៃប៉ារ៉ាម៉ែត្រ \$${params['unknown']}\$ ដើម្បីឱ្យអនុគមន៍ជាប់ត្រង់ចំណុច $point ៖\n${rawPrompt ?? ''}',
              null);
        }
        return LocalizedPrompt(
            'សិក្សាភាពជាប់នៃអនុគមន៍ត្រង់ចំណុច $point ៖\n${rawPrompt ?? ''}',
            null);
      }
    case 'differential_equations':
      return LocalizedPrompt(
          'ដោះស្រាយសមីការឌីផេរ៉ង់ស្យែលខាងក្រោម ៖\n${rawPrompt ?? ''}', null);
    case 'vectors_space':
      return LocalizedPrompt(
          'ក្នុងលំហប្រកបដោយតម្រុយអរតូណរម៉ាល់ គណនាប្រមាណវិធីវិចទ័រខាងក្រោម ៖\n${rawPrompt ?? ''}',
          null);
    case 'conics':
      return LocalizedPrompt(
          'គេឱ្យសមីការកោនិកខាងក្រោម។ ចូររកលក្ខណៈដែលបានសួរ ៖\n${rawPrompt ?? ''}',
          null);
    default:
      return LocalizedPrompt(rawPrompt ?? '', rawPromptLatex);
  }
}
