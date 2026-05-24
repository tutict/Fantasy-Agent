package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysUserRole;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.SysRoleService;
import com.tutict.finalassignmentbackend.service.SysUserRoleService;
import com.tutict.finalassignmentbackend.service.SysUserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/users")
@Tag(name = "User Management", description = "User Management endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN"})
public class UserManagementController {

    private static final Logger LOG = Logger.getLogger(UserManagementController.class.getName());

    private final SysUserService sysUserService;
    private final SysRoleService sysRoleService;
    private final SysUserRoleService sysUserRoleService;
    private final CurrentUserTrafficSupportService currentUserTrafficSupportService;

    public UserManagementController(SysUserService sysUserService,
                                    SysRoleService sysRoleService,
                                    SysUserRoleService sysUserRoleService,
                                    CurrentUserTrafficSupportService currentUserTrafficSupportService) {
        this.sysUserService = sysUserService;
        this.sysRoleService = sysRoleService;
        this.sysUserRoleService = sysUserRoleService;
        this.currentUserTrafficSupportService = currentUserTrafficSupportService;
    }

    @GetMapping("/me")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE", "APPEAL_REVIEWER", "USER"})
    @Operation(summary = "Get Current User")
    public ResponseEntity<Map<String, Object>> getCurrentUser() {
        String username = currentUsername();
        if (username == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        SysUser user = sysUserService.findByUsername(username);
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(buildCurrentUserPayload(user));
    }

    @PutMapping("/me")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE", "APPEAL_REVIEWER", "USER"})
    @Operation(summary = "Update Current User")
    public ResponseEntity<Map<String, Object>> updateCurrentUser(@RequestBody SysUser request) {
        String username = currentUsername();
        if (username == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        try {
            SysUser updatedUser = currentUserTrafficSupportService.updateCurrentUserProfile(request);
            return ResponseEntity.ok(buildCurrentUserPayload(updatedUser));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Update current user profile failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/me/password")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE", "APPEAL_REVIEWER", "USER"})
    @Operation(summary = "Update Current User Password")
    public ResponseEntity<String> updateCurrentUserPassword(@RequestBody(required = false) Map<String, String> request,
                                                            @RequestHeader(value = "Idempotency-Key", required = false)
                                                            String idempotencyHeader,
                                                            @RequestParam(required = false) String idempotencyKey) {
        String username = currentUsername();
        if (username == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        try {
            SysUser user = sysUserService.findByUsername(username);
            if (user == null) {
                return ResponseEntity.notFound().build();
            }
            String currentPassword = normalizeBodyValue(request, "currentPassword");
            String newPassword = normalizeBodyValue(request, "newPassword");
            if (currentPassword == null || newPassword == null) {
                return ResponseEntity.badRequest().body("currentPassword and newPassword are required");
            }
            String effectiveIdempotencyKey = firstNonBlank(idempotencyHeader, idempotencyKey);
            if (effectiveIdempotencyKey != null) {
                String fingerprint = sysUserService.buildPasswordChangeFingerprint(currentPassword, newPassword);
                SysUserService.PasswordChangeIdempotencyStatus status =
                        sysUserService.beginPasswordChange(effectiveIdempotencyKey, user.getUserId(), fingerprint);
                if (status == SysUserService.PasswordChangeIdempotencyStatus.ALREADY_SUCCEEDED) {
                    return ResponseEntity.ok().build();
                }
                if (status == SysUserService.PasswordChangeIdempotencyStatus.ALREADY_PROCESSING) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                if (status == SysUserService.PasswordChangeIdempotencyStatus.CONFLICT) {
                    return ResponseEntity.status(HttpStatus.CONFLICT)
                            .body("Idempotency key is already associated with a different password change request");
                }
            }
            if (!sysUserService.verifyPassword(user, currentPassword)) {
                sysUserService.markPasswordChangeFailure(effectiveIdempotencyKey, "Current password is incorrect");
                return ResponseEntity.status(HttpStatus.FORBIDDEN)
                        .body("auth.error.currentPasswordIncorrect");
            }
            sysUserService.updatePassword(user, newPassword);
            sysUserService.markPasswordChangeSuccess(effectiveIdempotencyKey, user.getUserId());
            return ResponseEntity.ok().build();
        } catch (Exception ex) {
            sysUserService.markPasswordChangeFailure(firstNonBlank(idempotencyHeader, idempotencyKey), ex.getMessage());
            LOG.log(Level.WARNING, "Update current user password failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).body(ex.getMessage());
        }
    }

    @PostMapping
    @Operation(summary = "Create User")
    public ResponseEntity<SysUser> createUser(@RequestBody SysUser request,
                                              @RequestHeader(value = "Idempotency-Key", required = false)
                                              String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            if (useKey) {
                if (sysUserService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysUserService.checkAndInsertIdempotency(idempotencyKey, request, "create");
            }
            SysUser saved = sysUserService.createSysUser(request);
            if (useKey && saved.getUserId() != null) {
                sysUserService.markHistorySuccess(idempotencyKey, saved.getUserId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                sysUserService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Create user failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/{userId}")
    @Operation(summary = "Update User")
    public ResponseEntity<SysUser> updateUser(@PathVariable Long userId,
                                              @RequestBody SysUser request,
                                              @RequestHeader(value = "Idempotency-Key", required = false)
                                              String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            request.setUserId(userId);
            if (useKey) {
                if (sysUserService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysUserService.checkAndInsertIdempotency(idempotencyKey, request, "update");
            }
            SysUser updated = sysUserService.updateSysUser(request);
            if (useKey && updated.getUserId() != null) {
                sysUserService.markHistorySuccess(idempotencyKey, updated.getUserId());
            }
            return ResponseEntity.ok(updated);
        } catch (Exception ex) {
            if (useKey) {
                sysUserService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Update user failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @DeleteMapping("/{userId}")
    @Operation(summary = "Delete User")
    public ResponseEntity<Void> deleteUser(@PathVariable Long userId) {
        try {
            sysUserService.deleteSysUser(userId);
            return ResponseEntity.noContent().build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Delete user failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/{userId}")
    @Operation(summary = "Get User")
    public ResponseEntity<SysUser> getUser(@PathVariable Long userId) {
        try {
            SysUser user = sysUserService.findById(userId);
            return user == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(user);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get user failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List Users")
    public ResponseEntity<List<SysUser>> listUsers(@RequestParam(defaultValue = "1") int page,
                                                   @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(sysUserService.listUsers(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List users failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/username/{username}")
    @Operation(summary = "Get By Username")
    public ResponseEntity<SysUser> getByUsername(@PathVariable String username) {
        try {
            SysUser user = sysUserService.findByUsername(username);
            return user == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(user);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get user by username failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/username/prefix")
    @Operation(summary = "Search By Username Prefix")
    public ResponseEntity<List<SysUser>> searchByUsernamePrefix(@RequestParam String username,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByUsernamePrefix(username, page, size));
    }

    @GetMapping("/search/username/fuzzy")
    @Operation(summary = "Search By Username Fuzzy")
    public ResponseEntity<List<SysUser>> searchByUsernameFuzzy(@RequestParam String username,
                                                               @RequestParam(defaultValue = "1") int page,
                                                               @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByUsernameFuzzy(username, page, size));
    }

    @GetMapping("/search/real-name/prefix")
    @Operation(summary = "Search By Real Name Prefix")
    public ResponseEntity<List<SysUser>> searchByRealNamePrefix(@RequestParam String realName,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByRealNamePrefix(realName, page, size));
    }

    @GetMapping("/search/real-name/fuzzy")
    @Operation(summary = "Search By Real Name Fuzzy")
    public ResponseEntity<List<SysUser>> searchByRealNameFuzzy(@RequestParam String realName,
                                                               @RequestParam(defaultValue = "1") int page,
                                                               @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByRealNameFuzzy(realName, page, size));
    }

    @GetMapping("/search/id-card")
    @Operation(summary = "Search By Id Card")
    public ResponseEntity<List<SysUser>> searchByIdCard(@RequestParam String idCardNumber,
                                                        @RequestParam(defaultValue = "1") int page,
                                                        @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByIdCardNumber(idCardNumber, page, size));
    }

    @GetMapping("/search/contact")
    @Operation(summary = "Search By Contact")
    public ResponseEntity<List<SysUser>> searchByContact(@RequestParam String contactNumber,
                                                         @RequestParam(defaultValue = "1") int page,
                                                         @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByContactNumber(contactNumber, page, size));
    }

    @GetMapping("/search/email")
    @Operation(summary = "Search By Email")
    public ResponseEntity<List<SysUser>> searchByEmail(@RequestParam String email,
                                                       @RequestParam(defaultValue = "1") int page,
                                                       @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByEmail(email, page, size));
    }

    @GetMapping("/search/status")
    @Operation(summary = "List By Status")
    public ResponseEntity<List<SysUser>> listByStatus(@RequestParam String status,
                                                      @RequestParam(defaultValue = "1") int page,
                                                      @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(sysUserService.findByStatus(status, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List users by status failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/department")
    @Operation(summary = "List By Department")
    public ResponseEntity<List<SysUser>> listByDepartment(@RequestParam String department,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(sysUserService.findByDepartment(department, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List users by department failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/department/prefix")
    @Operation(summary = "Search By Department Prefix")
    public ResponseEntity<List<SysUser>> searchByDepartmentPrefix(@RequestParam String department,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByDepartmentPrefix(department, page, size));
    }

    @GetMapping("/search/employee-number")
    @Operation(summary = "Search By Employee Number")
    public ResponseEntity<List<SysUser>> searchByEmployeeNumber(@RequestParam String employeeNumber,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByEmployeeNumber(employeeNumber, page, size));
    }

    @GetMapping("/search/last-login-range")
    @Operation(summary = "Search By Last Login Range")
    public ResponseEntity<List<SysUser>> searchByLastLoginRange(@RequestParam String startTime,
                                                                @RequestParam String endTime,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserService.searchByLastLoginTimeRange(startTime, endTime, page, size));
    }

    @PostMapping("/{userId}/roles")
    @Operation(summary = "Add User Role")
    public ResponseEntity<SysUserRole> addUserRole(@PathVariable Long userId,
                                                   @RequestBody SysUserRole relation,
                                                   @RequestHeader(value = "Idempotency-Key", required = false)
                                                   String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            relation.setUserId(userId);
            if (useKey) {
                if (sysUserRoleService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysUserRoleService.checkAndInsertIdempotency(idempotencyKey, relation, "create");
            }
            SysUserRole saved = sysUserRoleService.createRelation(relation);
            if (useKey && saved.getId() != null) {
                sysUserRoleService.markHistorySuccess(idempotencyKey, saved.getId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                sysUserRoleService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Add user role failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @DeleteMapping("/roles/{relationId}")
    @Operation(summary = "Delete User Role")
    public ResponseEntity<Void> deleteUserRole(@PathVariable Long relationId) {
        try {
            sysUserRoleService.deleteRelation(relationId);
            return ResponseEntity.noContent().build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Delete user role failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/{userId}/roles")
    @Operation(summary = "List User Roles")
    public ResponseEntity<List<SysUserRole>> listUserRoles(@PathVariable Long userId,
                                                           @RequestParam(defaultValue = "1") int page,
                                                           @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(sysUserRoleService.findByUserId(userId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List user roles failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/role-bindings/{relationId}")
    @Operation(summary = "Update User Role")
    public ResponseEntity<SysUserRole> updateUserRole(@PathVariable Long relationId,
                                                      @RequestBody SysUserRole relation,
                                                      @RequestHeader(value = "Idempotency-Key", required = false)
                                                      String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/role-bindings/{relationId}")
    @Operation(summary = "Get User Role")
    public ResponseEntity<SysUserRole> getUserRole(@PathVariable Long relationId) {
        SysUserRole relation = sysUserRoleService.findById(relationId);
        return relation == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(relation);
    }

    @GetMapping("/role-bindings")
    @Operation(summary = "List Role Bindings")
    public ResponseEntity<List<SysUserRole>> listRoleBindings(@RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserRoleService.findAll(page, size));
    }

    @GetMapping("/role-bindings/by-role/{roleId}")
    @Operation(summary = "List Bindings By Role")
    public ResponseEntity<List<SysUserRole>> listBindingsByRole(@PathVariable Integer roleId,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserRoleService.findByRoleId(roleId, page, size));
    }

    @GetMapping("/role-bindings/search")
    @Operation(summary = "Search Bindings")
    public ResponseEntity<List<SysUserRole>> searchBindings(@RequestParam Long userId,
                                                            @RequestParam Integer roleId,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysUserRoleService.findByUserIdAndRoleId(userId, roleId, page, size));
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private String normalizeBodyValue(Map<String, String> request, String key) {
        if (request == null || key == null) {
            return null;
        }
        String value = request.get(key);
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private String firstNonBlank(String primary, String secondary) {
        if (primary != null && !primary.isBlank()) {
            return primary.trim();
        }
        if (secondary != null && !secondary.isBlank()) {
            return secondary.trim();
        }
        return null;
    }

    private String currentUsername() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            return null;
        }
        Object principal = authentication.getPrincipal();
        if (principal == null) {
            return null;
        }
        String username = principal.toString();
        return "anonymousUser".equalsIgnoreCase(username) ? null : username;
    }

    private Map<String, Object> buildCurrentUserPayload(SysUser user) {
        Map<String, Object> payload = new LinkedHashMap<>();
        List<String> roleCodes = new ArrayList<>();
        List<String> roleNames = new ArrayList<>();

        if (user.getUserId() != null) {
            List<SysUserRole> relations = sysUserRoleService.findByUserId(user.getUserId(), 1, 100);
            for (SysUserRole relation : relations) {
                if (relation == null || relation.getRoleId() == null) {
                    continue;
                }
                SysRole role = sysRoleService.findById(relation.getRoleId());
                if (role == null) {
                    continue;
                }
                if (role.getRoleCode() != null && !role.getRoleCode().isBlank()) {
                    roleCodes.add(role.getRoleCode().trim().toUpperCase(Locale.ROOT));
                }
                if (role.getRoleName() != null && !role.getRoleName().isBlank()) {
                    roleNames.add(role.getRoleName());
                }
            }
        }

        payload.put("userId", user.getUserId());
        payload.put("username", user.getUsername());
        payload.put("realName", user.getRealName());
        payload.put("email", user.getEmail());
        payload.put("contactNumber", user.getContactNumber());
        payload.put("department", user.getDepartment());
        payload.put("remarks", user.getRemarks());
        payload.put("status", user.getStatus());
        payload.put("roles", roleCodes.stream().distinct().toList());
        payload.put("roleCodes", roleCodes.stream().distinct().toList());
        payload.put("roleNames", roleNames.stream().distinct().toList());
        return payload;
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}
