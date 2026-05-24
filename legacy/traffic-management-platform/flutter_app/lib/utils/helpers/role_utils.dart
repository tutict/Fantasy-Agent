List<String> normalizeRoleCodes(dynamic rawRoles) {
  Iterable<dynamic> values;
  if (rawRoles is String) {
    values = rawRoles.split(',');
  } else if (rawRoles is Iterable) {
    values = rawRoles;
  } else {
    values = const [];
  }

  return values
      .map((role) => role.toString().trim().toUpperCase())
      .where((role) => role.isNotEmpty)
      .map((role) => role.startsWith('ROLE_') ? role.substring(5) : role)
      .toSet()
      .toList();
}

bool hasAnyRole(dynamic rawRoles, Iterable<String> expectedRoles) {
  final normalizedRoles = normalizeRoleCodes(rawRoles).toSet();
  final normalizedExpected = expectedRoles.map((role) => role.toUpperCase());
  return normalizedExpected.any(normalizedRoles.contains);
}

bool hasManagementAccess(dynamic rawRoles) {
  return hasAnyRole(rawRoles, const [
    'SUPER_ADMIN',
    'ADMIN',
    'TRAFFIC_POLICE',
    'FINANCE',
    'APPEAL_REVIEWER',
  ]);
}

String resolveWorkspaceRole(dynamic rawRoles) {
  if (hasAnyRole(rawRoles, const ['SUPER_ADMIN', 'ADMIN'])) {
    return 'ADMIN';
  }
  if (hasManagementAccess(rawRoles)) {
    return 'MANAGER';
  }
  return 'USER';
}

String resolveStoredUserRole(dynamic rawRoles) {
  return resolveWorkspaceRole(rawRoles);
}
