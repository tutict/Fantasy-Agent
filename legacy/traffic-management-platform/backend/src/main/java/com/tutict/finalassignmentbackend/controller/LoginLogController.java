package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.AuditLoginLog;
import com.tutict.finalassignmentbackend.service.AuditLoginLogService;
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
@RequestMapping("/api/logs/login")
@Tag(name = "", description = " endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN"})
public class LoginLogController {

    private static final Logger LOG = Logger.getLogger(LoginLogController.class.getName());

    private final AuditLoginLogService auditLoginLogService;

    public LoginLogController(AuditLoginLogService auditLoginLogService) {
        this.auditLoginLogService = auditLoginLogService;
    }

    @PostMapping
    @Operation(summary = "Create")
    public ResponseEntity<AuditLoginLog> create(@RequestBody AuditLoginLog request,
                                                @RequestHeader(value = "Idempotency-Key", required = false)
                                                String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @PutMapping("/{logId}")
    @Operation(summary = "Update")
    public ResponseEntity<AuditLoginLog> update(@PathVariable Long logId,
                                                @RequestBody AuditLoginLog request,
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
    public ResponseEntity<AuditLoginLog> get(@PathVariable Long logId) {
        try {
            AuditLoginLog log = auditLoginLogService.findById(logId);
            return log == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(log);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get login log failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List")
    public ResponseEntity<List<AuditLoginLog>> list(@RequestParam(defaultValue = "1") int page,
                                                    @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.listLogs(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List login logs failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/username")
    @Operation(summary = "Search By Username")
    public ResponseEntity<List<AuditLoginLog>> searchByUsername(@RequestParam String username,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByUsername(username, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by username failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/result")
    @Operation(summary = "Search By Result")
    public ResponseEntity<List<AuditLoginLog>> searchByResult(@RequestParam String result,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByLoginResult(result, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by result failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/time-range")
    @Operation(summary = "Search By Time Range")
    public ResponseEntity<List<AuditLoginLog>> searchByTimeRange(@RequestParam String startTime,
                                                                 @RequestParam String endTime,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByLoginTimeRange(startTime, endTime, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by time range failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/ip")
    @Operation(summary = "Search By Ip")
    public ResponseEntity<List<AuditLoginLog>> searchByIp(@RequestParam String ip,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByLoginIp(ip, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by IP failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/location")
    @Operation(summary = "Search By Location")
    public ResponseEntity<List<AuditLoginLog>> searchByLocation(@RequestParam String loginLocation,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByLoginLocation(loginLocation, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by location failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/device-type")
    @Operation(summary = "Search By Device Type")
    public ResponseEntity<List<AuditLoginLog>> searchByDeviceType(@RequestParam String deviceType,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByDeviceType(deviceType, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by device type failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/browser-type")
    @Operation(summary = "Search By Browser Type")
    public ResponseEntity<List<AuditLoginLog>> searchByBrowserType(@RequestParam String browserType,
                                                                   @RequestParam(defaultValue = "1") int page,
                                                                   @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByBrowserType(browserType, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by browser type failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/logout-time-range")
    @Operation(summary = "Search By Logout Time Range")
    public ResponseEntity<List<AuditLoginLog>> searchByLogoutTimeRange(@RequestParam String startTime,
                                                                       @RequestParam String endTime,
                                                                       @RequestParam(defaultValue = "1") int page,
                                                                       @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(auditLoginLogService.searchByLogoutTimeRange(startTime, endTime, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search login log by logout time range failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}
