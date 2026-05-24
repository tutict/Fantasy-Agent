package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.OffenseTypeDict;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.service.AppealRecordService;
import com.tutict.finalassignmentbackend.service.DeductionRecordService;
import com.tutict.finalassignmentbackend.service.FineRecordService;
import com.tutict.finalassignmentbackend.service.OffenseRecordService;
import com.tutict.finalassignmentbackend.service.OffenseTypeDictService;
import com.tutict.finalassignmentbackend.service.PaymentRecordService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/violations")
@Tag(name = "Traffic Violations", description = "Traffic Violations endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE", "APPEAL_REVIEWER"})
public class TrafficViolationController {

    private static final Logger LOG = Logger.getLogger(TrafficViolationController.class.getName());
    private static final int SUMMARY_BATCH_SIZE = 200;

    private final OffenseRecordService offenseRecordService;
    private final FineRecordService fineRecordService;
    private final PaymentRecordService paymentRecordService;
    private final DeductionRecordService deductionRecordService;
    private final AppealRecordService appealRecordService;
    private final OffenseTypeDictService offenseTypeDictService;

    public TrafficViolationController(OffenseRecordService offenseRecordService,
                                      FineRecordService fineRecordService,
                                      PaymentRecordService paymentRecordService,
                                      DeductionRecordService deductionRecordService,
                                      AppealRecordService appealRecordService,
                                      OffenseTypeDictService offenseTypeDictService) {
        this.offenseRecordService = offenseRecordService;
        this.fineRecordService = fineRecordService;
        this.paymentRecordService = paymentRecordService;
        this.deductionRecordService = deductionRecordService;
        this.appealRecordService = appealRecordService;
        this.offenseTypeDictService = offenseTypeDictService;
    }

