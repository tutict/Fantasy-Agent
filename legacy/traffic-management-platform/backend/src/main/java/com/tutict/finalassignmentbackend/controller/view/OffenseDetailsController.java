package com.tutict.finalassignmentbackend.controller.view;

import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.service.AppealRecordService;
import com.tutict.finalassignmentbackend.service.DeductionRecordService;
import com.tutict.finalassignmentbackend.service.FineRecordService;
import com.tutict.finalassignmentbackend.service.OffenseRecordService;
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
import org.springframework.web.bind.annotation.RestController;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/view/offenses")
@Tag(name = "Offense Details View", description = "Offense Details View endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE", "APPEAL_REVIEWER"})
public class OffenseDetailsController {

    private static final Logger LOG = Logger.getLogger(OffenseDetailsController.class.getName());
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final OffenseRecordService offenseRecordService;
    private final FineRecordService fineRecordService;
    private final PaymentRecordService paymentRecordService;
    private final DeductionRecordService deductionRecordService;
    private final AppealRecordService appealRecordService;

    public OffenseDetailsController(OffenseRecordService offenseRecordService,
                                    FineRecordService fineRecordService,
                                    PaymentRecordService paymentRecordService,
                                    DeductionRecordService deductionRecordService,
                                    AppealRecordService appealRecordService) {
        this.offenseRecordService = offenseRecordService;
        this.fineRecordService = fineRecordService;
        this.paymentRecordService = paymentRecordService;
        this.deductionRecordService = deductionRecordService;
        this.appealRecordService = appealRecordService;
    }

    @GetMapping("/{offenseId}")
    @Operation(summary = "Get Details")
    public ResponseEntity<Map<String, Object>> getDetails(@PathVariable Long offenseId) {
        try {
            OffenseRecord offense = offenseRecordService.findById(offenseId);
            if (offense == null) {
                return ResponseEntity.notFound().build();
            }

            Map<String, Object> payload = new HashMap<>();
            payload.put("offense", offense);

            List<FineRecord> fines = fineRecordService.findByOffenseId(offenseId, 1, 20);
            payload.put("fines", fines);

            List<PaymentRecord> payments = new ArrayList<>();
            for (FineRecord fine : fines) {
                if (fine.getFineId() != null) {
                    payments.addAll(sanitizePayments(paymentRecordService.findByFineId(fine.getFineId(), 1, 10)));
                }
            }
            payload.put("payments", payments);

            List<DeductionRecord> deductions = deductionRecordService.findByOffenseId(offenseId, 1, 20);
            payload.put("deductions", deductions);

            List<AppealRecord> appeals = appealRecordService.findByOffenseId(offenseId, 1, 20);
            payload.put("appeals", appeals);

            payload.put("timeline", buildTimeline(offense, fines, payments, appeals));

            return ResponseEntity.ok(payload);
        } catch (Exception ex) {
            LOG.log(Level.SEVERE, "Fetch offense view failed", ex);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    private List<Map<String, Object>> buildTimeline(OffenseRecord offense,
                                                    List<FineRecord> fines,
                                                    List<PaymentRecord> payments,
                                                    List<AppealRecord> appeals) {
        List<Map<String, Object>> timeline = new ArrayList<>();

        Map<String, Object> offenseNode = new HashMap<>();
        offenseNode.put("event", "Offense recorded");
        offenseNode.put("timestamp", offense.getOffenseTime() != null ? offense.getOffenseTime().format(FORMATTER) : null);
        offenseNode.put("status", offense.getProcessStatus());
        timeline.add(offenseNode);

        for (FineRecord fine : fines) {
            Map<String, Object> fineNode = new HashMap<>();
            fineNode.put("event", "Fine issued");
            fineNode.put("timestamp", fine.getFineDate() != null ? fine.getFineDate().toString() : null);
            fineNode.put("status", fine.getPaymentStatus());
            timeline.add(fineNode);
        }

        for (PaymentRecord payment : payments) {
            Map<String, Object> paymentNode = new HashMap<>();
            paymentNode.put("event", "Payment completed");
            paymentNode.put("timestamp", payment.getPaymentTime() != null ? payment.getPaymentTime().format(FORMATTER) : null);
            paymentNode.put("status", payment.getPaymentStatus());
            timeline.add(paymentNode);
        }

        for (AppealRecord appeal : appeals) {
            Map<String, Object> appealNode = new HashMap<>();
            appealNode.put("event", "Appeal submitted");
            appealNode.put("timestamp", appeal.getCreatedAt() != null ? appeal.getCreatedAt().format(FORMATTER) : null);
            appealNode.put("status", appeal.getProcessStatus());
            timeline.add(appealNode);
        }

        return timeline;
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
}
