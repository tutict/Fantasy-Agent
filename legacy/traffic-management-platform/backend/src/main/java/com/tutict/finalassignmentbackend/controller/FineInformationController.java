package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.FineRecordService;
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
@RequestMapping("/api/fines")
@Tag(name = "", description = " endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE"})
public class FineInformationController {

    private static final Logger LOG = Logger.getLogger(FineInformationController.class.getName());

    private final FineRecordService fineRecordService;
    private final CurrentUserTrafficSupportService currentUserTrafficSupportService;

    public FineInformationController(FineRecordService fineRecordService,
                                     CurrentUserTrafficSupportService currentUserTrafficSupportService) {
        this.fineRecordService = fineRecordService;
        this.currentUserTrafficSupportService = currentUserTrafficSupportService;
    }

    @GetMapping("/me")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE", "USER"})
    @Operation(summary = "List Current User Fines")
    public ResponseEntity<List<FineRecord>> listCurrentUserFines(@RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(currentUserTrafficSupportService.listCurrentUserFines(page, size));
        } catch (IllegalStateException ex) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List current user fines failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PostMapping
    @Operation(summary = "Create")
    public ResponseEntity<FineRecord> create(@RequestBody FineRecord request,
                                             @RequestHeader(value = "Idempotency-Key", required = false)
                                             String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            if (useKey) {
                if (fineRecordService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                fineRecordService.checkAndInsertIdempotency(idempotencyKey, request, "create");
            }
            FineRecord saved = fineRecordService.createFineRecord(request);
            if (useKey && saved.getFineId() != null) {
                fineRecordService.markHistorySuccess(idempotencyKey, saved.getFineId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                fineRecordService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Create fine failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/{fineId}")
    @Operation(summary = "Update")
    public ResponseEntity<FineRecord> update(@PathVariable Long fineId,
                                             @RequestBody FineRecord request,
                                             @RequestHeader(value = "Idempotency-Key", required = false)
                                             String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @DeleteMapping("/{fineId}")
    @Operation(summary = "Delete")
    public ResponseEntity<Void> delete(@PathVariable Long fineId) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/{fineId}")
    @Operation(summary = "Get")
    public ResponseEntity<FineRecord> get(@PathVariable Long fineId) {
        try {
            FineRecord record = fineRecordService.findById(fineId);
            return record == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(record);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get fine failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List")
    public ResponseEntity<List<FineRecord>> list(@RequestParam(defaultValue = "1") int page,
                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(fineRecordService.listFines(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List fines failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/offense/{offenseId}")
    @Operation(summary = "By Offense")
    public ResponseEntity<List<FineRecord>> byOffense(@PathVariable Long offenseId,
                                                      @RequestParam(defaultValue = "1") int page,
                                                      @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(fineRecordService.findByOffenseId(offenseId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List fines by offense failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/handler")
    @Operation(summary = "Search By Handler")
    public ResponseEntity<List<FineRecord>> searchByHandler(@RequestParam String handler,
                                                            @RequestParam(defaultValue = "prefix") String mode,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        try {
            List<FineRecord> result = "fuzzy".equalsIgnoreCase(mode)
                    ? fineRecordService.searchByHandlerFuzzy(handler, page, size)
                    : fineRecordService.searchByHandlerPrefix(handler, page, size);
            return ResponseEntity.ok(result);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search fine by handler failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/status")
    @Operation(summary = "Search By Payment Status")
    public ResponseEntity<List<FineRecord>> searchByPaymentStatus(@RequestParam String status,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(fineRecordService.searchByPaymentStatus(status, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search fine by status failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/date-range")
    @Operation(summary = "Search By Date Range")
    public ResponseEntity<List<FineRecord>> searchByDateRange(@RequestParam String startDate,
                                                              @RequestParam String endDate,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(fineRecordService.searchByFineDateRange(startDate, endDate, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search fine by date range failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
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
