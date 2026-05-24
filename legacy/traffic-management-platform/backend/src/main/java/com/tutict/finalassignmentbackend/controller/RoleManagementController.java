package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysRolePermission;
import com.tutict.finalassignmentbackend.service.SysRolePermissionService;
import com.tutict.finalassignmentbackend.service.SysRoleService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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

import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/roles")
@Tag(name = "Role Management", description = "Role Management endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN"})
public class RoleManagementController {

    private static final Logger LOG = Logger.getLogger(RoleManagementController.class.getName());

    private final SysRoleService sysRoleService;
    private final SysRolePermissionService sysRolePermissionService;

    public RoleManagementController(SysRoleService sysRoleService,
                                    SysRolePermissionService sysRolePermissionService) {
        this.sysRoleService = sysRoleService;
        this.sysRolePermissionService = sysRolePermissionService;
    }

    @PostMapping
    @Operation(summary = "Create Role")
    public ResponseEntity<SysRole> createRole(@RequestBody SysRole request,
                                              @RequestHeader(value = "Idempotency-Key", required = false)
                                              String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            if (useKey) {
                if (sysRoleService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysRoleService.checkAndInsertIdempotency(idempotencyKey, request, "create");
            }
            SysRole saved = sysRoleService.createSysRole(request);
            if (useKey && saved.getRoleId() != null) {
                sysRoleService.markHistorySuccess(idempotencyKey, saved.getRoleId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                sysRoleService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Create role failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/{roleId}")
    @Operation(summary = "Update Role")
    public ResponseEntity<SysRole> updateRole(@PathVariable Integer roleId,
                                              @RequestBody SysRole request,
                                              @RequestHeader(value = "Idempotency-Key", required = false)
                                              String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            request.setRoleId(roleId);
            if (useKey) {
                if (sysRoleService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysRoleService.checkAndInsertIdempotency(idempotencyKey, request, "update");
            }
            SysRole updated = sysRoleService.updateSysRole(request);
            if (useKey && updated.getRoleId() != null) {
                sysRoleService.markHistorySuccess(idempotencyKey, updated.getRoleId());
            }
            return ResponseEntity.ok(updated);
        } catch (Exception ex) {
            if (useKey) {
                sysRoleService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Update role failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @DeleteMapping("/{roleId}")
    @Operation(summary = "Delete Role")
    public ResponseEntity<Void> deleteRole(@PathVariable Integer roleId) {
        try {
            sysRoleService.deleteSysRole(roleId);
            return ResponseEntity.noContent().build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Delete role failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/{roleId}")
    @Operation(summary = "Get Role")
    public ResponseEntity<SysRole> getRole(@PathVariable Integer roleId) {
        try {
            SysRole role = sysRoleService.findById(roleId);
            return role == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(role);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get role failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List Roles")
    public ResponseEntity<List<SysRole>> listRoles(@RequestParam(defaultValue = "1") int page,
                                                   @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(sysRoleService.findAll(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List roles failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/by-code/{roleCode}")
    @Operation(summary = "Get By Code")
    public ResponseEntity<SysRole> getByCode(@PathVariable String roleCode) {
        try {
            SysRole role = sysRoleService.findByRoleCode(roleCode);
            return role == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(role);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get role by code failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/code/prefix")
    @Operation(summary = "Search By Code Prefix")
    public ResponseEntity<List<SysRole>> searchByCodePrefix(@RequestParam String roleCode,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysRoleService.searchByRoleCodePrefix(roleCode, page, size));
    }

    @GetMapping("/search/code/fuzzy")
    @Operation(summary = "Search By Code Fuzzy")
    public ResponseEntity<List<SysRole>> searchByCodeFuzzy(@RequestParam String roleCode,
                                                           @RequestParam(defaultValue = "1") int page,
                                                           @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysRoleService.searchByRoleCodeFuzzy(roleCode, page, size));
    }

    @GetMapping("/search/name/prefix")
    @Operation(summary = "Search By Name Prefix")
    public ResponseEntity<List<SysRole>> searchByNamePrefix(@RequestParam String roleName,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysRoleService.searchByRoleNamePrefix(roleName, page, size));
    }

    @GetMapping("/search/name/fuzzy")
    @Operation(summary = "Search By Name Fuzzy")
    public ResponseEntity<List<SysRole>> searchByNameFuzzy(@RequestParam String roleName,
                                                           @RequestParam(defaultValue = "1") int page,
                                                           @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysRoleService.searchByRoleNameFuzzy(roleName, page, size));
    }

    @GetMapping("/search/type")
    @Operation(summary = "Search By Role Type")
    public ResponseEntity<List<SysRole>> searchByRoleType(@RequestParam String roleType,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysRoleService.searchByRoleType(roleType, page, size));
    }

    @GetMapping("/search/data-scope")
    @Operation(summary = "Search By Data Scope")
    public ResponseEntity<List<SysRole>> searchByDataScope(@RequestParam String dataScope,
                                                           @RequestParam(defaultValue = "1") int page,
                                                           @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysRoleService.searchByDataScope(dataScope, page, size));
    }

    @GetMapping("/search/status")
    @Operation(summary = "Search By Status")
    public ResponseEntity<List<SysRole>> searchByStatus(@RequestParam String status,
                                                        @RequestParam(defaultValue = "1") int page,
                                                        @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(sysRoleService.searchByStatus(status, page, size));
    }

    @PostMapping("/{roleId}/permissions")
    @Operation(summary = "Add Permission")
    public ResponseEntity<SysRolePermission> addPermission(@PathVariable Integer roleId,
                                                           @RequestBody SysRolePermission relation,
                                                           @RequestHeader(value = "Idempotency-Key", required = false)
                                                           String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            relation.setRoleId(roleId);
            if (useKey) {
                if (sysRolePermissionService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysRolePermissionService.checkAndInsertIdempotency(idempotencyKey, relation, "create");
            }
            SysRolePermission saved = sysRolePermissionService.createRelation(relation);
            if (useKey && saved.getId() != null) {
                sysRolePermissionService.markHistorySuccess(idempotencyKey, saved.getId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                sysRolePermissionService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Add role permission failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @DeleteMapping("/permissions/{relationId}")
    @Operation(summary = "Delete Permission")
    public ResponseEntity<Void> deletePermission(@PathVariable Long relationId) {
        try {
            sysRolePermissionService.deleteRelation(relationId);
            return ResponseEntity.noContent().build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Delete role permission failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/{roleId}/permissions")
    @Operation(summary = "List Permissions")
    public ResponseEntity<List<SysRolePermission>> listPermissions(@PathVariable Integer roleId,
                                                                   @RequestParam(defaultValue = "1") int page,
                                                                   @RequestParam(defaultValue = "50") int size) {
        try {
            return ResponseEntity.ok(sysRolePermissionService.findByRoleId(roleId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List role permissions failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/permissions/{relationId}")
    @Operation(summary = "Update Permission")
    public ResponseEntity<SysRolePermission> updatePermission(@PathVariable Long relationId,
                                                              @RequestBody SysRolePermission relation,
                                                              @RequestHeader(value = "Idempotency-Key", required = false)
                                                              String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/permissions/{relationId}")
    @Operation(summary = "Get Permission Relation")
    public ResponseEntity<SysRolePermission> getPermissionRelation(@PathVariable Long relationId) {
        try {
            SysRolePermission relation = sysRolePermissionService.findById(relationId);
            return relation == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(relation);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get role permission failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/permissions")
    @Operation(summary = "List All Relations")
    public ResponseEntity<List<SysRolePermission>> listAllRelations(@RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "50") int size) {
        try {
            return ResponseEntity.ok(sysRolePermissionService.findAll(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List role permission relations failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/permissions/by-permission/{permissionId}")
    @Operation(summary = "List By Permission")
    public ResponseEntity<List<SysRolePermission>> listByPermission(@PathVariable Integer permissionId,
                                                                    @RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "50") int size) {
        try {
            return ResponseEntity.ok(sysRolePermissionService.findByPermissionId(permissionId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List role permissions by permissionId failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/permissions/search")
    @Operation(summary = "Search Role Permission Bindings")
    public ResponseEntity<List<SysRolePermission>> searchRolePermissionBindings(@RequestParam Integer roleId,
                                                                                @RequestParam Integer permissionId,
                                                                                @RequestParam(defaultValue = "1") int page,
                                                                                @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysRolePermissionService.findByRoleIdAndPermissionId(roleId, permissionId, page, size));
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}
