package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.PaymentRecordService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
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

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.function.Supplier;

@RestController
@RequestMapping("/api/payments")
@Tag(name = "", description = " endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "FINANCE"})
public class PaymentRecordController {

    private final PaymentRecordService paymentRecordService;
    private final CurrentUserTrafficSupportService currentUserTrafficSupportService;

    public PaymentRecordController(PaymentRecordService paymentRecordService,
                                   CurrentUserTrafficSupportService currentUserTrafficSupportService) {
        this.paymentRecordService = paymentRecordService;
        this.currentUserTrafficSupportService = currentUserTrafficSupportService;
    }

    @PostMapping("/me")
    @RolesAllowed({"USER"})
    @Operation(summary = "Create Current User Payment")
    public ResponseEntity<PaymentRecord> createCurrentUserPayment(
            @Valid @RequestBody CurrentUserPaymentCreateRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        PaymentRecord draft = toCurrentUserCreatePayment(request);
        try {
            return executeIdempotentPaymentAction(
                    idempotencyKey,
                    draft,
                    "create",
                    HttpStatus.CREATED,
                    () -> currentUserTrafficSupportService.createPaymentForCurrentUser(draft));
        } catch (IllegalStateException ex) {
            return handleCurrentUserPaymentState(ex);
        }
    }

    @GetMapping("/me")
    @RolesAllowed({"USER"})
    @Operation(summary = "List Current User Payments")
    public ResponseEntity<List<PaymentRecord>> listCurrentUserPayments(@RequestParam(defaultValue = "1") int page,
                                                                       @RequestParam(defaultValue = "20") int size,
                                                                       @RequestParam(required = false) Long fineId) {
        try {
            return ResponseEntity.ok(fineId == null
                    ? currentUserTrafficSupportService.listCurrentUserPayments(page, size)
                    : currentUserTrafficSupportService.listCurrentUserPaymentsByFineId(fineId, page, size));
        } catch (IllegalStateException ex) {
            return handleCurrentUserPaymentState(ex);
        }
    }

    @PostMapping("/me/{paymentId}/confirm")
    @RolesAllowed({"USER"})
    @Operation(summary = "Confirm Current User Payment")
    public ResponseEntity<PaymentRecord> confirmCurrentUserPayment(
            @PathVariable Long paymentId,
            @Valid @RequestBody CurrentUserPaymentConfirmationRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        PaymentRecord confirmationDraft = new PaymentRecord();
        confirmationDraft.setPaymentId(paymentId);
        confirmationDraft.setTransactionId(request.getTransactionId());
        confirmationDraft.setReceiptUrl(request.getReceiptUrl());
        try {
            return executeIdempotentPaymentAction(
                    idempotencyKey,
                    confirmationDraft,
                    "confirm",
                    HttpStatus.OK,
                    () -> currentUserTrafficSupportService.confirmCurrentUserPayment(paymentId, confirmationDraft));
        } catch (IllegalStateException ex) {
            return handleCurrentUserPaymentState(ex);
        }
    }

    @PostMapping("/me/{paymentId}/proof")
    @RolesAllowed({"USER"})
    @Operation(summary = "Update Current User Payment Proof")
    public ResponseEntity<PaymentRecord> updateCurrentUserPaymentProof(
            @PathVariable Long paymentId,
            @Valid @RequestBody CurrentUserPaymentProofRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        PaymentRecord proofDraft = new PaymentRecord();
        proofDraft.setPaymentId(paymentId);
        proofDraft.setReceiptUrl(request.getReceiptUrl());
        try {
            return executeIdempotentPaymentAction(
                    idempotencyKey,
                    proofDraft,
                    "proof",
                    HttpStatus.OK,
                    () -> currentUserTrafficSupportService.updateCurrentUserPaymentProof(paymentId, proofDraft));
        } catch (IllegalStateException ex) {
            return handleCurrentUserPaymentState(ex);
        }
    }

    @PostMapping("/{paymentId}/finance-review")
    @Operation(summary = "Review Self-Service Payment")
    public ResponseEntity<PaymentRecord> reviewPayment(
            @PathVariable Long paymentId,
            @Valid @RequestBody PaymentFinanceReviewRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        PaymentRecord reviewDraft = new PaymentRecord();
        reviewDraft.setPaymentId(paymentId);
        reviewDraft.setRemarks("reviewResult=" + request.getReviewResult()
                + ",reviewOpinion=" + request.getReviewOpinion());
        return executeIdempotentPaymentAction(
                idempotencyKey,
                reviewDraft,
                "review",
                HttpStatus.OK,
                () -> paymentRecordService.recordFinanceReview(
                        paymentId,
                        request.getReviewResult(),
                        request.getReviewOpinion()));
    }

    @PostMapping
    @Operation(summary = "Create Payment")
    public ResponseEntity<PaymentRecord> createPayment(
            @Valid @RequestBody CreatePaymentRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        PaymentRecord draft = toPaymentRecord(request);
        return executeIdempotentPaymentAction(
                idempotencyKey,
                draft,
                "create",
                HttpStatus.CREATED,
                () -> paymentRecordService.createPaymentRecord(draft));
    }

    @PutMapping("/{paymentId}")
    @Operation(summary = "Update Payment")
    public ResponseEntity<PaymentRecord> updatePayment(@PathVariable Long paymentId,
                                                       @RequestBody PaymentRecord request,
                                                       @RequestHeader(value = "Idempotency-Key", required = false)
                                                       String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @DeleteMapping("/{paymentId}")
    @Operation(summary = "Delete Payment")
    public ResponseEntity<Void> deletePayment(@PathVariable Long paymentId) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/{paymentId}")
    @Operation(summary = "Get Payment")
    public ResponseEntity<PaymentRecord> getPayment(@PathVariable Long paymentId) {
        PaymentRecord record = paymentRecordService.findById(paymentId);
        return record == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(record);
    }

    @GetMapping
    @Operation(summary = "List Payments")
    public ResponseEntity<List<PaymentRecord>> listPayments(@RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.listPayments(page, size));
    }

    @GetMapping("/fine/{fineId}")
    @Operation(summary = "Find By Fine")
    public ResponseEntity<List<PaymentRecord>> findByFine(@PathVariable Long fineId,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.findByFineId(fineId, page, size));
    }

    @GetMapping("/search/payer")
    @Operation(summary = "Search By Payer")
    public ResponseEntity<List<PaymentRecord>> searchByPayer(@RequestParam("idCard") String idCard,
                                                             @RequestParam(defaultValue = "1") int page,
                                                             @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByPayerIdCard(idCard, page, size));
    }

    @GetMapping("/search/status")
    @Operation(summary = "Search By Status")
    public ResponseEntity<List<PaymentRecord>> searchByStatus(@RequestParam String status,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByPaymentStatus(status, page, size));
    }

    @GetMapping("/search/transaction")
    @Operation(summary = "Search By Transaction")
    public ResponseEntity<List<PaymentRecord>> searchByTransaction(@RequestParam String transactionId,
                                                                   @RequestParam(defaultValue = "1") int page,
                                                                   @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByTransactionId(transactionId, page, size));
    }

    @GetMapping("/search/payment-number")
    @Operation(summary = "Search By Payment Number")
    public ResponseEntity<List<PaymentRecord>> searchByPaymentNumber(@RequestParam String paymentNumber,
                                                                     @RequestParam(defaultValue = "1") int page,
                                                                     @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByPaymentNumber(paymentNumber, page, size));
    }

    @GetMapping("/search/payer-name")
    @Operation(summary = "Search By Payer Name")
    public ResponseEntity<List<PaymentRecord>> searchByPayerName(@RequestParam String payerName,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByPayerName(payerName, page, size));
    }

    @GetMapping("/search/payment-method")
    @Operation(summary = "Search By Payment Method")
    public ResponseEntity<List<PaymentRecord>> searchByPaymentMethod(@RequestParam String paymentMethod,
                                                                     @RequestParam(defaultValue = "1") int page,
                                                                     @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByPaymentMethod(paymentMethod, page, size));
    }

    @GetMapping("/search/payment-channel")
    @Operation(summary = "Search By Payment Channel")
    public ResponseEntity<List<PaymentRecord>> searchByPaymentChannel(@RequestParam String paymentChannel,
                                                                      @RequestParam(defaultValue = "1") int page,
                                                                      @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByPaymentChannel(paymentChannel, page, size));
    }

    @GetMapping("/review-tasks")
    @Operation(summary = "List Finance Review Tasks")
    public ResponseEntity<List<PaymentRecord>> listFinanceReviewTasks(@RequestParam(defaultValue = "1") int page,
                                                                      @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.listFinanceReviewTasks(page, size));
    }

    @GetMapping("/search/time-range")
    @Operation(summary = "Search By Time Range")
    public ResponseEntity<List<PaymentRecord>> searchByTimeRange(@RequestParam String startTime,
                                                                 @RequestParam String endTime,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(paymentRecordService.searchByPaymentTimeRange(startTime, endTime, page, size));
    }

    @PutMapping("/{paymentId}/status/{state}")
    @Operation(summary = "Update Payment Status")
    public ResponseEntity<PaymentRecord> updatePaymentStatus(@PathVariable Long paymentId,
                                                             @PathVariable PaymentState state) {
        return ResponseEntity.ok(paymentRecordService.transitionPaymentStatus(paymentId, state));
    }

    private ResponseEntity<PaymentRecord> executeIdempotentPaymentAction(String idempotencyKey,
                                                                         PaymentRecord draft,
                                                                         String action,
                                                                         HttpStatus successStatus,
                                                                         Supplier<PaymentRecord> operation) {
        boolean useKey = hasKey(idempotencyKey);
        if (useKey) {
            if (paymentRecordService.shouldSkipProcessing(idempotencyKey)) {
                return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
            }
            paymentRecordService.checkAndInsertIdempotency(idempotencyKey, draft, action);
        }
        try {
            PaymentRecord saved = operation.get();
            if (useKey && saved != null && saved.getPaymentId() != null) {
                paymentRecordService.markHistorySuccess(idempotencyKey, saved.getPaymentId());
            }
            return ResponseEntity.status(successStatus).body(saved);
        } catch (RuntimeException ex) {
            if (useKey) {
                paymentRecordService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            throw ex;
        }
    }

    private PaymentRecord toCurrentUserCreatePayment(CurrentUserPaymentCreateRequest request) {
        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setFineId(request.getFineId());
        paymentRecord.setPaymentAmount(request.getPaymentAmount());
        paymentRecord.setPaymentMethod(request.getPaymentMethod());
        paymentRecord.setPaymentChannel(request.getPaymentChannel());
        paymentRecord.setRemarks(request.getRemarks());
        return paymentRecord;
    }

    private PaymentRecord toPaymentRecord(CreatePaymentRequest request) {
        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setFineId(request.getFineId());
        paymentRecord.setPaymentAmount(request.getPaymentAmount());
        paymentRecord.setPaymentMethod(request.getPaymentMethod());
        paymentRecord.setPaymentTime(request.getPaymentTime());
        paymentRecord.setPaymentChannel(request.getPaymentChannel());
        paymentRecord.setPayerName(request.getPayerName());
        paymentRecord.setPayerIdCard(request.getPayerIdCard());
        paymentRecord.setPayerContact(request.getPayerContact());
        paymentRecord.setBankName(request.getBankName());
        paymentRecord.setBankAccount(request.getBankAccount());
        paymentRecord.setTransactionId(request.getTransactionId());
        paymentRecord.setReceiptNumber(request.getReceiptNumber());
        paymentRecord.setReceiptUrl(request.getReceiptUrl());
        paymentRecord.setRemarks(request.getRemarks());
        return paymentRecord;
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private <T> ResponseEntity<T> handleCurrentUserPaymentState(IllegalStateException ex) {
        String message = ex == null || ex.getMessage() == null
                ? ""
                : ex.getMessage().trim().toLowerCase(Locale.ROOT);
        if (message.contains("current user is not authenticated") || message.contains("current user not found")) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        if (message.contains("fine record not found") || message.contains("payment record not found")) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        if (message.contains("does not belong to current user")
                || message.contains("outside the current user scope")) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }
        if (message.contains("current user profile has no id card number")
                || message.contains("already fully paid")
                || message.contains("no payable amount")
                || message.contains("exceeds current remaining payable amount")
                || message.contains("pending self-service payment")
                || message.contains("only self-service payment")
                || message.contains("only pending self-service payment")
                || message.contains("only confirmed self-service payment")
                || message.contains("has expired")
                || message.contains("waived fines do not require payment proof updates")
                || message.contains("missing the linked fine")) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
        throw ex;
    }

    public static class CurrentUserPaymentCreateRequest {
        @NotNull(message = "Fine ID is required")
        @Positive(message = "Fine ID must be greater than zero")
        private Long fineId;

        @NotNull(message = "Payment amount is required")
        @DecimalMin(value = "0.01", message = "Payment amount must be greater than zero")
        private BigDecimal paymentAmount;

        @Size(max = 32, message = "Payment method must be at most 32 characters")
        private String paymentMethod;

        @Size(max = 64, message = "Payment channel must be at most 64 characters")
        private String paymentChannel;

        @Size(max = 255, message = "Remarks must be at most 255 characters")
        private String remarks;

        public Long getFineId() {
            return fineId;
        }

        public void setFineId(Long fineId) {
            this.fineId = fineId;
        }

        public BigDecimal getPaymentAmount() {
            return paymentAmount;
        }

        public void setPaymentAmount(BigDecimal paymentAmount) {
            this.paymentAmount = paymentAmount;
        }

        public String getPaymentMethod() {
            return paymentMethod;
        }

        public void setPaymentMethod(String paymentMethod) {
            this.paymentMethod = paymentMethod;
        }

        public String getPaymentChannel() {
            return paymentChannel;
        }

        public void setPaymentChannel(String paymentChannel) {
            this.paymentChannel = paymentChannel;
        }

        public String getRemarks() {
            return remarks;
        }

        public void setRemarks(String remarks) {
            this.remarks = remarks;
        }
    }

    public static class CreatePaymentRequest {
        @NotNull(message = "Fine ID is required")
        @Positive(message = "Fine ID must be greater than zero")
        private Long fineId;

        @NotNull(message = "Payment amount is required")
        @DecimalMin(value = "0.01", message = "Payment amount must be greater than zero")
        private BigDecimal paymentAmount;

        @Size(max = 32, message = "Payment method must be at most 32 characters")
        private String paymentMethod;

        private LocalDateTime paymentTime;

        @Size(max = 64, message = "Payment channel must be at most 64 characters")
        private String paymentChannel;

        @NotBlank(message = "Payer name must not be blank")
        @Size(max = 128, message = "Payer name must be at most 128 characters")
        private String payerName;

        @NotBlank(message = "Payer ID card must not be blank")
        @Size(max = 32, message = "Payer ID card must be at most 32 characters")
        private String payerIdCard;

        @Size(max = 64, message = "Payer contact must be at most 64 characters")
        private String payerContact;

        @Size(max = 128, message = "Bank name must be at most 128 characters")
        private String bankName;

        @Size(max = 128, message = "Bank account must be at most 128 characters")
        private String bankAccount;

        @Size(max = 128, message = "Transaction ID must be at most 128 characters")
        private String transactionId;

        @Size(max = 64, message = "Receipt number must be at most 64 characters")
        private String receiptNumber;

        @Size(max = 512, message = "Receipt URL must be at most 512 characters")
        private String receiptUrl;

        @Size(max = 255, message = "Remarks must be at most 255 characters")
        private String remarks;

        public Long getFineId() {
            return fineId;
        }

        public void setFineId(Long fineId) {
            this.fineId = fineId;
        }

        public BigDecimal getPaymentAmount() {
            return paymentAmount;
        }

        public void setPaymentAmount(BigDecimal paymentAmount) {
            this.paymentAmount = paymentAmount;
        }

        public String getPaymentMethod() {
            return paymentMethod;
        }

        public void setPaymentMethod(String paymentMethod) {
            this.paymentMethod = paymentMethod;
        }

        public LocalDateTime getPaymentTime() {
            return paymentTime;
        }

        public void setPaymentTime(LocalDateTime paymentTime) {
            this.paymentTime = paymentTime;
        }

        public String getPaymentChannel() {
            return paymentChannel;
        }

        public void setPaymentChannel(String paymentChannel) {
            this.paymentChannel = paymentChannel;
        }

        public String getPayerName() {
            return payerName;
        }

        public void setPayerName(String payerName) {
            this.payerName = payerName;
        }

        public String getPayerIdCard() {
            return payerIdCard;
        }

        public void setPayerIdCard(String payerIdCard) {
            this.payerIdCard = payerIdCard;
        }

        public String getPayerContact() {
            return payerContact;
        }

        public void setPayerContact(String payerContact) {
            this.payerContact = payerContact;
        }

        public String getBankName() {
            return bankName;
        }

        public void setBankName(String bankName) {
            this.bankName = bankName;
        }

        public String getBankAccount() {
            return bankAccount;
        }

        public void setBankAccount(String bankAccount) {
            this.bankAccount = bankAccount;
        }

        public String getTransactionId() {
            return transactionId;
        }

        public void setTransactionId(String transactionId) {
            this.transactionId = transactionId;
        }

        public String getReceiptNumber() {
            return receiptNumber;
        }

        public void setReceiptNumber(String receiptNumber) {
            this.receiptNumber = receiptNumber;
        }

        public String getReceiptUrl() {
            return receiptUrl;
        }

        public void setReceiptUrl(String receiptUrl) {
            this.receiptUrl = receiptUrl;
        }

        public String getRemarks() {
            return remarks;
        }

        public void setRemarks(String remarks) {
            this.remarks = remarks;
        }
    }

    public static class CurrentUserPaymentConfirmationRequest {
        @NotBlank(message = "Transaction ID must not be blank")
        @Size(max = 128, message = "Transaction ID must be at most 128 characters")
        private String transactionId;

        @Size(max = 512, message = "Receipt URL must be at most 512 characters")
        private String receiptUrl;

        public String getTransactionId() {
            return transactionId;
        }

        public void setTransactionId(String transactionId) {
            this.transactionId = transactionId;
        }

        public String getReceiptUrl() {
            return receiptUrl;
        }

        public void setReceiptUrl(String receiptUrl) {
            this.receiptUrl = receiptUrl;
        }
    }

    public static class PaymentFinanceReviewRequest {
        @NotBlank(message = "Review result must not be blank")
        @Pattern(regexp = "(?i)APPROVED|NEED_PROOF",
                message = "Review result must be APPROVED or NEED_PROOF")
        private String reviewResult;

        @Size(max = 255, message = "Review opinion must be at most 255 characters")
        private String reviewOpinion;

        public String getReviewResult() {
            return reviewResult;
        }

        public void setReviewResult(String reviewResult) {
            this.reviewResult = reviewResult;
        }

        public String getReviewOpinion() {
            return reviewOpinion;
        }

        public void setReviewOpinion(String reviewOpinion) {
            this.reviewOpinion = reviewOpinion;
        }
    }

    public static class CurrentUserPaymentProofRequest {
        @NotBlank(message = "Receipt URL must not be blank")
        @Size(max = 512, message = "Receipt URL must be at most 512 characters")
        private String receiptUrl;

        public String getReceiptUrl() {
            return receiptUrl;
        }

        public void setReceiptUrl(String receiptUrl) {
            this.receiptUrl = receiptUrl;
        }
    }
}
