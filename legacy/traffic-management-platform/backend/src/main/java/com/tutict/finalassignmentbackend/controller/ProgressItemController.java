package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.PaymentRecordService;
import com.tutict.finalassignmentbackend.service.SysRequestHistoryService;
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

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.function.IntFunction;
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/progress")
@Tag(name = "", description = " endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE", "APPEAL_REVIEWER"})
public class ProgressItemController {

    private static final Logger LOG = Logger.getLogger(ProgressItemController.class.getName());

    private final SysRequestHistoryService sysRequestHistoryService;
    private final CurrentUserTrafficSupportService currentUserTrafficSupportService;
    private final PaymentRecordService paymentRecordService;

    public ProgressItemController(SysRequestHistoryService sysRequestHistoryService,
                                  CurrentUserTrafficSupportService currentUserTrafficSupportService,
                                  PaymentRecordService paymentRecordService) {
        this.sysRequestHistoryService = sysRequestHistoryService;
        this.currentUserTrafficSupportService = currentUserTrafficSupportService;
        this.paymentRecordService = paymentRecordService;
    }

    @PostMapping
    @Operation(summary = "Create")
    public ResponseEntity<SysRequestHistory> create(@RequestBody SysRequestHistory request,
                                                    @RequestHeader(value = "Idempotency-Key", required = false)
                                                    String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @PutMapping("/{historyId}")
    @Operation(summary = "Update")
    public ResponseEntity<SysRequestHistory> update(@PathVariable Long historyId,
                                                    @RequestBody SysRequestHistory request,
                                                    @RequestHeader(value = "Idempotency-Key", required = false)
                                                    String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @DeleteMapping("/{historyId}")
    @Operation(summary = "Delete")
    public ResponseEntity<Void> delete(@PathVariable Long historyId) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/{historyId}")
    @Operation(summary = "Get")
    public ResponseEntity<SysRequestHistory> get(@PathVariable Long historyId) {
        try {
            SysRequestHistory history = sysRequestHistoryService.findById(historyId);
            return history == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(history);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get request history failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List")
    public ResponseEntity<List<SysRequestHistory>> list(@RequestParam(defaultValue = "1") int page,
                                                        @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(sysRequestHistoryService.findAll(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List request histories failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/me")
    @RolesAllowed({"USER"})
    @Operation(summary = "List Current User Progress")
    public ResponseEntity<List<SysRequestHistory>> listCurrentUserProgress(@RequestParam(defaultValue = "1") int page,
                                                                           @RequestParam(defaultValue = "20") int size,
                                                                           @RequestParam(required = false) Long appealId) {
        try {
            Long userId = currentUserTrafficSupportService.requireCurrentUser().getUserId();
            LinkedHashMap<Long, SysRequestHistory> merged = new LinkedHashMap<>();
            LinkedHashMap<String, LinkedHashSet<Long>> relatedBusinessIds = new LinkedHashMap<>();
            LinkedHashSet<Long> appealIds = new LinkedHashSet<>();
            LinkedHashSet<Long> businessIds = new LinkedHashSet<>();
            LinkedHashSet<Long> fineIds = new LinkedHashSet<>();
            int relatedPageSize = Math.max(size * 5, 100);
            int relatedHistoryPageSize = Math.max(size * 10, 200);

            appealIds.addAll(resolveCurrentUserAppealIds(appealId, relatedPageSize));
            appealIds.forEach(id -> registerBusinessId(relatedBusinessIds, businessIds, id, "APPEAL_"));

            fetchAllPages(pageNumber -> sysRequestHistoryService.findByUserId(userId, pageNumber, relatedPageSize), relatedPageSize)
                    .forEach(history -> {
                        if (appealId == null) {
                            putIfPresent(merged, history);
                            return;
                        }
                        putIfAppealScopedHistory(merged, history, appealId, relatedBusinessIds);
                    });

            if (appealId == null) {
                String currentUserIdCardNumber = tryResolveCurrentUserIdCardNumber();
                currentUserTrafficSupportService.listCurrentUserFineIds()
                        .forEach(id -> registerBusinessId(relatedBusinessIds, businessIds, id, "FINE_"));
                fineIds.addAll(relatedBusinessIds.getOrDefault("FINE_", new LinkedHashSet<>()));
                currentUserTrafficSupportService.listCurrentUserOffenseIds()
                        .forEach(id -> registerBusinessId(relatedBusinessIds, businessIds, id, "OFFENSE_"));
                currentUserTrafficSupportService.listCurrentUserDeductionIds()
                        .forEach(id -> registerBusinessId(relatedBusinessIds, businessIds, id, "DEDUCTION_"));
                if (currentUserIdCardNumber != null) {
                    currentUserTrafficSupportService.listCurrentUserVehicleIds()
                            .forEach(id -> registerBusinessId(relatedBusinessIds, businessIds, id, "VEHICLE_"));
                    paymentRecordService.findIdsByPayerIdCardAndFineIds(currentUserIdCardNumber, fineIds)
                            .forEach(id -> registerBusinessId(
                                    relatedBusinessIds,
                                    businessIds,
                                    id,
                                    "PAYMENT_",
                                    "PARTIAL_REFUND",
                                    "WAIVE_AND_REFUND"));
                }
            }

            fineIds.forEach(fineId -> fetchAllPages(
                            pageNumber -> sysRequestHistoryService.findRefundAudits(null, fineId, null, pageNumber, relatedPageSize),
                            relatedPageSize)
                    .forEach(history -> putIfPresent(merged, history)));
            appealIds.forEach(currentAppealId -> fetchAllPages(
                            pageNumber -> sysRequestHistoryService.searchByRequestUrlPrefix(
                                    "/api/appeals/" + currentAppealId + "/reviews",
                                    pageNumber,
                                    relatedHistoryPageSize),
                            relatedHistoryPageSize)
                    .forEach(history -> putIfAppealReviewHistory(merged, history, currentAppealId)));

            if (!businessIds.isEmpty()) {
                fetchAllPages(pageNumber -> sysRequestHistoryService.findByBusinessIds(businessIds, pageNumber, relatedHistoryPageSize),
                        relatedHistoryPageSize)
                        .forEach(history -> putIfRelatedBusinessHistory(merged, history, relatedBusinessIds));
            }

            List<SysRequestHistory> ordered = merged.values().stream()
                    .sorted(Comparator.comparing(SysRequestHistory::getUpdatedAt,
                                    Comparator.nullsLast(Comparator.reverseOrder()))
                            .thenComparing(SysRequestHistory::getCreatedAt,
                                    Comparator.nullsLast(Comparator.reverseOrder()))
                            .thenComparing(SysRequestHistory::getId,
                                    Comparator.nullsLast(Comparator.reverseOrder())))
                    .skip((long) (Math.max(page, 1) - 1) * Math.max(size, 1))
                    .limit(Math.max(size, 1))
                    .toList();
            return ResponseEntity.ok(ordered);
        } catch (IllegalArgumentException ex) {
            return handleCurrentUserProgressArgument(ex);
        } catch (IllegalStateException ex) {
            return handleCurrentUserProgressState(ex);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List current user progress failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/status")
    @Operation(summary = "List By Status")
    public ResponseEntity<List<SysRequestHistory>> listByStatus(@RequestParam String status,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(sysRequestHistoryService.findByBusinessStatus(status, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List request histories by status failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/idempotency/{key}")
    @Operation(summary = "Get By Idempotency Key")
    public ResponseEntity<SysRequestHistory> getByIdempotencyKey(@PathVariable String key) {
        try {
            Optional<SysRequestHistory> history = sysRequestHistoryService.findByIdempotencyKey(key);
            return history.map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get request history by idempotency key failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/refunds")
    @Operation(summary = "List Refund Audits")
    public ResponseEntity<List<SysRequestHistory>> listRefundAudits(@RequestParam(required = false) String status,
                                                                    @RequestParam(required = false) Long fineId,
                                                                    @RequestParam(required = false) Long paymentId,
                                                                    @RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "20") int size) {
        try {
            if (fineId != null || paymentId != null) {
                return ResponseEntity.ok(sysRequestHistoryService.findRefundAudits(status, fineId, paymentId, page, size));
            }
            if (status == null || status.isBlank()) {
                return ResponseEntity.ok(sysRequestHistoryService.findRefundAudits(page, size));
            }
            return ResponseEntity.ok(sysRequestHistoryService.findRefundAuditsByStatus(status, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List refund audits failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private <T> List<T> fetchAllPages(IntFunction<List<T>> pageFetcher, int pageSize) {
        List<T> allItems = new ArrayList<>();
        if (pageFetcher == null || pageSize < 1) {
            return allItems;
        }
        for (int pageNumber = 1; ; pageNumber++) {
            List<T> pageItems = pageFetcher.apply(pageNumber);
            if (pageItems == null || pageItems.isEmpty()) {
                break;
            }
            allItems.addAll(pageItems);
            if (pageItems.size() < pageSize) {
                break;
            }
        }
        return allItems;
    }

    private String tryResolveCurrentUserIdCardNumber() {
        try {
            return currentUserTrafficSupportService.getCurrentUserIdCardNumber();
        } catch (IllegalStateException ex) {
            return null;
        }
    }

    private void putIfPresent(LinkedHashMap<Long, SysRequestHistory> sink, SysRequestHistory history) {
        if (sink == null || history == null || history.getId() == null) {
            return;
        }
        sink.put(history.getId(), history);
    }

    private void putIfRelatedBusinessHistory(LinkedHashMap<Long, SysRequestHistory> sink,
                                             SysRequestHistory history,
                                             LinkedHashMap<String, LinkedHashSet<Long>> relatedBusinessIds) {
        if (!isRelatedBusinessHistory(history, relatedBusinessIds)) {
            return;
        }
        putIfPresent(sink, history);
    }

    private void putIfAppealScopedHistory(LinkedHashMap<Long, SysRequestHistory> sink,
                                          SysRequestHistory history,
                                          Long appealId,
                                          LinkedHashMap<String, LinkedHashSet<Long>> relatedBusinessIds) {
        if (!isAppealScopedHistory(history, appealId, relatedBusinessIds)) {
            return;
        }
        putIfPresent(sink, history);
    }

    private boolean isRelatedBusinessHistory(SysRequestHistory history,
                                             LinkedHashMap<String, LinkedHashSet<Long>> relatedBusinessIds) {
        if (history == null
                || history.getBusinessId() == null
                || history.getBusinessId() <= 0
                || relatedBusinessIds == null
                || relatedBusinessIds.isEmpty()) {
            return false;
        }
        String businessType = normalizeBusinessType(history.getBusinessType());
        if (businessType.isEmpty()) {
            return false;
        }
        for (var entry : relatedBusinessIds.entrySet()) {
            if (businessType.startsWith(entry.getKey()) && entry.getValue().contains(history.getBusinessId())) {
                return true;
            }
        }
        return false;
    }

    private boolean isAppealScopedHistory(SysRequestHistory history,
                                          Long appealId,
                                          LinkedHashMap<String, LinkedHashSet<Long>> relatedBusinessIds) {
        if (history == null || appealId == null || appealId <= 0) {
            return false;
        }
        if (isAppealReviewHistoryForAppeal(history, appealId)) {
            return true;
        }
        Long requestAppealId = parseRequestParamId(history.getRequestParams(), "appealId");
        if (appealId.equals(requestAppealId)) {
            return true;
        }
        if (isRelatedBusinessHistory(history, relatedBusinessIds)) {
            return true;
        }
        String requestUrl = history.getRequestUrl();
        return requestUrl != null
                && (requestUrl.contains("/api/appeals/" + appealId)
                || requestUrl.contains("/api/appeals/me/" + appealId));
    }

    private void putIfAppealReviewHistory(LinkedHashMap<Long, SysRequestHistory> sink,
                                          SysRequestHistory history,
                                          Long appealId) {
        if (!isAppealReviewHistoryForAppeal(history, appealId)) {
            return;
        }
        putIfPresent(sink, history);
    }

    private boolean isAppealReviewHistoryForAppeal(SysRequestHistory history, Long appealId) {
        if (history == null || appealId == null || appealId <= 0) {
            return false;
        }
        String businessType = normalizeBusinessType(history.getBusinessType());
        if (!businessType.startsWith("APPEAL_REVIEW_")) {
            return false;
        }
        Long requestAppealId = parseRequestParamId(history.getRequestParams(), "appealId");
        if (appealId.equals(requestAppealId)) {
            return true;
        }
        String requestUrl = history.getRequestUrl();
        return requestUrl != null && requestUrl.contains("/api/appeals/" + appealId + "/reviews");
    }

    private Long parseRequestParamId(String requestParams, String key) {
        if (requestParams == null || requestParams.isBlank() || key == null || key.isBlank()) {
            return null;
        }
        String normalizedKey = key.trim();
        for (String segment : requestParams.split(",")) {
            if (segment == null || segment.isBlank()) {
                continue;
            }
            String trimmed = segment.trim();
            int separatorIndex = trimmed.indexOf('=');
            if (separatorIndex <= 0 || separatorIndex == trimmed.length() - 1) {
                continue;
            }
            String currentKey = trimmed.substring(0, separatorIndex).trim();
            if (!normalizedKey.equals(currentKey)) {
                continue;
            }
            try {
                return Long.parseLong(trimmed.substring(separatorIndex + 1).trim());
            } catch (NumberFormatException ex) {
                return null;
            }
        }
        return null;
    }

    private LinkedHashSet<Long> resolveCurrentUserAppealIds(Long appealId, int pageSize) {
        LinkedHashSet<Long> appealIds = new LinkedHashSet<>();
        if (appealId != null) {
            if (appealId <= 0) {
                throw new IllegalArgumentException("Appeal ID must be greater than zero");
            }
            if (!currentUserOwnsAppeal(appealId, pageSize)) {
                throw new IllegalArgumentException("Appeal ID is outside the current user scope");
            }
            appealIds.add(appealId);
            return appealIds;
        }
        fetchAllPages(pageNumber -> currentUserTrafficSupportService.listCurrentUserAppeals(pageNumber, pageSize), pageSize).stream()
                .map(appeal -> appeal == null ? null : appeal.getAppealId())
                .filter(id -> id != null && id > 0)
                .forEach(appealIds::add);
        return appealIds;
    }

    private boolean currentUserOwnsAppeal(Long appealId, int pageSize) {
        if (appealId == null || appealId <= 0 || pageSize < 1) {
            return false;
        }
        for (int pageNumber = 1; ; pageNumber++) {
            List<AppealRecord> pageItems =
                    currentUserTrafficSupportService.listCurrentUserAppeals(pageNumber, pageSize);
            if (pageItems == null || pageItems.isEmpty()) {
                return false;
            }
            boolean matched = pageItems.stream()
                    .map(appeal -> appeal == null ? null : appeal.getAppealId())
                    .anyMatch(appealId::equals);
            if (matched) {
                return true;
            }
            if (pageItems.size() < pageSize) {
                return false;
            }
        }
    }

    private void registerBusinessId(LinkedHashMap<String, LinkedHashSet<Long>> relatedBusinessIds,
                                    LinkedHashSet<Long> businessIds,
                                    Long businessId,
                                    String... businessTypePrefixes) {
        if (businessId == null || businessId <= 0) {
            return;
        }
        if (businessIds != null) {
            businessIds.add(businessId);
        }
        if (relatedBusinessIds == null || businessTypePrefixes == null) {
            return;
        }
        for (String businessTypePrefix : businessTypePrefixes) {
            String normalizedPrefix = normalizeBusinessType(businessTypePrefix);
            if (normalizedPrefix.isEmpty()) {
                continue;
            }
            relatedBusinessIds.computeIfAbsent(normalizedPrefix, ignored -> new LinkedHashSet<>()).add(businessId);
        }
    }

    private String normalizeBusinessType(String businessType) {
        if (businessType == null) {
            return "";
        }
        return businessType.trim().toUpperCase();
    }

    private <T> ResponseEntity<T> handleCurrentUserProgressArgument(IllegalArgumentException ex) {
        String message = ex == null || ex.getMessage() == null
                ? ""
                : ex.getMessage().trim().toLowerCase(Locale.ROOT);
        if (message.contains("outside the current user scope")) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
    }

    private <T> ResponseEntity<T> handleCurrentUserProgressState(IllegalStateException ex) {
        String message = ex == null || ex.getMessage() == null
                ? ""
                : ex.getMessage().trim().toLowerCase(Locale.ROOT);
        if (message.contains("current user is not authenticated") || message.contains("current user not found")) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        if (message.contains("current user profile has no id card number")) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}
