import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../core/i18n/language_provider.dart';
import '../core/auth/auth_provider.dart';
import '../core/theme/app_theme.dart';

class AppScaffold extends StatelessWidget {
  final Widget child;
  final String currentRoute;

  const AppScaffold({
    super.key,
    required this.child,
    required this.currentRoute,
  });

  int _calculateSelectedIndex() {
    if (currentRoute.startsWith('/practice')) return 0;
    if (currentRoute.startsWith('/formulas')) return 1;
    if (currentRoute.startsWith('/exam')) return 2;
    if (currentRoute.startsWith('/stats')) return 3;
    if (currentRoute.startsWith('/profile')) return 4;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);
    final auth = Provider.of<AuthProvider>(context);
    final selectedIndex = _calculateSelectedIndex();
    final isHome = currentRoute == '/';

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: InkWell(
          onTap: () => context.go('/'),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: AppTheme.primaryNavy,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(Icons.calculate_rounded, color: Colors.white, size: 18),
              ),
              const SizedBox(width: 6),
              const Flexible(
                child: Text(
                  'BAC II Math',
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ],
          ),
        ),
        actions: [
          // Compact Language Switcher (Single Tap Switch)
          InkWell(
            onTap: () => lang.setLanguage(lang.isKhmer ? 'en' : 'km'),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(
                color: AppTheme.slate100,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.slate300),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    lang.isKhmer ? '🇰🇭 ខ្មែរ' : '🇬🇧 EN',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 2),
                  const Icon(Icons.swap_horiz_rounded, size: 14, color: AppTheme.slate600),
                ],
              ),
            ),
          ),
          const SizedBox(width: 8),

          // Auth Button / Profile
          if (auth.isAuthenticated) ...[
            PopupMenuButton<String>(
              icon: const CircleAvatar(
                radius: 14,
                backgroundColor: AppTheme.primaryIndigo,
                child: Icon(Icons.person, size: 16, color: Colors.white),
              ),
              onSelected: (val) async {
                if (val == 'profile') context.go('/profile');
                if (val == 'logout') {
                  await auth.logout();
                  if (context.mounted) context.go('/');
                }
              },
              itemBuilder: (ctx) => [
                PopupMenuItem(
                  enabled: false,
                  child: Text(auth.user?.email ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                const PopupMenuDivider(),
                PopupMenuItem(
                  value: 'profile',
                  child: Text(lang.t('nav_profile')),
                ),
                PopupMenuItem(
                  value: 'logout',
                  child: Text(lang.t('nav_logout'), style: const TextStyle(color: AppTheme.errorRed)),
                ),
              ],
            ),
          ] else ...[
            TextButton(
              onPressed: () => context.go('/login'),
              child: Text(lang.t('nav_login'), style: const TextStyle(fontWeight: FontWeight.w600)),
            ),
          ],
          const SizedBox(width: 8),
        ],
      ),

      // Navigation Drawer
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: const BoxDecoration(color: AppTheme.primaryNavy),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  const Icon(Icons.school_rounded, color: AppTheme.accentAmber, size: 40),
                  const SizedBox(height: 8),
                  const Text(
                    'BAC II Math Cambodia',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    auth.user?.email ?? 'National Examination Prep',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 12),
                  ),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.home_outlined),
              title: const Text('Home'),
              selected: currentRoute == '/',
              onTap: () {
                Navigator.pop(context);
                context.go('/');
              },
            ),
            ListTile(
              leading: const Icon(Icons.draw_outlined),
              title: Text(lang.t('nav_practice')),
              selected: currentRoute.startsWith('/practice'),
              onTap: () {
                Navigator.pop(context);
                context.go('/practice');
              },
            ),
            ListTile(
              leading: const Icon(Icons.menu_book_outlined),
              title: Text(lang.t('nav_formulas')),
              selected: currentRoute.startsWith('/formulas'),
              onTap: () {
                Navigator.pop(context);
                context.go('/formulas');
              },
            ),
            ListTile(
              leading: const Icon(Icons.assignment_turned_in_outlined),
              title: Text(lang.t('nav_exam')),
              selected: currentRoute.startsWith('/exam'),
              onTap: () {
                Navigator.pop(context);
                context.go('/exam');
              },
            ),
            ListTile(
              leading: const Icon(Icons.history_rounded),
              title: Text(lang.t('nav_history')),
              selected: currentRoute.startsWith('/history'),
              onTap: () {
                Navigator.pop(context);
                context.go('/history');
              },
            ),
            ListTile(
              leading: const Icon(Icons.bar_chart_rounded),
              title: Text(lang.t('nav_stats')),
              selected: currentRoute.startsWith('/stats'),
              onTap: () {
                Navigator.pop(context);
                context.go('/stats');
              },
            ),
            ListTile(
              leading: const Icon(Icons.person_outline_rounded),
              title: Text(lang.t('nav_profile')),
              selected: currentRoute.startsWith('/profile'),
              onTap: () {
                Navigator.pop(context);
                context.go('/profile');
              },
            ),
            ListTile(
              leading: const Icon(Icons.bookmark_outline_rounded),
              title: Text(lang.t('saved_shelf_title')),
              selected: currentRoute.startsWith('/saved'),
              onTap: () {
                Navigator.pop(context);
                context.go('/saved');
              },
            ),
            if (auth.user?.isAdmin == true) ...[
              const Divider(),
              ListTile(
                leading: const Icon(Icons.admin_panel_settings_outlined, color: AppTheme.accentAmberDark),
                title: Text(lang.t('nav_admin')),
                selected: currentRoute.startsWith('/admin'),
                onTap: () {
                  Navigator.pop(context);
                  context.go('/admin');
                },
              ),
            ],
          ],
        ),
      ),

      body: SafeArea(child: child),

      // Bottom navigation bar for mobile navigation
      bottomNavigationBar: isHome
          ? null
          : BottomNavigationBar(
              currentIndex: selectedIndex,
              onTap: (index) {
                switch (index) {
                  case 0:
                    context.go('/practice');
                    break;
                  case 1:
                    context.go('/formulas');
                    break;
                  case 2:
                    context.go('/exam');
                    break;
                  case 3:
                    context.go('/stats');
                    break;
                  case 4:
                    context.go('/profile');
                    break;
                }
              },
              type: BottomNavigationBarType.fixed,
              selectedItemColor: AppTheme.primaryNavy,
              unselectedItemColor: AppTheme.slate600,
              items: [
                BottomNavigationBarItem(
                  icon: const Icon(Icons.draw_outlined),
                  activeIcon: const Icon(Icons.draw_rounded),
                  label: lang.t('nav_practice'),
                ),
                BottomNavigationBarItem(
                  icon: const Icon(Icons.menu_book_outlined),
                  activeIcon: const Icon(Icons.menu_book_rounded),
                  label: lang.t('nav_formulas'),
                ),
                BottomNavigationBarItem(
                  icon: const Icon(Icons.assignment_outlined),
                  activeIcon: const Icon(Icons.assignment_rounded),
                  label: lang.t('nav_exam'),
                ),
                BottomNavigationBarItem(
                  icon: const Icon(Icons.bar_chart_outlined),
                  activeIcon: const Icon(Icons.bar_chart_rounded),
                  label: lang.t('nav_stats'),
                ),
                BottomNavigationBarItem(
                  icon: const Icon(Icons.person_outline),
                  activeIcon: const Icon(Icons.person),
                  label: lang.t('nav_profile'),
                ),
              ],
            ),
    );
  }
}
