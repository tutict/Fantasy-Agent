package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.OffenseRecordService;
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
@RequestMapping("/api/offenses")
@Tag(name = "Offense Management", description = "Offense Management endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "APPEAL_REVIEWER"})
public class OffenseInformationController {

    private static final Logger LOG = Logger.getLogger(OffenseInformationController.class.getName());

    private final OffenseRecordService offenseRecordService;
    private final CurrentUserTrafficSupportService currentUserTrafficSupportService;

    public OffenseInformationController(OffenseRecordService offenseRecordService,
                                       CurrentUserTrafficSupportService currentUserTrafficSupportService) {
        this.offenseRecordService = offenseRecordService;
        this.currentUserTrafficSupportService = currentUserTrafficSupportService;
    }

    @GetMapping("/me")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "APPEAL_REVIEWER", "USER"})
    @Operation(summary = "List Current User Offenses")
    public ResponseEntity<List<OffenseRecord>> listCurrentUserOffenses(@RequestParam(defaultValue = "1") int page,
                                                                       @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(currentUserTrafficSupportService.listCurrentUserOffenses(page, size));
        } catch (IllegalStateException ex) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List current user offenses failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PostMapping
    @Operation(summary = "Create")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE"})
    public ResponseEntity<OffenseRecord> create(@RequestBody OffenseRecord request,
                                                @RequestHeader(value = "Idempotency-Key", required = false)
                                                String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            if (useKey) {
                if (offenseRecordService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                offenseRecordService.checkAndInsertIdempotency(idempotencyKey, request, "create");
            }
            OffenseRecord saved = offenseRecordService.createOffenseRecord(request);
            if (useKey && saved.getOffenseId() != null) {
                offenseRecordService.markHistorySuccess(idempotencyKey, saved.getOffenseId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                offenseRecordService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Create offense failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/{offenseId}")
    @Operation(summary = "Update")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE"})
    public ResponseEntity<OffenseRecord> update(@PathVariable Long offenseId,
                                                @RequestBody OffenseRecord request,
                                                @RequestHeader(value = "Idempotency-Key", required = false)
                                                String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            request.setOffenseId(offenseId);
            if (useKey) {
                if (offenseRecordService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                offenseRecordService.checkAndInsertIdempotency(idempotencyKey, request, "update");
            }
            OffenseRecord updated = offenseRecordService.updateOffenseRecord(request);
            if (useKey && updated.getOffenseId() != null) {
                offenseRecordService.markHistorySuccess(idempotencyKey, updated.getOffenseId());
            }
            return ResponseEntity.ok(updated);
        } catch (Exception ex) {
            if (useKey) {
                offenseRecordService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Update offense failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @DeleteMapping("/{offenseId}")
    @Operation(summary = "Delete")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE"})
    public ResponseEntity<Void> delete(@PathVariable Long offenseId) {
        try {
            offenseRecordService.deleteOffenseRecord(offenseId);
            return ResponseEntity.noContent().build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Delete offense failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/{offenseId}")
    @Operation(summary = "Get")
    public ResponseEntity<OffenseRecord> get(@PathVariable Long offenseId) {
        try {
            OffenseRecord record = offenseRecordService.findById(offenseId);
            return record == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(record);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get offense failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List")
    public ResponseEntity<List<OffenseRecord>> list(@RequestParam(defaultValue = "1") int page,
                                                    @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.listOffenses(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List offenses failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/driver/{driverId}")
    @Operation(summary = "By Driver")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "APPEAL_REVIEWER", "FINANCE"})
    public ResponseEntity<List<OffenseRecord>> byDriver(@PathVariable Long driverId,
                                                        @RequestParam(defaultValue = "1") int page,
                                                        @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.findByDriverId(driverId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List offenses by driver failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/vehicle/{vehicleId}")
    @Operation(summary = "By Vehicle")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "APPEAL_REVIEWER", "FINANCE"})
    public ResponseEntity<List<OffenseRecord>> byVehicle(@PathVariable Long vehicleId,
                                                         @RequestParam(defaultValue = "1") int page,
                                                         @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.findByVehicleId(vehicleId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List offenses by vehicle failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/code")
    @Operation(summary = "Search By Code")
    public ResponseEntity<List<OffenseRecord>> searchByCode(@RequestParam String offenseCode,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByOffenseCode(offenseCode, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by code failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/type")
    @Operation(summary = "Search By Type")
    public ResponseEntity<List<OffenseRecord>> searchByType(@RequestParam String offenseType,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByOffenseType(offenseType, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by type failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/status")
    @Operation(summary = "Search By Status")
    public ResponseEntity<List<OffenseRecord>> searchByStatus(@RequestParam(required = false) String status,
                                                              @RequestParam(required = false) String processStatus,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(
                    offenseRecordService.searchByProcessStatus(firstNonBlank(status, processStatus), page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by status failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/time-range")
    @Operation(summary = "Search By Time Range")
    public ResponseEntity<List<OffenseRecord>> searchByTimeRange(@RequestParam String startTime,
                                                                 @RequestParam String endTime,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByOffenseTimeRange(startTime, endTime, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by time range failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/number")
    @Operation(summary = "Search By Number")
    public ResponseEntity<List<OffenseRecord>> searchByNumber(@RequestParam String offenseNumber,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByOffenseNumber(offenseNumber, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by number failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/location")
    @Operation(summary = "Search By Location")
    public ResponseEntity<List<OffenseRecord>> searchByLocation(@RequestParam String offenseLocation,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByOffenseLocation(offenseLocation, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by location failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/province")
    @Operation(summary = "Search By Province")
    public ResponseEntity<List<OffenseRecord>> searchByProvince(@RequestParam String offenseProvince,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByOffenseProvince(offenseProvince, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by province failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/city")
    @Operation(summary = "Search By City")
    public ResponseEntity<List<OffenseRecord>> searchByCity(@RequestParam String offenseCity,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByOffenseCity(offenseCity, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by city failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/notification")
    @Operation(summary = "Search By Notification")
    public ResponseEntity<List<OffenseRecord>> searchByNotification(@RequestParam String notificationStatus,
                                                                    @RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByNotificationStatus(notificationStatus, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by notification status failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/agency")
    @Operation(summary = "Search By Agency")
    public ResponseEntity<List<OffenseRecord>> searchByAgency(@RequestParam String enforcementAgency,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByEnforcementAgency(enforcementAgency, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by enforcement agency failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/fine-range")
    @Operation(summary = "Search By Fine Range")
    public ResponseEntity<List<OffenseRecord>> searchByFineRange(@RequestParam double minAmount,
                                                                 @RequestParam double maxAmount,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByFineAmountRange(minAmount, maxAmount, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Search offense by fine amount range failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private String firstNonBlank(String... values) {
        if (values == null) {
            return null;
        }
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}
