class AgentContextInfo {
  final String? operatorLabel;
  final String? accessScopeLabel;
  final bool authenticated;
  final bool privilegedOperator;

  const AgentContextInfo({
    this.operatorLabel,
    this.accessScopeLabel,
    this.authenticated = false,
    this.privilegedOperator = false,
  });

  factory AgentContextInfo.fromJson(Map<String, dynamic> json) {
    return AgentContextInfo(
      operatorLabel: json['operatorLabel'] as String?,
      accessScopeLabel: json['accessScopeLabel'] as String?,
      authenticated: json['authenticated'] == true,
      privilegedOperator: json['privilegedOperator'] == true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'operatorLabel': operatorLabel,
      'accessScopeLabel': accessScopeLabel,
      'authenticated': authenticated,
      'privilegedOperator': privilegedOperator,
    };
  }
}
