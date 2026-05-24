package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.AuditOperationLog;
import com.tutict.finalassignmentbackend.service.AuditOperationLogService;
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
@RequestMapping("/api/logs/operation")
@Tag(name = "", description = " endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN"})
public class OperationLogController {

    private static final Logger LOG = Logger.getLogger(OperationLogController.class.getName());

    private final AuditOperationLogService auditOperationLogService;

    public OperationLogController(AuditOperationLogService auditOperationLogService) {
        this.auditOperationLogService = auditOperationLogService;
    }

    @PostMapping
    @Operation(summary = "Create")
    public ResponseEntity<AuditOperationLog> create(@RequestBody AuditOperationLog request,
                                                    @RequestHeader(value = "Idempotency-Key", required = false)
                                                    String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @PutMapping("/{logId}")
    @Operation(summary = "Update")
    public ResponseEntity<AuditOperationLog> update(@PathVariable Long logId,
                                                    @RequestBody AuditOperationLog request,
                                                    @RequestHeader(value = "Idempotency-Key", required = false)
                                                    String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @DeleteMapping("/{logId}")
    @Operation(summary = "Delete")
    public ResponseEntity<Void> delete(@PathVariable Long logId) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/{logId}")
    @Operation(summary = "Get")
    public ResponseEntity<AuditOperationLog> get(@PathVariable Long logId) {
        try {
            AuditOperationLog log = auditOperationLogService.findById(logId);
            return log == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(log);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get operation log failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List")
    public ResponseEntity<List<AuditOperationLog>> list(@RequestParam(defaultValue = "1") int page,
                                                        @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.listLogs(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List operation logs failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/module")
    @Operation(summary = "Search By Module")
    public ResponseEntity<List<AuditOperationLog>> searchByModule(@RequestParam String module,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.searchByModule(module, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by module failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/type")
    @Operation(summary = "Search By Type")
    public ResponseEntity<List<AuditOperationLog>> searchByType(@RequestParam String type,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.searchByOperationType(type, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by type failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/user/{userId}")
    @Operation(summary = "Search By User")
    public ResponseEntity<List<AuditOperationLog>> searchByUser(@PathVariable Long userId,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.findByUserId(userId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by user failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/time-range")
    @Operation(summary = "Search By Time Range")
    public ResponseEntity<List<AuditOperationLog>> searchByTimeRange(@RequestParam String startTime,
                                                                     @RequestParam String endTime,
                                                                     @RequestParam(defaultValue = "1") int page,
                                                                     @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.searchByOperationTimeRange(startTime, endTime, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by time range failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/username")
    @Operation(summary = "Search By Username")
    public ResponseEntity<List<AuditOperationLog>> searchByUsername(@RequestParam String username,
                                                                    @RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.searchByUsername(username, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by username failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/request-url")
    @Operation(summary = "Search By Request Url")
    public ResponseEntity<List<AuditOperationLog>> searchByRequestUrl(@RequestParam String requestUrl,
                                                                      @RequestParam(defaultValue = "1") int page,
                                                                      @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.searchByRequestUrl(requestUrl, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by request URL failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/request-method")
    @Operation(summary = "Search By Request Method")
    public ResponseEntity<List<AuditOperationLog>> searchByRequestMethod(@RequestParam String requestMethod,
                                                                         @RequestParam(defaultValue = "1") int page,
                                                                         @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.searchByRequestMethod(requestMethod, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by request method failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/result")
    @Operation(summary = "Search By Result")
    public ResponseEntity<List<AuditOperationLog>> searchByResult(@RequestParam String operationResult,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditOperationLogService.searchByOperationResult(operationResult, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search operation log by result failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}
