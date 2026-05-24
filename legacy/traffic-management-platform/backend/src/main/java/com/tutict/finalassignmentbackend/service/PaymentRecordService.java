package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.tutict.finalassignmentbackend.config.statemachine.events.PaymentEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.config.tenant.TenantIsolationProperties;
import com.tutict.finalassignmentbackend.config.tenant.TenantAwareSupport;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.PaymentRecordDocument;
import com.tutict.finalassignmentbackend.mapper.PaymentRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.PaymentRecordSearchRepository;
import com.tutict.finalassignmentbackend.service.statemachine.StateMachineService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class PaymentRecordService {

    private static final Logger log = Logger.getLogger(PaymentRecordService.class.getName());
    private static final String CACHE_NAME = "paymentRecordCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;
    private static final Set<String> SELF_SERVICE_PAYMENT_CHANNELS = Set.of("APP", "USER_SELF_SERVICE");
    private static final Set<String> EFFECTIVE_PAYMENT_STATUSES = Set.of(
            PaymentState.PAID.getCode(),
            PaymentState.PARTIAL.getCode(),
            "Success");
    private static final String FINANCE_REVIEW_PREFIX = "[FINANCE_REVIEW]|";
    private static final Set<String> FINANCE_REVIEW_RESULTS = Set.of("APPROVED", "NEED_PROOF");

    private final PaymentRecordMapper paymentRecordMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final PaymentRecordSearchRepository paymentRecordSearchRepository;
    private final TenantAwareSupport tenantAwareSupport;
    private final FineRecordService fineRecordService;
    private final SysUserService sysUserService;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final TransactionTemplate requiresNewTransactionTemplate;
    private final StateMachineService stateMachineService;

    @Autowired
    public PaymentRecordService(PaymentRecordMapper paymentRecordMapper,
                                SysRequestHistoryMapper sysRequestHistoryMapper,
                                PaymentRecordSearchRepository paymentRecordSearchRepository,
                                TenantAwareSupport tenantAwareSupport,
                                FineRecordService fineRecordService,
                                SysUserService sysUserService,
                                KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper,
                                PlatformTransactionManager transactionManager,
                                StateMachineService stateMachineService) {
        this.paymentRecordMapper = paymentRecordMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.paymentRecordSearchRepository = paymentRecordSearchRepository;
        this.tenantAwareSupport = tenantAwareSupport;
        this.fineRecordService = fineRecordService;
        this.sysUserService = sysUserService;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.requiresNewTransactionTemplate = new TransactionTemplate(transactionManager);
        this.requiresNewTransactionTemplate.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        this.stateMachineService = stateMachineService;
    }

    public PaymentRecordService(PaymentRecordMapper paymentRecordMapper,
                                SysRequestHistoryMapper sysRequestHistoryMapper,
                                PaymentRecordSearchRepository paymentRecordSearchRepository,
                                FineRecordService fineRecordService,
                                SysUserService sysUserService,
                                KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper,
                                PlatformTransactionManager transactionManager,
                                StateMachineService stateMachineService) {
        this(paymentRecordMapper,
                sysRequestHistoryMapper,
                paymentRecordSearchRepository,
                defaultTenantAwareSupport(),
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                objectMapper,
                transactionManager,
                stateMachineService);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "PaymentRecordService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, PaymentRecord paymentRecord, String action) {
        Objects.requireNonNull(paymentRecord, "PaymentRecord must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate payment record request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, paymentRecord, action);
        sysRequestHistoryMapper.insert(history);

        // Persist the idempotency record first, then publish the Kafka event for downstream indexing.
        sendKafkaMessage("payment_record_" + action, idempotencyKey, paymentRecord);

    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord createPaymentRecord(PaymentRecord paymentRecord) {
        FineRecord fineRecord = requireFineRecord(paymentRecord == null ? null : paymentRecord.getFineId());
        normalizeCreateManagedFields(paymentRecord, fineRecord);
        validatePaymentRecord(paymentRecord, fineRecord);
        ensureNoDuplicatePendingSelfServicePayment(paymentRecord);
        try {
            paymentRecordMapper.insert(paymentRecord);
        } catch (DuplicateKeyException ex) {
            throw translatePaymentUniquenessViolation(ex);
        }
        syncFinePaymentSummary(paymentRecord.getFineId());
        syncToIndexAfterCommit(paymentRecord);
        return paymentRecord;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord updatePaymentRecord(PaymentRecord paymentRecord) {
        throw new IllegalStateException(
                "Payment records are immutable after creation; use workflow transitions or refund operations instead");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord updatePaymentStatus(Long paymentId, PaymentState newState) {
        requirePositive(paymentId, "Payment ID");
        return persistPaymentStatusUpdate(requireExistingPaymentRecord(paymentId), newState, LocalDateTime.now());
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord transitionPaymentStatus(Long paymentId, PaymentState targetState) {
        requirePositive(paymentId, "Payment ID");
        Objects.requireNonNull(targetState, "Target payment state must not be null");
        PaymentRecord existing = requireExistingPaymentRecord(paymentId);
        PaymentState newState = resolveTransitionedPaymentState(paymentId, existing, targetState);
        return persistPaymentStatusUpdate(existing, newState, LocalDateTime.now());
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord updateSelfServicePaymentConfirmationDetails(Long paymentId,
                                                                    String transactionId,
                                                                    String receiptUrl) {
        requirePositive(paymentId, "Payment ID");
        String normalizedTransactionId = trimToNull(transactionId);
        if (normalizedTransactionId == null) {
            throw new IllegalArgumentException("Transaction ID must not be blank");
        }
        PaymentRecord existing = requireExistingPaymentRecord(paymentId);
        ensurePendingSelfServicePaymentForConfirmation(existing);
        ensureUniqueTransactionId(normalizedTransactionId, paymentId);
        ensureConfirmationTransactionConsistency(existing, normalizedTransactionId);

        LocalDateTime confirmationTime = LocalDateTime.now();
        existing.setTransactionId(normalizedTransactionId);
        existing.setReceiptUrl(trimToNull(receiptUrl));
        existing.setReceiptNumber(defaultIfBlank(existing.getReceiptNumber(), generateReferenceNumber("RCT")));
        existing.setPaymentTime(confirmationTime);
        existing.setUpdatedAt(confirmationTime);
        updatePaymentConfirmationDetailsScoped(existing, confirmationTime);
        syncToIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord confirmSelfServicePayment(Long paymentId,
                                                   String transactionId,
                                                   String receiptUrl,
                                                   PaymentState targetState) {
        requirePositive(paymentId, "Payment ID");
        Objects.requireNonNull(targetState, "Target payment state must not be null");
        if (targetState != PaymentState.PAID && targetState != PaymentState.PARTIAL) {
            throw new IllegalStateException("Self-service payment confirmation can only target paid states");
        }
        String normalizedTransactionId = trimToNull(transactionId);
        if (normalizedTransactionId == null) {
            throw new IllegalArgumentException("Transaction ID must not be blank");
        }

        PaymentRecord existing = requireExistingPaymentRecord(paymentId);
        ensurePendingSelfServicePaymentForConfirmation(existing);
        ensureUniqueTransactionId(normalizedTransactionId, paymentId);
        ensureConfirmationTransactionConsistency(existing, normalizedTransactionId);

        PaymentState newState = resolveTransitionedPaymentState(paymentId, existing, targetState);
        LocalDateTime confirmationTime = LocalDateTime.now();
        existing.setTransactionId(normalizedTransactionId);
        existing.setReceiptUrl(trimToNull(receiptUrl));
        existing.setReceiptNumber(defaultIfBlank(existing.getReceiptNumber(), generateReferenceNumber("RCT")));
        existing.setPaymentTime(confirmationTime);
        return persistSelfServiceConfirmation(existing, newState, confirmationTime);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord recordFinanceReview(Long paymentId, String reviewResult, String reviewOpinion) {
        requirePositive(paymentId, "Payment ID");
        String normalizedReviewResult = normalizeFinanceReviewResult(reviewResult);
        String normalizedReviewOpinion = normalizeFinanceReviewOpinion(reviewOpinion);
        if ("NEED_PROOF".equals(normalizedReviewResult) && normalizedReviewOpinion == null) {
            throw new IllegalArgumentException("Review opinion must not be blank when requesting more proof");
        }

        PaymentRecord existing = requireExistingPaymentRecord(paymentId);
        if (existing == null) {
            throw new IllegalStateException("PaymentRecord not found for id=" + paymentId);
        }
        if (!shouldCreateAsPendingSelfServicePayment(existing)) {
            throw new IllegalStateException("Only self-service payment records can be reviewed in this flow");
        }

        PaymentState paymentState = resolvePaymentState(existing.getPaymentStatus());
        if (paymentState != PaymentState.PAID && paymentState != PaymentState.PARTIAL) {
            throw new IllegalStateException("Only confirmed self-service payment records can be reviewed");
        }

        LocalDateTime reviewTime = LocalDateTime.now();
        String operator = defaultIfBlank(resolveOperatorName(), "system");
        existing.setRemarks(appendRemark(
                existing.getRemarks(),
                buildFinanceReviewRemark(normalizedReviewResult, operator, reviewTime, normalizedReviewOpinion)));
        existing.setUpdatedAt(reviewTime);
        existing.setUpdatedBy(operator);
        updatePaymentByIdScoped(existing);
        syncToIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public PaymentRecord updateSelfServicePaymentReceiptProof(Long paymentId, String receiptUrl) {
        requirePositive(paymentId, "Payment ID");
        return updateSelfServicePaymentReceiptProof(requireExistingPaymentRecord(paymentId), receiptUrl);
    }

    PaymentRecord updateSelfServicePaymentReceiptProof(PaymentRecord existing, String receiptUrl) {
        String normalizedReceiptUrl = trimToNull(receiptUrl);
        if (normalizedReceiptUrl == null) {
            throw new IllegalArgumentException("Receipt URL must not be blank");
        }
        if (!shouldCreateAsPendingSelfServicePayment(existing)) {
            throw new IllegalStateException("Only self-service payment records can update proof in this flow");
        }

        PaymentState paymentState = resolvePaymentState(existing.getPaymentStatus());
        if (paymentState != PaymentState.PAID && paymentState != PaymentState.PARTIAL) {
            throw new IllegalStateException("Only confirmed self-service payment records can update proof");
        }

        LocalDateTime updateTime = LocalDateTime.now();
        String operator = defaultIfBlank(resolveOperatorName(), "system");
        existing.setReceiptUrl(normalizedReceiptUrl);
        existing.setRemarks(appendRemark(existing.getRemarks(), buildUserProofUploadRemark(updateTime, normalizedReceiptUrl)));
        existing.setUpdatedAt(updateTime);
        existing.setUpdatedBy(operator);
        updatePaymentByIdScoped(existing);
        syncToIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void refundPaymentsByFineId(Long fineId, BigDecimal refundAmount, String reason) {
        try {
            requirePositive(fineId, "Fine ID");
            requireNonNegative(refundAmount, "Refund amount");
            if (refundAmount == null || refundAmount.signum() == 0) {
                return;
            }
            BigDecimal remaining = refundAmount;
            List<PaymentRecord> paymentRecords = loadRefundCandidatePayments(fineId);
            LocalDateTime refundTime = LocalDateTime.now();
            List<PaymentRecord> updatedRecords = new java.util.ArrayList<>();
            for (PaymentRecord record : paymentRecords) {
                if (record == null || !isEffectivePaymentStatus(record.getPaymentStatus())) {
                    continue;
                }
                BigDecimal refundable = resolveRefundableAmount(record);
                if (refundable.signum() <= 0) {
                    continue;
                }
                BigDecimal actualRefund = refundable.min(remaining);
                record.setRefundAmount(normalizeAmount(record.getRefundAmount()).add(actualRefund));
                record.setRefundTime(refundTime);
                record.setRemarks(appendRemark(record.getRemarks(), reason));
                record.setUpdatedAt(refundTime);
                updatePaymentByIdScoped(record);
                recordRefundAudit(record, actualRefund, reason, "PARTIAL_REFUND");
                updatedRecords.add(record);
                remaining = remaining.subtract(actualRefund);
                if (remaining.signum() <= 0) {
                    break;
                }
            }
            if (remaining.signum() > 0) {
                throw new IllegalStateException("Refund amount exceeds the refundable paid amount");
            }
            syncBatchToIndexAfterCommit(updatedRecords);
            syncFinePaymentSummary(fineId);
        } catch (Exception ex) {
            recordRefundFailureAudit(fineId, refundAmount, reason, "PARTIAL_REFUND_FAILED", ex);
            throw ex;
        }
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void waiveAndRefundPaymentsByFineId(Long fineId, String reason) {
        try {
            requirePositive(fineId, "Fine ID");
            LocalDateTime now = LocalDateTime.now();
            long pageNumber = 1L;
            while (true) {
                List<PaymentRecord> paymentRecords = loadFinePaymentBatch(fineId, pageNumber, FULL_LOAD_BATCH_SIZE);
                if (paymentRecords == null || paymentRecords.isEmpty()) {
                    break;
                }
                List<PaymentRecord> updatedBatch = new java.util.ArrayList<>();
                for (PaymentRecord record : paymentRecords) {
                    if (record == null) {
                        continue;
                    }
                    BigDecimal paidAmount = normalizeAmount(record.getPaymentAmount());
                    BigDecimal refundedAmount = normalizeAmount(record.getRefundAmount());
                    if (paidAmount.signum() > 0 && refundedAmount.compareTo(paidAmount) < 0) {
                        record.setRefundAmount(paidAmount);
                        record.setRefundTime(now);
                    }
                    record.setPaymentStatus(PaymentState.WAIVED.getCode());
                    record.setRemarks(appendRemark(record.getRemarks(), reason));
                    record.setUpdatedAt(now);
                    updatePaymentByIdScoped(record);
                    BigDecimal refundedDelta = paidAmount.subtract(refundedAmount);
                    if (refundedDelta.signum() > 0) {
                        recordRefundAudit(record, refundedDelta, reason, "WAIVE_AND_REFUND");
                    }
                    updatedBatch.add(record);
                }
                syncBatchToIndexAfterCommit(updatedBatch);
                if (paymentRecords.size() < FULL_LOAD_BATCH_SIZE) {
                    break;
                }
                pageNumber++;
            }
            syncFinePaymentSummary(fineId);
        } catch (Exception ex) {
            recordRefundFailureAudit(fineId, null, reason, "WAIVE_AND_REFUND_FAILED", ex);
            throw ex;
        }
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deletePaymentRecord(Long paymentId) {
        throw new IllegalStateException(
                "Payment records cannot be deleted manually; retain them as financial audit evidence");
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('payment', #paymentId)", unless = "#result == null")
    public PaymentRecord findById(Long paymentId) {
        requirePositive(paymentId, "Payment ID");
        if (databaseOnlyForTenantIsolation()) {
            return findPaymentByIdFromDatabase(paymentId);
        }
        return paymentRecordSearchRepository.findById(paymentId)
                .map(PaymentRecordDocument::toEntity)
                .orElseGet(() -> {
                    PaymentRecord entity = findPaymentByIdFromDatabase(paymentId);
                    if (entity != null) {
                        paymentRecordSearchRepository.save(PaymentRecordDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<PaymentRecord> findAll() {
        if (databaseOnlyForTenantIsolation()) {
            return loadAllFromDatabase();
        }
        List<PaymentRecord> fromIndex = StreamSupport.stream(paymentRecordSearchRepository.findAll().spliterator(), false)
                .map(PaymentRecordDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('page', #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> listPayments(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("updated_at")
                .orderByDesc("payment_time")
                .orderByDesc("payment_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('fine', #fineId, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> findByFineId(Long fineId, int page, int size) {
        requirePositive(fineId, "Fine ID");
        validatePagination(page, size);
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.findByFineId(fineId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("fine_id", fineId)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('finePayer', #fineId, #payerIdCard, #page, #size)",
              unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> findByFineIdAndPayerIdCard(Long fineId, String payerIdCard, int page, int size) {
        requirePositive(fineId, "Fine ID");
        if (isBlank(payerIdCard)) {
            return List.of();
        }
        validatePagination(page, size);
        String normalizedIdCard = payerIdCard.trim();
        List<PaymentRecord> index = mapHits(
                paymentRecordSearchRepository.findByFineIdAndPayerIdCard(fineId, normalizedIdCard, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("fine_id", fineId)
                .eq("payer_id_card", normalizedIdCard)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('payer', #payerIdCard, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByPayerIdCard(String payerIdCard, int page, int size) {
        if (isBlank(payerIdCard)) {
            return List.of();
        }
        validatePagination(page, size);
        String normalizedIdCard = payerIdCard.trim();
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByPayerIdCard(normalizedIdCard, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("payer_id_card", normalizedIdCard)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('status', #paymentStatus, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByPaymentStatus(String paymentStatus, int page, int size) {
        if (isBlank(paymentStatus)) {
            return List.of();
        }
        validatePagination(page, size);
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByPaymentStatus(paymentStatus, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("payment_status", paymentStatus)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('txn', #transactionId, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByTransactionId(String transactionId, int page, int size) {
        if (isBlank(transactionId)) {
            return List.of();
        }
        validatePagination(page, size);
        String normalizedTransactionId = transactionId.trim();
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByTransactionId(normalizedTransactionId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("transaction_id", normalizedTransactionId)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('number', #paymentNumber, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByPaymentNumber(String paymentNumber, int page, int size) {
        if (isBlank(paymentNumber)) {
            return List.of();
        }
        validatePagination(page, size);
        String normalizedPaymentNumber = paymentNumber.trim();
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByPaymentNumber(normalizedPaymentNumber, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("payment_number", normalizedPaymentNumber)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('payerName', #payerName, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByPayerName(String payerName, int page, int size) {
        if (isBlank(payerName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByPayerName(payerName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.likeRight("payer_name", payerName)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('method', #paymentMethod, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByPaymentMethod(String paymentMethod, int page, int size) {
        if (isBlank(paymentMethod)) {
            return List.of();
        }
        validatePagination(page, size);
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByPaymentMethod(paymentMethod, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("payment_method", paymentMethod)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('channel', #paymentChannel, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByPaymentChannel(String paymentChannel, int page, int size) {
        if (isBlank(paymentChannel)) {
            return List.of();
        }
        validatePagination(page, size);
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByPaymentChannel(paymentChannel, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("payment_channel", paymentChannel)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<Long> findIdsByPayerIdCardAndFineIds(String payerIdCard, Iterable<Long> fineIds) {
        if (isBlank(payerIdCard)) {
            return List.of();
        }
        List<Long> normalizedFineIds = normalizePositiveIds(fineIds);
        if (normalizedFineIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).select("payment_id")
                .eq("payer_id_card", payerIdCard.trim())
                .in("fine_id", normalizedFineIds)
                .orderByDesc("payment_time");
        return paymentRecordMapper.selectObjs(wrapper).stream()
                .filter(Objects::nonNull)
                .map(this::toLong)
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<PaymentRecord> listFinanceReviewTasks(int page, int size) {
        validatePagination(page, size);
        int startIndex = (page - 1) * size;
        int endExclusive = startIndex + size;
        int candidatePage = 1;
        int candidateBatchSize = Math.max(size * 3, 50);
        List<Long> matchedPaymentIds = new java.util.ArrayList<>();

        while (matchedPaymentIds.size() < endExclusive) {
            List<PaymentRecord> records = loadFinanceReviewTaskCandidateBatch(candidatePage, candidateBatchSize);
            if (records == null || records.isEmpty()) {
                break;
            }
            for (PaymentRecord record : records) {
                if (!requiresFinanceReviewTask(record)) {
                    continue;
                }
                if (record.getPaymentId() != null) {
                    matchedPaymentIds.add(record.getPaymentId());
                }
                if (matchedPaymentIds.size() >= endExclusive) {
                    break;
                }
            }
            if (records.size() < candidateBatchSize) {
                break;
            }
            candidatePage++;
        }

        if (matchedPaymentIds.size() <= startIndex) {
            return List.of();
        }
        List<Long> pagePaymentIds = matchedPaymentIds.subList(startIndex, Math.min(endExclusive, matchedPaymentIds.size()));
        return loadPaymentRecordsByIds(pagePaymentIds);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('timeRange', #startTime, #endTime, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<PaymentRecord> searchByPaymentTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<PaymentRecord> index = mapHits(paymentRecordSearchRepository.searchByPaymentTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        wrapper.between("payment_time", start, end)
                .orderByDesc("payment_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long paymentId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(paymentId);
        history.setUpdatedAt(LocalDateTime.now());
        sysRequestHistoryMapper.updateById(history);
    }

    public void markHistoryFailure(String idempotencyKey, String reason) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark failure for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("FAILED");
        history.setRequestParams(appendFailureReason(history.getRequestParams(), reason));
        history.setUpdatedAt(LocalDateTime.now());
        sysRequestHistoryMapper.updateById(history);
    }

    private SysRequestHistory buildHistory(String idempotencyKey, PaymentRecord paymentRecord, String action) {
        SysRequestHistory history = new SysRequestHistory();
        String normalizedAction = action == null ? "" : action.trim().toLowerCase();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl(resolveHistoryRequestUrl(paymentRecord, normalizedAction));
        history.setRequestParams(buildRequestParams(paymentRecord));
        history.setBusinessType(resolveHistoryBusinessType(normalizedAction));
        history.setBusinessStatus("PROCESSING");
        if (("confirm".equals(normalizedAction)
                || "review".equals(normalizedAction)
                || "proof".equals(normalizedAction)) && paymentRecord != null) {
            history.setBusinessId(paymentRecord.getPaymentId());
        }
        history.setUserId(resolveCurrentUserId());
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String resolveHistoryRequestUrl(PaymentRecord paymentRecord, String action) {
        if ("confirm".equals(action) && paymentRecord != null && paymentRecord.getPaymentId() != null) {
            return "/api/payments/me/" + paymentRecord.getPaymentId() + "/confirm";
        }
        if ("review".equals(action) && paymentRecord != null && paymentRecord.getPaymentId() != null) {
            return "/api/payments/" + paymentRecord.getPaymentId() + "/finance-review";
        }
        if ("proof".equals(action) && paymentRecord != null && paymentRecord.getPaymentId() != null) {
            return "/api/payments/me/" + paymentRecord.getPaymentId() + "/proof";
        }
        return "/api/payments";
    }

    private String resolveHistoryBusinessType(String action) {
        return switch (action) {
            case "confirm" -> "PAYMENT_CONFIRM";
            case "review" -> "PAYMENT_REVIEW";
            case "proof" -> "PAYMENT_PROOF_UPDATE";
            default -> "PAYMENT_CREATE";
        };
    }

    private String buildRequestParams(PaymentRecord paymentRecord) {
        if (paymentRecord == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "paymentId", paymentRecord.getPaymentId());
        appendParam(builder, "fineId", paymentRecord.getFineId());
        appendParam(builder, "paymentAmount", paymentRecord.getPaymentAmount());
        appendParam(builder, "paymentMethod", paymentRecord.getPaymentMethod());
        appendParam(builder, "paymentStatus", paymentRecord.getPaymentStatus());
        appendParam(builder, "paymentTime", paymentRecord.getPaymentTime());
        appendParam(builder, "payerName", paymentRecord.getPayerName());
        appendParam(builder, "transactionId", paymentRecord.getTransactionId());
        appendParam(builder, "receiptUrl", paymentRecord.getReceiptUrl());
        appendParam(builder, "remarks", paymentRecord.getRemarks());
        return truncate(builder.toString());
    }

    private void ensureUniqueTransactionId(String transactionId, Long currentPaymentId) {
        if (isBlank(transactionId)) {
            return;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("transaction_id", transactionId.trim());
        if (currentPaymentId != null) {
            wrapper.ne("payment_id", currentPaymentId);
        }
        Long duplicateCount = paymentRecordMapper.selectCount(wrapper);
        if (duplicateCount != null && duplicateCount > 0) {
            throw new IllegalStateException("Transaction ID is already used by another payment record");
        }
    }

    private void ensureNoDuplicatePendingSelfServicePayment(PaymentRecord paymentRecord) {
        if (!shouldCreateAsPendingSelfServicePayment(paymentRecord)
                || resolvePaymentState(paymentRecord.getPaymentStatus()) != PaymentState.UNPAID) {
            return;
        }
        String payerIdCard = trimToNull(paymentRecord.getPayerIdCard());
        if (paymentRecord.getFineId() == null || payerIdCard == null) {
            return;
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper)
                .eq("fine_id", paymentRecord.getFineId())
                .eq("payer_id_card", payerIdCard)
                .eq("payment_status", PaymentState.UNPAID.getCode())
                .apply("UPPER(payment_channel) IN ('APP', 'USER_SELF_SERVICE')");
        Long duplicateCount = paymentRecordMapper.selectCount(wrapper);
        if (duplicateCount != null && duplicateCount > 0) {
            throw new IllegalStateException("A pending self-service payment order already exists for this fine and payer");
        }
    }

    private void ensureConfirmationTransactionConsistency(PaymentRecord existing, String normalizedTransactionId) {
        if (existing == null || isBlank(existing.getTransactionId())) {
            return;
        }
        if (!existing.getTransactionId().trim().equals(normalizedTransactionId)) {
            throw new IllegalStateException("Transaction ID has already been set for this payment record");
        }
    }

    private IllegalStateException translatePaymentUniquenessViolation(DuplicateKeyException ex) {
        String message = ex.getMostSpecificCause() == null
                ? ex.getMessage()
                : ex.getMostSpecificCause().getMessage();
        String normalizedMessage = message == null ? "" : message.toLowerCase();
        if (normalizedMessage.contains("transaction")) {
            return new IllegalStateException("Transaction ID is already used by another payment record", ex);
        }
        if (normalizedMessage.contains("pending_self_service")
                || normalizedMessage.contains("active_pending_self_service")) {
            return new IllegalStateException(
                    "A pending self-service payment order already exists for this fine and payer",
                    ex);
        }
        return new IllegalStateException("Payment record violates uniqueness constraints", ex);
    }

    private void appendParam(StringBuilder builder, String key, Object value) {
        if (builder == null || value == null) {
            return;
        }
        String normalized = value.toString().trim();
        if (normalized.isEmpty()) {
            return;
        }
        if (!builder.isEmpty()) {
            builder.append(',');
        }
        builder.append(key).append('=').append(normalized);
    }

    private String appendFailureReason(String existing, String reason) {
        String normalizedReason = truncate(reason);
        if (isBlank(normalizedReason)) {
            return existing;
        }
        if (isBlank(existing)) {
            return "failure=" + normalizedReason;
        }
        return truncate(existing + ",failure=" + normalizedReason);
    }

    // Refresh the Elasticsearch document after the transaction commits so search reads the latest state.
    private void syncToIndexAfterCommit(PaymentRecord paymentRecord) {
        if (databaseOnlyForTenantIsolation() || paymentRecord == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            PaymentRecordDocument doc = PaymentRecordDocument.fromEntity(paymentRecord);
            if (doc != null) {
                paymentRecordSearchRepository.save(doc);
            }
        });
    }

    private List<PaymentRecord> fetchFromDatabase(QueryWrapper<PaymentRecord> wrapper, int page, int size) {
        tenantScope(wrapper);
        Page<PaymentRecord> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        paymentRecordMapper.selectPage(mpPage, wrapper);
        List<PaymentRecord> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private void sendKafkaMessage(String topic, String idempotencyKey, PaymentRecord paymentRecord) {
        try {
            String payload = objectMapper.writeValueAsString(paymentRecord);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send PaymentRecord Kafka message", ex);
            throw new RuntimeException("Failed to send PaymentRecord event", ex);
        }
    }

    private void syncFinePaymentSummary(Long fineId) {
        if (fineId == null) {
            return;
        }
        FineRecord fineRecord = fineRecordService.findById(fineId);
        if (fineRecord == null) {
            throw new IllegalStateException("Fine record not found for id=" + fineId);
        }

        List<PaymentRecord> paymentRecords = loadPaymentSummaryRecords(fineId);

        BigDecimal totalAmount = normalizeAmount(resolveFineTotalAmount(fineRecord));
        BigDecimal paidAmount = BigDecimal.ZERO;
        boolean waived = false;
        for (PaymentRecord record : paymentRecords) {
            if (record == null) {
                continue;
            }
            if (isWaivedStatus(record.getPaymentStatus())) {
                waived = true;
            }
            if (isEffectivePaymentStatus(record.getPaymentStatus())) {
                paidAmount = paidAmount.add(resolveNetPaidAmount(record));
            }
        }

        BigDecimal unpaidAmount = totalAmount.subtract(paidAmount);
        if (unpaidAmount.signum() < 0) {
            unpaidAmount = BigDecimal.ZERO;
        }

        fineRecord.setTotalAmount(totalAmount);
        fineRecord.setPaidAmount(paidAmount);
        fineRecord.setUnpaidAmount(waived ? BigDecimal.ZERO : unpaidAmount);
        fineRecord.setPaymentStatus(resolveFinePaymentStatus(fineRecord, totalAmount, paidAmount, waived));
        fineRecord.setUpdatedAt(LocalDateTime.now());
        fineRecordService.updateFineRecordSystemManaged(fineRecord);
    }

    private BigDecimal resolveFineTotalAmount(FineRecord fineRecord) {
        if (fineRecord == null) {
            return BigDecimal.ZERO;
        }
        if (fineRecord.getTotalAmount() != null) {
            return fineRecord.getTotalAmount();
        }
        return normalizeAmount(fineRecord.getFineAmount()).add(normalizeAmount(fineRecord.getLateFee()));
    }

    private String resolveFinePaymentStatus(FineRecord fineRecord,
                                            BigDecimal totalAmount,
                                            BigDecimal paidAmount,
                                            boolean waived) {
        if (waived) {
            return PaymentState.WAIVED.getCode();
        }
        if (totalAmount.signum() <= 0 || paidAmount.compareTo(totalAmount) >= 0) {
            return PaymentState.PAID.getCode();
        }
        if (paidAmount.signum() > 0) {
            return PaymentState.PARTIAL.getCode();
        }
        if (fineRecord.getPaymentDeadline() != null
                && fineRecord.getPaymentDeadline().isBefore(LocalDateTime.now().toLocalDate())) {
            return PaymentState.OVERDUE.getCode();
        }
        return PaymentState.UNPAID.getCode();
    }

    private boolean isEffectivePaymentStatus(String status) {
        if (isBlank(status)) {
            return false;
        }
        String normalized = status.trim();
        return EFFECTIVE_PAYMENT_STATUSES.stream().anyMatch(candidate -> candidate.equalsIgnoreCase(normalized));
    }

    private boolean isWaivedStatus(String status) {
        return !isBlank(status) && PaymentState.WAIVED.getCode().equalsIgnoreCase(status.trim());
    }

    private BigDecimal normalizeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }

    private BigDecimal resolveNetPaidAmount(PaymentRecord record) {
        if (record == null) {
            return BigDecimal.ZERO;
        }
        BigDecimal netPaid = normalizeAmount(record.getPaymentAmount())
                .subtract(normalizeAmount(record.getRefundAmount()));
        return netPaid.signum() < 0 ? BigDecimal.ZERO : netPaid;
    }

    private BigDecimal resolveRefundableAmount(PaymentRecord record) {
        return resolveNetPaidAmount(record);
    }

    private void validatePaymentRecord(PaymentRecord paymentRecord) {
        validatePaymentRecord(paymentRecord, null);
    }

    private void validatePaymentRecord(PaymentRecord paymentRecord, FineRecord fineRecord) {
        Objects.requireNonNull(paymentRecord, "PaymentRecord must not be null");
        requirePositive(paymentRecord.getFineId(), "Fine ID");
        FineRecord existingFineRecord = fineRecord != null ? fineRecord : requireFineRecord(paymentRecord.getFineId());
        if (paymentRecord.getPaymentId() != null) {
            PaymentRecord existing = findPaymentByIdFromDatabase(paymentRecord.getPaymentId());
            if (existing != null
                    && existing.getFineId() != null
                    && !Objects.equals(existing.getFineId(), paymentRecord.getFineId())) {
                throw new IllegalArgumentException("Fine ID cannot be changed for an existing payment record");
            }
        }
        if (paymentRecord.getPaymentTime() == null) {
            paymentRecord.setPaymentTime(LocalDateTime.now());
        }
        if (paymentRecord.getPaymentStatus() == null || paymentRecord.getPaymentStatus().isBlank()) {
            paymentRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        }
        if (paymentRecord.getPaymentAmount() == null || paymentRecord.getPaymentAmount().signum() <= 0) {
            throw new IllegalArgumentException("Payment amount must be greater than zero");
        }
        requireNonBlank(paymentRecord.getPayerName(), "Payer name");
        requireNonBlank(paymentRecord.getPayerIdCard(), "Payer ID card");
        requireNonNegative(paymentRecord.getPaymentAmount(), "Payment amount");
        requireNonNegative(paymentRecord.getRefundAmount(), "Refund amount");
        if (paymentRecord.getRefundAmount() != null
                && paymentRecord.getPaymentAmount() != null
                && paymentRecord.getRefundAmount().compareTo(paymentRecord.getPaymentAmount()) > 0) {
            throw new IllegalArgumentException("Refund amount cannot exceed payment amount");
        }
        validateOutstandingAmount(paymentRecord, existingFineRecord);
        if (isEffectivePaymentStatus(paymentRecord.getPaymentStatus())
                && (paymentRecord.getPaymentAmount() == null || paymentRecord.getPaymentAmount().signum() <= 0)) {
            throw new IllegalArgumentException("Effective payment records must have a positive payment amount");
        }
        validatePaymentStateConsistency(paymentRecord, resolvePaymentState(paymentRecord.getPaymentStatus()));
    }

    private void normalizeCreateManagedFields(PaymentRecord paymentRecord, FineRecord fineRecord) {
        if (paymentRecord == null) {
            return;
        }
        paymentRecord.setPaymentId(null);
        paymentRecord.setPaymentNumber(defaultIfBlank(paymentRecord.getPaymentNumber(), generateReferenceNumber("PAY")));
        if (shouldCreateAsPendingSelfServicePayment(paymentRecord)) {
            paymentRecord.setReceiptNumber(null);
            paymentRecord.setTransactionId(null);
        } else {
            paymentRecord.setReceiptNumber(defaultIfBlank(paymentRecord.getReceiptNumber(), generateReferenceNumber("RCT")));
            paymentRecord.setTransactionId(defaultIfBlank(paymentRecord.getTransactionId(), generateReferenceNumber("TXN")));
        }
        paymentRecord.setRefundAmount(BigDecimal.ZERO);
        paymentRecord.setRefundTime(null);
        paymentRecord.setPaymentStatus(defaultPaymentStateForCreate(paymentRecord, fineRecord).getCode());
    }

    private void preserveManagedFieldsForManualUpdate(PaymentRecord paymentRecord, PaymentRecord existing) {
        if (paymentRecord == null || existing == null) {
            return;
        }
        paymentRecord.setPaymentStatus(existing.getPaymentStatus());
        paymentRecord.setRefundAmount(existing.getRefundAmount());
        paymentRecord.setRefundTime(existing.getRefundTime());
    }

    private PaymentState defaultPaymentStateForCreate(PaymentRecord paymentRecord, FineRecord fineRecord) {
        if (paymentRecord == null) {
            return PaymentState.UNPAID;
        }
        if (shouldCreateAsPendingSelfServicePayment(paymentRecord)) {
            return PaymentState.UNPAID;
        }
        FineRecord existingFineRecord = fineRecord;
        if (existingFineRecord == null && paymentRecord.getFineId() != null) {
            existingFineRecord = fineRecordService.findById(paymentRecord.getFineId());
        }
        if (existingFineRecord == null) {
            return resolveNetPaidAmount(paymentRecord).signum() > 0 ? PaymentState.PAID : PaymentState.UNPAID;
        }
        BigDecimal totalAmount = normalizeAmount(resolveFineTotalAmount(existingFineRecord));
        BigDecimal alreadyPaidAmount = normalizeAmount(existingFineRecord.getPaidAmount());
        BigDecimal paymentAmount = resolveNetPaidAmount(paymentRecord);
        BigDecimal projectedPaidAmount = alreadyPaidAmount.add(paymentAmount);
        if (totalAmount.signum() <= 0 || projectedPaidAmount.compareTo(totalAmount) >= 0) {
            return PaymentState.PAID;
        }
        if (paymentAmount.signum() > 0) {
            return PaymentState.PARTIAL;
        }
        if (existingFineRecord.getPaymentDeadline() != null
                && existingFineRecord.getPaymentDeadline().isBefore(LocalDateTime.now().toLocalDate())) {
            return PaymentState.OVERDUE;
        }
        return PaymentState.UNPAID;
    }

    private void validatePaymentStateConsistency(PaymentRecord paymentRecord, PaymentState targetState) {
        if (paymentRecord == null || targetState == null) {
            return;
        }
        BigDecimal netPaidAmount = resolveNetPaidAmount(paymentRecord);
        switch (targetState) {
            case PAID, PARTIAL -> {
                if (netPaidAmount.signum() <= 0) {
                    throw new IllegalStateException("Paid or partial payment states require a positive net paid amount");
                }
            }
            case UNPAID, OVERDUE -> {
                if (netPaidAmount.signum() > 0
                        && !(targetState == PaymentState.UNPAID && shouldCreateAsPendingSelfServicePayment(paymentRecord))) {
                    throw new IllegalStateException("Unpaid or overdue payment states cannot keep a positive net paid amount");
                }
            }
            case WAIVED -> {
            }
        }
    }

    private boolean shouldCreateAsPendingSelfServicePayment(PaymentRecord paymentRecord) {
        if (paymentRecord == null) {
            return false;
        }
        String paymentChannel = paymentRecord.getPaymentChannel();
        if (isBlank(paymentChannel)) {
            return false;
        }
        return SELF_SERVICE_PAYMENT_CHANNELS.contains(paymentChannel.trim().toUpperCase());
    }

    private PaymentState resolvePaymentState(String code) {
        PaymentState state = PaymentState.fromCode(code);
        return state != null ? state : PaymentState.UNPAID;
    }

    private PaymentRecord requireExistingPaymentRecord(Long paymentId) {
        PaymentRecord existing = findPaymentByIdFromDatabase(paymentId);
        if (existing == null) {
            throw new IllegalStateException("PaymentRecord not found for id=" + paymentId);
        }
        return existing;
    }

    private void ensurePendingSelfServicePaymentForConfirmation(PaymentRecord existing) {
        if (!shouldCreateAsPendingSelfServicePayment(existing)) {
            throw new IllegalStateException("Only self-service payment orders can accept confirmation details");
        }
        if (!Objects.equals(resolvePaymentState(existing.getPaymentStatus()), PaymentState.UNPAID)) {
            throw new IllegalStateException("Only pending self-service payment orders can accept confirmation details");
        }
    }

    private PaymentState resolveTransitionedPaymentState(Long paymentId,
                                                         PaymentRecord existing,
                                                         PaymentState targetState) {
        if (targetState == PaymentState.WAIVED) {
            throw new IllegalStateException(
                    "Manual payment waivers are not supported; use the fine waiver/refund workflow instead");
        }
        PaymentState currentState = resolvePaymentState(existing == null ? null : existing.getPaymentStatus());
        if (currentState == targetState) {
            validatePaymentStateConsistency(existing, targetState);
            return targetState;
        }

        PaymentEvent event = resolveTransitionEvent(currentState, targetState);
        if (event == null || !stateMachineService.canTransitionPaymentState(currentState, event)) {
            throw new IllegalStateException("Payment state transition is not allowed");
        }

        PaymentState newState = stateMachineService.processPaymentState(paymentId, currentState, event);
        if (newState != targetState) {
            throw new IllegalStateException("Payment state did not transition to the expected target state");
        }
        return newState;
    }

    private PaymentRecord persistPaymentStatusUpdate(PaymentRecord existing,
                                                     PaymentState newState,
                                                     LocalDateTime updateTime) {
        PaymentState effectiveState = newState != null ? newState : resolvePaymentState(existing == null
                ? null
                : existing.getPaymentStatus());
        validatePaymentStateConsistency(existing, effectiveState);
        existing.setPaymentStatus(effectiveState.getCode());
        existing.setUpdatedAt(updateTime == null ? LocalDateTime.now() : updateTime);
        updatePaymentByIdScoped(existing);
        syncFinePaymentSummary(existing.getFineId());
        syncToIndexAfterCommit(existing);
        return existing;
    }

    private PaymentRecord persistSelfServiceConfirmation(PaymentRecord existing,
                                                         PaymentState newState,
                                                         LocalDateTime updateTime) {
        PaymentState effectiveState = newState != null ? newState : resolvePaymentState(existing == null
                ? null
                : existing.getPaymentStatus());
        validatePaymentStateConsistency(existing, effectiveState);
        existing.setPaymentStatus(effectiveState.getCode());
        existing.setUpdatedAt(updateTime == null ? LocalDateTime.now() : updateTime);
        updateSelfServiceConfirmationScoped(existing);
        syncFinePaymentSummary(existing.getFineId());
        syncToIndexAfterCommit(existing);
        return existing;
    }

    private FineRecord requireFineRecord(Long fineId) {
        requirePositive(fineId, "Fine ID");
        FineRecord fineRecord = fineRecordService.findById(fineId);
        if (fineRecord == null) {
            throw new IllegalArgumentException("Fine record does not exist");
        }
        return fineRecord;
    }

    private void validateOutstandingAmount(PaymentRecord paymentRecord, FineRecord fineRecord) {
        if (paymentRecord == null || fineRecord == null) {
            return;
        }
        if (isWaivedStatus(fineRecord.getPaymentStatus())) {
            throw new IllegalStateException("Waived fines cannot accept new payments");
        }
        BigDecimal remainingPayableAmount = remainingPayableAmount(fineRecord);
        if (remainingPayableAmount.signum() <= 0) {
            throw new IllegalStateException("Fine is already fully paid");
        }
        BigDecimal paymentAmount = normalizeAmount(paymentRecord.getPaymentAmount());
        if (paymentAmount.compareTo(remainingPayableAmount) > 0) {
            throw new IllegalArgumentException("Payment amount exceeds the remaining payable amount");
        }
    }

    private BigDecimal remainingPayableAmount(FineRecord fineRecord) {
        if (fineRecord == null) {
            return BigDecimal.ZERO;
        }
        BigDecimal remaining = normalizeAmount(resolveFineTotalAmount(fineRecord))
                .subtract(normalizeAmount(fineRecord.getPaidAmount()));
        return remaining.signum() < 0 ? BigDecimal.ZERO : remaining;
    }

    private String defaultIfBlank(String value, String fallback) {
        return isBlank(value) ? fallback : value.trim();
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private String generateReferenceNumber(String prefix) {
        String normalizedPrefix = isBlank(prefix) ? "REF" : prefix.trim().toUpperCase();
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        String suffix = UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
        return normalizedPrefix + "-" + timestamp + "-" + suffix;
    }

    private PaymentEvent resolveTransitionEvent(PaymentState currentState, PaymentState targetState) {
        if (currentState == null || targetState == null) {
            return null;
        }
        return switch (currentState) {
            case UNPAID -> switch (targetState) {
                case PARTIAL -> PaymentEvent.PARTIAL_PAY;
                case PAID -> PaymentEvent.COMPLETE_PAYMENT;
                case OVERDUE -> PaymentEvent.MARK_OVERDUE;
                case WAIVED -> PaymentEvent.WAIVE_FINE;
                default -> null;
            };
            case PARTIAL -> switch (targetState) {
                case PAID -> PaymentEvent.CONTINUE_PAYMENT;
                case OVERDUE -> PaymentEvent.MARK_OVERDUE;
                case WAIVED -> PaymentEvent.WAIVE_FINE;
                default -> null;
            };
            case OVERDUE -> switch (targetState) {
                case PAID -> PaymentEvent.COMPLETE_PAYMENT;
                case WAIVED -> PaymentEvent.WAIVE_FINE;
                default -> null;
            };
            case PAID -> targetState == PaymentState.WAIVED ? PaymentEvent.WAIVE_FINE : null;
            case WAIVED -> null;
        };
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private List<Long> normalizePositiveIds(Iterable<Long> ids) {
        return ids == null
                ? List.of()
                : StreamSupport.stream(ids.spliterator(), false)
                .filter(Objects::nonNull)
                .filter(id -> id > 0)
                .distinct()
                .collect(Collectors.toList());
    }

    private Long toLong(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value instanceof String text) {
            try {
                return Long.parseLong(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    private void requirePositive(Number number, String fieldName) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException(fieldName + " must be greater than zero");
        }
    }

    private void requireNonBlank(String value, String fieldName) {
        if (isBlank(value)) {
            throw new IllegalArgumentException(fieldName + " must not be blank");
        }
    }

    private void requireNonNegative(BigDecimal number, String fieldName) {
        if (number != null && number.signum() < 0) {
            throw new IllegalArgumentException(fieldName + " must not be negative");
        }
    }

    private LocalDateTime parseDateTime(String value, String fieldName) {
        if (isBlank(value)) {
            return null;
        }
        try {
            return LocalDateTime.parse(value);
        } catch (DateTimeParseException ex) {
            log.log(Level.WARNING, "Failed to parse " + fieldName + ": " + value, ex);
            return null;
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String truncate(String value) {
        if (value == null) {
            return null;
        }
        return value.length() <= 500 ? value : value.substring(0, 500);
    }

    private String appendRemark(String existing, String addition) {
        String suffix = truncate(addition);
        if (isBlank(suffix)) {
            return existing;
        }
        if (isBlank(existing)) {
            return suffix;
        }
        return truncate(existing + "; " + suffix);
    }

    private String normalizeFinanceReviewResult(String reviewResult) {
        if (isBlank(reviewResult)) {
            throw new IllegalArgumentException("Review result must not be blank");
        }
        String normalized = reviewResult.trim().toUpperCase();
        if (!FINANCE_REVIEW_RESULTS.contains(normalized)) {
            throw new IllegalArgumentException("Unsupported finance review result: " + reviewResult);
        }
        return normalized;
    }

    private String normalizeFinanceReviewOpinion(String reviewOpinion) {
        String normalized = trimToNull(reviewOpinion);
        if (normalized == null) {
            return null;
        }
        normalized = normalized.replace('|', '/').replace(';', ' ');
        normalized = normalized.replace('\r', ' ').replace('\n', ' ').trim();
        return normalized.isEmpty() ? null : truncate(normalized);
    }

    private String buildFinanceReviewRemark(String reviewResult,
                                            String reviewer,
                                            LocalDateTime reviewTime,
                                            String reviewOpinion) {
        String normalizedReviewer = defaultIfBlank(reviewer, "system");
        String normalizedTime = reviewTime == null ? LocalDateTime.now().toString() : reviewTime.toString();
        String normalizedOpinion = reviewOpinion == null ? "" : reviewOpinion;
        return FINANCE_REVIEW_PREFIX
                + reviewResult
                + "|"
                + normalizedReviewer
                + "|"
                + normalizedTime
                + "|"
                + normalizedOpinion;
    }

    private boolean requiresFinanceReviewTask(PaymentRecord paymentRecord) {
        if (paymentRecord == null || !shouldCreateAsPendingSelfServicePayment(paymentRecord)) {
            return false;
        }
        PaymentState paymentState = resolvePaymentState(paymentRecord.getPaymentStatus());
        if (paymentState != PaymentState.PAID && paymentState != PaymentState.PARTIAL) {
            return false;
        }
        String latestReviewResult = extractLatestFinanceReviewResult(paymentRecord.getRemarks());
        return latestReviewResult == null || "NEED_PROOF".equals(latestReviewResult);
    }

    private String extractLatestFinanceReviewResult(String remarks) {
        if (isBlank(remarks)) {
            return null;
        }
        String[] segments = remarks.split(";");
        for (int index = segments.length - 1; index >= 0; index--) {
            String segment = trimToNull(segments[index]);
            if (segment == null || !segment.startsWith(FINANCE_REVIEW_PREFIX)) {
                continue;
            }
            String payload = segment.substring(FINANCE_REVIEW_PREFIX.length());
            int separatorIndex = payload.indexOf('|');
            String result = separatorIndex >= 0 ? payload.substring(0, separatorIndex) : payload;
            result = trimToNull(result);
            return result == null ? null : result.toUpperCase();
        }
        return null;
    }

    private List<PaymentRecord> loadFinanceReviewTaskCandidateBatch(int page, int size) {
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).select("payment_id", "payment_channel", "payment_status", "remarks", "updated_at", "payment_time")
                .in("payment_channel", SELF_SERVICE_PAYMENT_CHANNELS)
                .in("payment_status", PaymentState.PAID.getCode(), PaymentState.PARTIAL.getCode())
                // Exclude records that have already been approved and never requested more proof.
                // Rows with mixed finance-review history still flow through the exact in-memory check.
                .and(candidate -> candidate.isNull("remarks")
                        .or()
                        .eq("remarks", "")
                        .or()
                        .notLike("remarks", FINANCE_REVIEW_PREFIX + "APPROVED|")
                        .or()
                        .like("remarks", FINANCE_REVIEW_PREFIX + "NEED_PROOF|"))
                .orderByDesc("updated_at")
                .orderByDesc("payment_time")
                .orderByDesc("payment_id");
        Page<PaymentRecord> candidatePageResult = paymentRecordMapper.selectPage(
                new Page<>(Math.max(page, 1), Math.max(size, 1)),
                wrapper);
        return candidatePageResult.getRecords();
    }

    private List<PaymentRecord> loadPaymentRecordsByIds(List<Long> paymentIds) {
        if (paymentIds == null || paymentIds.isEmpty()) {
            return List.of();
        }
        List<PaymentRecord> records;
        if (databaseOnlyForTenantIsolation()) {
            QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
            tenantScope(wrapper).in("payment_id", paymentIds);
            records = paymentRecordMapper.selectList(wrapper);
        } else {
            records = paymentRecordMapper.selectBatchIds(paymentIds);
        }
        if (records == null || records.isEmpty()) {
            return List.of();
        }
        java.util.Map<Long, PaymentRecord> indexedRecords = records.stream()
                .filter(Objects::nonNull)
                .filter(record -> record.getPaymentId() != null)
                .collect(Collectors.toMap(PaymentRecord::getPaymentId, record -> record, (left, right) -> left));
        return paymentIds.stream()
                .map(indexedRecords::get)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
    }

    private List<PaymentRecord> loadRefundCandidatePayments(Long fineId) {
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("fine_id", fineId)
                .in("payment_status", EFFECTIVE_PAYMENT_STATUSES)
                .orderByDesc("payment_time")
                .orderByDesc("payment_id");
        return paymentRecordMapper.selectList(wrapper);
    }

    private List<PaymentRecord> loadFinePaymentBatch(Long fineId, long pageNumber, int batchSize) {
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("fine_id", fineId)
                .orderByAsc("payment_id");
        Page<PaymentRecord> batchPage = new Page<>(Math.max(pageNumber, 1L), Math.max(batchSize, 1));
        paymentRecordMapper.selectPage(batchPage, wrapper);
        return batchPage.getRecords();
    }

    private List<PaymentRecord> loadPaymentSummaryRecords(Long fineId) {
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).select("payment_id", "payment_status", "payment_amount", "refund_amount")
                .eq("fine_id", fineId)
                .orderByDesc("payment_time")
                .orderByDesc("payment_id");
        return paymentRecordMapper.selectList(wrapper);
    }

    private String buildUserProofUploadRemark(LocalDateTime updateTime, String receiptUrl) {
        String normalizedTime = updateTime == null ? LocalDateTime.now().toString() : updateTime.toString();
        return "[USER_PROOF_UPLOAD]|" + normalizedTime + "|" + truncate(receiptUrl);
    }

    private void recordRefundAudit(PaymentRecord record, BigDecimal refundAmount, String reason, String businessType) {
        if (record == null || refundAmount == null || refundAmount.signum() <= 0) {
            return;
        }
        persistRefundAudit(buildRefundAuditHistory(
                record.getPaymentId(),
                record.getFineId(),
                refundAmount,
                reason,
                businessType,
                "SUCCESS",
                null));
    }

    private void recordRefundFailureAudit(Long fineId,
                                          BigDecimal refundAmount,
                                          String reason,
                                          String businessType,
                                          Exception ex) {
        persistRefundAudit(buildRefundAuditHistory(
                null,
                fineId,
                refundAmount,
                reason,
                businessType,
                "FAILED",
                ex == null ? null : ex.getMessage()));
    }

    private SysRequestHistory buildRefundAuditHistory(Long paymentId,
                                                      Long fineId,
                                                      BigDecimal refundAmount,
                                                      String reason,
                                                      String businessType,
                                                      String businessStatus,
                                                      String failureMessage) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey("refund-" + UUID.randomUUID());
        history.setRequestMethod("SYSTEM");
        history.setRequestUrl(paymentId == null
                ? "/api/payments/refunds/auto"
                : "/api/payments/" + paymentId + "/refund");
        history.setRequestParams(truncate(buildRefundAuditParams(paymentId, fineId, refundAmount, reason, failureMessage)));
        history.setBusinessType(businessType);
        history.setBusinessId(paymentId);
        history.setBusinessStatus(businessStatus);
        history.setUserId(resolveCurrentUserId());
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private void persistRefundAudit(SysRequestHistory history) {
        if (history == null) {
            return;
        }
        try {
            requiresNewTransactionTemplate.executeWithoutResult(status ->
                    sysRequestHistoryMapper.insert(history));
        } catch (Exception auditEx) {
            log.log(Level.WARNING, "Failed to persist refund audit history", auditEx);
        }
    }

    private String buildRefundAuditParams(Long paymentId,
                                          Long fineId,
                                          BigDecimal refundAmount,
                                          String reason,
                                          String failureMessage) {
        String operator = resolveOperatorName();
        return "fineId=" + fineId
                + ",paymentId=" + paymentId
                + ",refundAmount=" + refundAmount
                + ",operator=" + (operator == null ? "SYSTEM" : operator)
                + ",failure=" + truncate(failureMessage)
                + ",reason=" + truncate(reason);
    }

    private String resolveOperatorName() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken
                || authentication.getName() == null
                || authentication.getName().isBlank()) {
            return null;
        }
        return authentication.getName();
    }

    private Long resolveCurrentUserId() {
        String operator = resolveOperatorName();
        if (isBlank(operator)) {
            return null;
        }
        SysUser user = sysUserService.findByUsername(operator);
        return user == null ? null : user.getUserId();
    }

    private String resolveRequestIp() {
        RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
        if (!(requestAttributes instanceof ServletRequestAttributes servletRequestAttributes)) {
            return null;
        }
        HttpServletRequest request = servletRequestAttributes.getRequest();
        if (request == null) {
            return null;
        }

        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (!isBlank(forwardedFor)) {
            return forwardedFor.split(",")[0].trim();
        }
        String realIp = request.getHeader("X-Real-IP");
        if (!isBlank(realIp)) {
            return realIp.trim();
        }
        String remoteAddr = request.getRemoteAddr();
        return isBlank(remoteAddr) ? null : remoteAddr.trim();
    }

    private void syncBatchToIndexAfterCommit(List<PaymentRecord> records) {
        if (databaseOnlyForTenantIsolation() || records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<PaymentRecordDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(PaymentRecordDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                paymentRecordSearchRepository.saveAll(documents);
            }
        });
    }

    private void runAfterCommitOrNow(Runnable task) {
        if (task == null) {
            return;
        }
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    task.run();
                }
            });
            return;
        }
        task.run();
    }

    private List<PaymentRecord> mapHits(org.springframework.data.elasticsearch.core.SearchHits<PaymentRecordDocument> hits) {
        if (databaseOnlyForTenantIsolation()) {
            return List.of();
        }
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(PaymentRecordDocument::toEntity)
                .collect(Collectors.toList());
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private List<PaymentRecord> loadAllFromDatabase() {
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).orderByAsc("payment_id");

        List<PaymentRecord> allRecords = new java.util.ArrayList<>();
        long pageNumber = 1L;
        while (true) {
            Page<PaymentRecord> batchPage = new Page<>(pageNumber, FULL_LOAD_BATCH_SIZE);
            paymentRecordMapper.selectPage(batchPage, wrapper);
            List<PaymentRecord> records = batchPage.getRecords();
            if (records == null || records.isEmpty()) {
                break;
            }
            allRecords.addAll(records);
            syncBatchToIndexAfterCommit(records);
            if (records.size() < FULL_LOAD_BATCH_SIZE) {
                break;
            }
            pageNumber++;
        }
        return allRecords;
    }

    private boolean databaseOnlyForTenantIsolation() {
        return tenantAwareSupport.isIsolationEnabled();
    }

    private <T> QueryWrapper<T> tenantScope(QueryWrapper<T> wrapper) {
        return tenantAwareSupport.applyTenantScope(wrapper);
    }

    private <T> UpdateWrapper<T> tenantScope(UpdateWrapper<T> wrapper) {
        if (wrapper == null || !databaseOnlyForTenantIsolation()) {
            return wrapper;
        }
        String tenantId = tenantAwareSupport.currentTenantId();
        if (!isBlank(tenantId)) {
            wrapper.eq("tenant_id", tenantId.trim());
        }
        return wrapper;
    }

    private PaymentRecord findPaymentByIdFromDatabase(Long paymentId) {
        if (paymentId == null) {
            return null;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return paymentRecordMapper.selectById(paymentId);
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("payment_id", paymentId).last("limit 1");
        return paymentRecordMapper.selectOne(wrapper);
    }

    private int updatePaymentByIdScoped(PaymentRecord paymentRecord) {
        if (paymentRecord == null || paymentRecord.getPaymentId() == null) {
            return 0;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return paymentRecordMapper.updateById(paymentRecord);
        }
        QueryWrapper<PaymentRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("payment_id", paymentRecord.getPaymentId());
        return paymentRecordMapper.update(paymentRecord, wrapper);
    }

    private void updatePaymentConfirmationDetailsScoped(PaymentRecord paymentRecord, LocalDateTime updateTime) {
        if (paymentRecord == null || paymentRecord.getPaymentId() == null) {
            return;
        }
        PaymentRecord update = new PaymentRecord();
        update.setTransactionId(paymentRecord.getTransactionId());
        update.setReceiptUrl(paymentRecord.getReceiptUrl());
        update.setReceiptNumber(paymentRecord.getReceiptNumber());
        update.setPaymentTime(paymentRecord.getPaymentTime());
        update.setUpdatedAt(updateTime == null ? LocalDateTime.now() : updateTime);

        UpdateWrapper<PaymentRecord> wrapper = new UpdateWrapper<>();
        tenantScope(wrapper)
                .eq("payment_id", paymentRecord.getPaymentId())
                .eq("payment_status", PaymentState.UNPAID.getCode())
                .isNull("transaction_id");
        int updatedRows;
        try {
            updatedRows = paymentRecordMapper.update(update, wrapper);
        } catch (DuplicateKeyException ex) {
            throw translatePaymentUniquenessViolation(ex);
        }
        if (updatedRows <= 0) {
            throw new IllegalStateException(
                    "Only pending self-service payment orders without confirmation details can accept confirmation details");
        }
    }

    private void updateSelfServiceConfirmationScoped(PaymentRecord paymentRecord) {
        if (paymentRecord == null || paymentRecord.getPaymentId() == null) {
            return;
        }
        PaymentRecord update = new PaymentRecord();
        update.setTransactionId(paymentRecord.getTransactionId());
        update.setReceiptUrl(paymentRecord.getReceiptUrl());
        update.setReceiptNumber(paymentRecord.getReceiptNumber());
        update.setPaymentTime(paymentRecord.getPaymentTime());
        update.setPaymentStatus(paymentRecord.getPaymentStatus());
        update.setUpdatedAt(paymentRecord.getUpdatedAt());

        UpdateWrapper<PaymentRecord> wrapper = new UpdateWrapper<>();
        tenantScope(wrapper)
                .eq("payment_id", paymentRecord.getPaymentId())
                .eq("payment_status", PaymentState.UNPAID.getCode());
        int updatedRows;
        try {
            updatedRows = paymentRecordMapper.update(update, wrapper);
        } catch (DuplicateKeyException ex) {
            throw translatePaymentUniquenessViolation(ex);
        }
        if (updatedRows <= 0) {
            throw new IllegalStateException("Only pending self-service payment orders can be confirmed");
        }
    }

    private static TenantAwareSupport defaultTenantAwareSupport() {
        ProductGovernanceProperties productGovernanceProperties = new ProductGovernanceProperties();
        productGovernanceProperties.setTenantIsolationEnabled(false);
        return new TenantAwareSupport(productGovernanceProperties, new TenantIsolationProperties());
    }
}