    @GetMapping
    @Operation(summary = "List Violations")
    public ResponseEntity<List<OffenseRecord>> listViolations(@RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.listOffenses(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List violations failed", ex);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    @GetMapping("/dashboard-summary")
    @Operation(summary = "Dashboard Summary")
    public ResponseEntity<Map<String, Object>> dashboardSummary() {
        try {
            LocalDate startDate = LocalDate.now().minusDays(6);
            Map<String, String> offenseTypeNames = buildOffenseTypeNameMap();
            Map<String, Long> violationTypes = new LinkedHashMap<>();
            Map<LocalDate, TrendPoint> trendBuckets = initTrendBuckets(startDate);
            Map<String, Long> appealReasons = new LinkedHashMap<>();
            Map<String, Long> paymentStatus = new LinkedHashMap<>();

            aggregateOffenseSummary(
                    offenseTypeNames,
                    startDate,
                    violationTypes,
                    trendBuckets,
                    appealReasons);
            aggregatePaymentStatusSummary(paymentStatus);

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("startTime", startDate.atStartOfDay());
            payload.put("violationTypes", violationTypes);
            payload.put("timeSeries", buildTrendSummary(trendBuckets));
            payload.put("appealReasons", appealReasons);
            payload.put("paymentStatus", paymentStatus);
            return ResponseEntity.ok(payload);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Build violation dashboard summary failed", ex);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    @GetMapping("/{offenseId}")
    @Operation(summary = "Violation Details")
    public ResponseEntity<Map<String, Object>> violationDetails(@PathVariable Long offenseId) {
        try {
            OffenseRecord offense = offenseRecordService.findById(offenseId);
            if (offense == null) {
                return ResponseEntity.notFound().build();
            }
            Map<String, Object> payload = new HashMap<>();
            payload.put("offense", offense);

            List<FineRecord> fines = fineRecordService.findByOffenseId(offenseId, 1, 50);
            payload.put("fines", fines);

            List<PaymentRecord> payments = new ArrayList<>();
            for (FineRecord fine : fines) {
                if (fine.getFineId() != null) {
                    payments.addAll(sanitizePayments(paymentRecordService.findByFineId(fine.getFineId(), 1, 20)));
                }
            }
            payload.put("payments", payments);

            List<DeductionRecord> deductions = deductionRecordService.findByOffenseId(offenseId, 1, 50);
            payload.put("deductions", deductions);

            List<AppealRecord> appeals = appealRecordService.findByOffenseId(offenseId, 1, 20);
            payload.put("appeals", appeals);

            return ResponseEntity.ok(payload);
        } catch (Exception ex) {
            LOG.log(Level.SEVERE, "Get violation details failed", ex);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    @GetMapping("/status")
    @Operation(summary = "Violation By Status")
    public ResponseEntity<List<OffenseRecord>> violationByStatus(@RequestParam String processStatus,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(offenseRecordService.searchByProcessStatus(processStatus, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Filter violations by status failed", ex);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    private void aggregateOffenseSummary(Map<String, String> offenseTypeNames,
                                         LocalDate startDate,
                                         Map<String, Long> violationTypes,
                                         Map<LocalDate, TrendPoint> trendBuckets,
                                         Map<String, Long> appealReasons) {
        for (int page = 1; ; page++) {
            List<OffenseRecord> offenses = loadOffensePage(page, SUMMARY_BATCH_SIZE);
            if (offenses.isEmpty()) {
                break;
            }
            List<Long> offenseIds = new ArrayList<>();
            for (OffenseRecord offense : offenses) {
                if (offense == null) {
                    continue;
                }
                mergeSummaryCount(violationTypes, resolveOffenseTypeLabel(offense, offenseTypeNames));
                accumulateTrendPoint(trendBuckets, offense, startDate);
                if (offense.getOffenseId() != null) {
                    offenseIds.add(offense.getOffenseId());
                }
            }
            aggregateAppealReasons(offenseIds, appealReasons);
            if (offenses.size() < SUMMARY_BATCH_SIZE) {
                break;
            }
        }
    }

    private List<OffenseRecord> loadOffensePage(int page, int size) {
        List<OffenseRecord> offenses = offenseRecordService.listOffenses(page, size);
        return offenses != null ? offenses : List.of();
    }

    private void aggregateAppealReasons(List<Long> offenseIds, Map<String, Long> appealReasons) {
        if (offenseIds == null || offenseIds.isEmpty()) {
            return;
        }
        for (int page = 1; ; page++) {
            List<AppealRecord> appeals = loadAppealPage(offenseIds, page, SUMMARY_BATCH_SIZE);
            if (appeals.isEmpty()) {
                break;
            }
            for (AppealRecord appeal : appeals) {
                if (appeal == null) {
                    continue;
                }
                mergeSummaryCount(appealReasons, normalizeSummaryLabel(appeal.getAppealReason()));
            }
            if (appeals.size() < SUMMARY_BATCH_SIZE) {
                break;
            }
        }
    }

    private List<AppealRecord> loadAppealPage(List<Long> offenseIds, int page, int size) {
        List<AppealRecord> appeals = appealRecordService.findByOffenseIds(offenseIds, page, size);
        return appeals != null ? appeals : List.of();
    }

    private void aggregatePaymentStatusSummary(Map<String, Long> paymentStatus) {
        for (int page = 1; ; page++) {
            List<FineRecord> fines = loadFinePage(page, SUMMARY_BATCH_SIZE);
            if (fines.isEmpty()) {
                break;
            }
            for (FineRecord fine : fines) {
                if (fine == null) {
                    continue;
                }
                mergeSummaryCount(paymentStatus, normalizeSummaryLabel(fine.getPaymentStatus()));
            }
            if (fines.size() < SUMMARY_BATCH_SIZE) {
                break;
            }
        }
    }

    private List<FineRecord> loadFinePage(int page, int size) {
        List<FineRecord> fines = fineRecordService.listFines(page, size);
        return fines != null ? fines : List.of();
    }

    private void mergeSummaryCount(Map<String, Long> summary, String rawLabel) {
        String label = normalizeSummaryLabel(rawLabel);
        if (summary == null) {
            return;
        }
        summary.merge(label, 1L, Long::sum);
    }

    private Map<LocalDate, TrendPoint> initTrendBuckets(LocalDate startDate) {
        Map<LocalDate, TrendPoint> buckets = new LinkedHashMap<>();
        for (int index = 0; index < 7; index++) {
            buckets.put(startDate.plusDays(index), new TrendPoint());
        }
        return buckets;
    }

    private void accumulateTrendPoint(Map<LocalDate, TrendPoint> buckets,
                                      OffenseRecord offense,
                                      LocalDate startDate) {
        if (buckets == null || offense == null || startDate == null) {
            return;
        }
        LocalDateTime offenseTime = offense.getOffenseTime();
        if (offenseTime == null) {
            return;
        }
        LocalDate offenseDate = offenseTime.toLocalDate();
        LocalDate endDate = startDate.plusDays(6);
        if (offenseDate.isBefore(startDate) || offenseDate.isAfter(endDate)) {
            return;
        }
        TrendPoint point = buckets.get(offenseDate);
        if (point == null) {
            return;
        }
        point.addFineAmount(offense.getFineAmount());
        point.addDeductedPoints(offense.getDeductedPoints());
    }

    private List<Map<String, Object>> buildTrendSummary(Map<LocalDate, TrendPoint> buckets) {
        List<Map<String, Object>> summary = new ArrayList<>(buckets.size());
        for (Map.Entry<LocalDate, TrendPoint> entry : buckets.entrySet()) {
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("time", entry.getKey().atStartOfDay());
            point.put("value1", entry.getValue().fineAmount);
            point.put("value2", entry.getValue().deductedPoints);
            summary.add(point);
        }
        return summary;
    }

    private Map<String, String> buildOffenseTypeNameMap() {
        Map<String, String> names = new HashMap<>();
        for (int page = 1; ; page++) {
            List<OffenseTypeDict> offenseTypes = loadOffenseTypePage(page, SUMMARY_BATCH_SIZE);
            if (offenseTypes.isEmpty()) {
                break;
            }
            for (OffenseTypeDict dict : offenseTypes) {
                if (dict == null) {
                    continue;
                }
                String offenseCode = trimToNull(dict.getOffenseCode());
                String offenseName = trimToNull(dict.getOffenseName());
                if (offenseCode == null || offenseName == null) {
                    continue;
                }
                names.putIfAbsent(offenseCode, offenseName);
            }
            if (offenseTypes.size() < SUMMARY_BATCH_SIZE) {
                break;
            }
        }
        return names;
    }

    private List<OffenseTypeDict> loadOffenseTypePage(int page, int size) {
        List<OffenseTypeDict> offenseTypes = offenseTypeDictService.findAll(page, size);
        return offenseTypes != null ? offenseTypes : List.of();
    }

    private String resolveOffenseTypeLabel(OffenseRecord offense, Map<String, String> offenseTypeNames) {
        String offenseCode = trimToNull(offense.getOffenseCode());
        if (offenseCode != null) {
            String resolvedName = trimToNull(offenseTypeNames.get(offenseCode));
            if (resolvedName != null) {
                return resolvedName;
            }
            return offenseCode;
        }
        String offenseDescription = trimToNull(offense.getOffenseDescription());
        return offenseDescription != null ? offenseDescription : "Other";
    }

    private String normalizeSummaryLabel(String value) {
        String trimmed = trimToNull(value);
        return trimmed != null ? trimmed : "";
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private List<PaymentRecord> sanitizePayments(List<PaymentRecord> payments) {
        if (payments == null || payments.isEmpty()) {
            return List.of();
        }
        List<PaymentRecord> sanitized = new ArrayList<>(payments.size());
        for (PaymentRecord payment : payments) {
            if (payment == null) {
                continue;
            }
            sanitized.add(sanitizePayment(payment));
        }
        return sanitized;
    }

    private PaymentRecord sanitizePayment(PaymentRecord payment) {
        PaymentRecord sanitized = new PaymentRecord();
        sanitized.setPaymentId(payment.getPaymentId());
        sanitized.setFineId(payment.getFineId());
        sanitized.setPaymentNumber(payment.getPaymentNumber());
        sanitized.setPaymentAmount(payment.getPaymentAmount());
        sanitized.setPaymentMethod(payment.getPaymentMethod());
        sanitized.setPaymentTime(payment.getPaymentTime());
        sanitized.setPaymentChannel(payment.getPaymentChannel());
        sanitized.setPayerName(payment.getPayerName());
        sanitized.setPayerIdCard(maskSensitiveValue(payment.getPayerIdCard(), 3, 4));
        sanitized.setPayerContact(maskSensitiveValue(payment.getPayerContact(), 3, 4));
        sanitized.setBankName(payment.getBankName());
        sanitized.setBankAccount(maskSensitiveValue(payment.getBankAccount(), 4, 4));
        sanitized.setTransactionId(payment.getTransactionId());
        sanitized.setReceiptNumber(payment.getReceiptNumber());
        sanitized.setReceiptUrl(null);
        sanitized.setPaymentStatus(payment.getPaymentStatus());
        sanitized.setRefundAmount(payment.getRefundAmount());
        sanitized.setRefundTime(payment.getRefundTime());
        sanitized.setCreatedAt(payment.getCreatedAt());
        sanitized.setUpdatedAt(payment.getUpdatedAt());
        sanitized.setCreatedBy(payment.getCreatedBy());
        sanitized.setUpdatedBy(payment.getUpdatedBy());
        sanitized.setDeletedAt(payment.getDeletedAt());
        sanitized.setRemarks(payment.getRemarks());
        return sanitized;
    }

    private String maskSensitiveValue(String value, int prefixLength, int suffixLength) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return trimmed;
        }
        int effectivePrefix = Math.max(prefixLength, 0);
        int effectiveSuffix = Math.max(suffixLength, 0);
        if (trimmed.length() <= effectivePrefix + effectiveSuffix) {
            return "*".repeat(Math.max(trimmed.length(), 3));
        }
        return trimmed.substring(0, effectivePrefix)
                + "*".repeat(Math.max(trimmed.length() - effectivePrefix - effectiveSuffix, 3))
                + trimmed.substring(trimmed.length() - effectiveSuffix);
    }

    private static final class TrendPoint {
        private double fineAmount;
        private int deductedPoints;

        private void addFineAmount(BigDecimal amount) {
            if (amount != null) {
                fineAmount += amount.doubleValue();
            }
        }

        private void addDeductedPoints(Integer points) {
            if (points != null) {
                deductedPoints += points;
            }
        }
    }
}
