import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../widgets/app_scaffold.dart';
import '../../screens/home/home_screen.dart';
import '../../screens/auth/login_screen.dart';
import '../../screens/auth/signup_screen.dart';
import '../../screens/practice/practice_screen.dart';
import '../../screens/formulas/formulas_screen.dart';
import '../../screens/profile/profile_screen.dart';
import '../../screens/stats/stats_screen.dart';
import '../../screens/history/history_screen.dart';
import '../../screens/exam/exam_screen.dart';
import '../../screens/admin/admin_screen.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<NavigatorState> _shellNavigatorKey = GlobalKey<NavigatorState>();

final GoRouter appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/',
  routes: [
    ShellRoute(
      navigatorKey: _shellNavigatorKey,
      builder: (context, state, child) {
        return AppScaffold(
          currentRoute: state.uri.path,
          child: child,
        );
      },
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => const HomeScreen(),
        ),
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(),
        ),
        GoRoute(
          path: '/signup',
          builder: (context, state) => const SignupScreen(),
        ),
        GoRoute(
          path: '/practice',
          builder: (context, state) {
            final qp = state.uri.queryParameters;
            return PracticeScreen(
              key: ValueKey(state.uri.toString()),
              initialTopic: qp['topic'],
              initialSkill: qp['skill'],
              initialFormula: qp['formula'],
              initialAttempt: qp['attempt'],
            );
          },
        ),
        GoRoute(
          path: '/formulas',
          builder: (context, state) => const FormulasScreen(),
        ),
        GoRoute(
          path: '/profile',
          builder: (context, state) => const ProfileScreen(),
        ),
        GoRoute(
          path: '/stats',
          builder: (context, state) => const StatsScreen(),
        ),
        GoRoute(
          path: '/history',
          builder: (context, state) => const HistoryScreen(),
        ),
        GoRoute(
          path: '/exam',
          builder: (context, state) => const ExamScreen(),
        ),
        GoRoute(
          path: '/admin',
          builder: (context, state) => const AdminScreen(),
        ),
      ],
    ),
  ],
);
