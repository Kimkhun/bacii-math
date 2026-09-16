/// Admin cost / observability models. Mirrors AdminCostSummary /
/// AdminUserCost / AdminUsageLog in web/src/lib/api.ts.

class CostToday {
  final int calls;
  final int totalTokens;
  final double costUsd;

  CostToday(
      {required this.calls, required this.totalTokens, required this.costUsd});

  factory CostToday.fromJson(Map<String, dynamic> json) => CostToday(
        calls: json['calls'] as int? ?? 0,
        totalTokens: json['total_tokens'] as int? ?? 0,
        costUsd: (json['cost_usd'] as num?)?.toDouble() ?? 0,
      );
}

class CostPeriod {
  final int calls;
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;
  final double costUsd;
  final double avgLatencyMs;

  CostPeriod({
    required this.calls,
    required this.promptTokens,
    required this.completionTokens,
    required this.totalTokens,
    required this.costUsd,
    required this.avgLatencyMs,
  });

  factory CostPeriod.fromJson(Map<String, dynamic> json) => CostPeriod(
        calls: json['calls'] as int? ?? 0,
        promptTokens: json['prompt_tokens'] as int? ?? 0,
        completionTokens: json['completion_tokens'] as int? ?? 0,
        totalTokens: json['total_tokens'] as int? ?? 0,
        costUsd: (json['cost_usd'] as num?)?.toDouble() ?? 0,
        avgLatencyMs: (json['avg_latency_ms'] as num?)?.toDouble() ?? 0,
      );
}

class CostByEndpoint {
  final String endpoint;
  final int calls;
  final int totalTokens;
  final double costUsd;

  CostByEndpoint({
    required this.endpoint,
    required this.calls,
    required this.totalTokens,
    required this.costUsd,
  });

  factory CostByEndpoint.fromJson(Map<String, dynamic> json) => CostByEndpoint(
        endpoint: json['endpoint'] as String? ?? '',
        calls: json['calls'] as int? ?? 0,
        totalTokens: json['total_tokens'] as int? ?? 0,
        costUsd: (json['cost_usd'] as num?)?.toDouble() ?? 0,
      );
}

class CostByModel {
  final String modelName;
  final int calls;
  final int totalTokens;
  final double costUsd;

  CostByModel({
    required this.modelName,
    required this.calls,
    required this.totalTokens,
    required this.costUsd,
  });

  factory CostByModel.fromJson(Map<String, dynamic> json) => CostByModel(
        modelName: json['model_name'] as String? ?? '',
        calls: json['calls'] as int? ?? 0,
        totalTokens: json['total_tokens'] as int? ?? 0,
        costUsd: (json['cost_usd'] as num?)?.toDouble() ?? 0,
      );
}

class AdminCostSummary {
  final int timeframeDays;
  final CostToday today;
  final CostPeriod period;
  final List<CostByEndpoint> byEndpoint;
  final List<CostByModel> byModel;

  AdminCostSummary({
    required this.timeframeDays,
    required this.today,
    required this.period,
    required this.byEndpoint,
    required this.byModel,
  });

  factory AdminCostSummary.fromJson(Map<String, dynamic> json) =>
      AdminCostSummary(
        timeframeDays: json['timeframe_days'] as int? ?? 30,
        today: CostToday.fromJson(
            (json['today'] as Map<String, dynamic>?) ?? const {}),
        period: CostPeriod.fromJson(
            (json['period'] as Map<String, dynamic>?) ?? const {}),
        byEndpoint: ((json['by_endpoint'] as List?) ?? [])
            .map((e) => CostByEndpoint.fromJson(e as Map<String, dynamic>))
            .toList(),
        byModel: ((json['by_model'] as List?) ?? [])
            .map((m) => CostByModel.fromJson(m as Map<String, dynamic>))
            .toList(),
      );
}

class AdminUserCost {
  final String userId;
  final String email;
  final int totalCalls;
  final int totalTokens;
  final double totalCostUsd;
  final String? lastActive;

  AdminUserCost({
    required this.userId,
    required this.email,
    required this.totalCalls,
    required this.totalTokens,
    required this.totalCostUsd,
    this.lastActive,
  });

  factory AdminUserCost.fromJson(Map<String, dynamic> json) => AdminUserCost(
        userId: json['user_id'] as String? ?? '',
        email: json['email'] as String? ?? '',
        totalCalls: json['total_calls'] as int? ?? 0,
        totalTokens: json['total_tokens'] as int? ?? 0,
        totalCostUsd: (json['total_cost_usd'] as num?)?.toDouble() ?? 0,
        lastActive: json['last_active'] as String?,
      );
}

class AdminUsageLog {
  final String id;
  final String? userId;
  final String email;
  final String endpoint;
  final String provider;
  final String modelName;
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;
  final double estimatedCostUsd;
  final int latencyMs;
  final bool success;
  final String? errorMessage;
  final String createdAt;

  AdminUsageLog({
    required this.id,
    this.userId,
    required this.email,
    required this.endpoint,
    required this.provider,
    required this.modelName,
    required this.promptTokens,
    required this.completionTokens,
    required this.totalTokens,
    required this.estimatedCostUsd,
    required this.latencyMs,
    required this.success,
    this.errorMessage,
    required this.createdAt,
  });

  factory AdminUsageLog.fromJson(Map<String, dynamic> json) => AdminUsageLog(
        id: json['id'] as String? ?? '',
        userId: json['user_id'] as String?,
        email: json['email'] as String? ?? '',
        endpoint: json['endpoint'] as String? ?? '',
        provider: json['provider'] as String? ?? '',
        modelName: json['model_name'] as String? ?? '',
        promptTokens: json['prompt_tokens'] as int? ?? 0,
        completionTokens: json['completion_tokens'] as int? ?? 0,
        totalTokens: json['total_tokens'] as int? ?? 0,
        estimatedCostUsd: (json['estimated_cost_usd'] as num?)?.toDouble() ?? 0,
        latencyMs: json['latency_ms'] as int? ?? 0,
        success: json['success'] as bool? ?? false,
        errorMessage: json['error_message'] as String?,
        createdAt: json['created_at'] as String? ?? '',
      );
}

class ModelSettings {
  final String textModel;
  final String visionModel;
  final String visionProvider;

  ModelSettings({
    required this.textModel,
    required this.visionModel,
    required this.visionProvider,
  });

  factory ModelSettings.fromJson(Map<String, dynamic> json) => ModelSettings(
        textModel: json['text_model'] as String? ?? '',
        visionModel: json['vision_model'] as String? ?? '',
        visionProvider: json['vision_provider'] as String? ?? 'gemini',
      );

  Map<String, dynamic> toJson() => {
        'text_model': textModel,
        'vision_model': visionModel,
        'vision_provider': visionProvider,
      };
}
