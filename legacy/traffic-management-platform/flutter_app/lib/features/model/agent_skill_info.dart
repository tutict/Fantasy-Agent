class AgentSkillInfo {
  final String id;
  final String name;
  final String description;

  const AgentSkillInfo({
    required this.id,
    required this.name,
    required this.description,
  });

  factory AgentSkillInfo.fromJson(Map<String, dynamic> json) {
    return AgentSkillInfo(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
    );
  }
}
