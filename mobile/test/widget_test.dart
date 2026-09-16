import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:bacii_mobile/main.dart';
import 'package:bacii_mobile/core/api/api_client.dart';
import 'package:bacii_mobile/core/auth/auth_provider.dart';
import 'package:bacii_mobile/core/i18n/language_provider.dart';

import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('BacIIMathApp renders correctly', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final apiClient = ApiClient();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => LanguageProvider()),
          ChangeNotifierProvider(create: (_) => AuthProvider(apiClient: apiClient)),
        ],
        child: const BacIIMathApp(),
      ),
    );

    expect(find.text('BAC II Math'), findsWidgets);
  });
}
