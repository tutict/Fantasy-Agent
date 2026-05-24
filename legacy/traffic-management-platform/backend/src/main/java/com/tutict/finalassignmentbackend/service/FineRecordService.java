package com.tutict.finalassignmentbackend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.config.tenant.TenantIsolationProperties;
import com.tutict.finalassignmentbackend.config.tenant.TenantAwareSupport;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.FineRecordDocument;
import com.tutict.finalassignmentbackend.mapper.FineRecordMapper;
import com.tutict.finalassignmentbackend.mapper.PaymentRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.FineRecordSearchRepository;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class FineRecordService {

    private static final Logger log = Logger.getLogger(FineRecordService.class.getName());
    private static final String CACHE_NAME = "fineRecordCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final FineRecordMapper fineRecordMapper;
    private final PaymentRecordMapper paymentRecordMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final FineRecordSearchRepository fineRecordSearchRepository;
    private final TenantAwareSupport tenantAwareSupport;
    private final OffenseRecordService offenseRecordService;
    private final SysUserService sysUserService;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public FineRecordService(FineRecordMapper fineRecordMapper,
                             PaymentRecordMapper paymentRecordMapper,
                             SysRequestHistoryMapper sysRequestHistoryMapper,
                             FineRecordSearchRepository fineRecordSearchRepository,
                             TenantAwareSupport tenantAwareSupport,
                             OffenseRecordService offenseRecordService,
                             SysUserService sysUserService,
                             KafkaTemplate<String, String> kafkaTemplate,
                             ObjectMapper objectMapper) {
        this.fineRecordMapper = fineRecordMapper;
        this.paymentRecordMapper = paymentRecordMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.fineRecordSearchRepository = fineRecordSearchRepository;
        this.tenantAwareSupport = tenantAwareSupport;
        this.offenseRecordService = offenseRecordService;
        this.sysUserService = sysUserService;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    public FineRecordService(FineRecordMapper fineRecordMapper,
                             PaymentRecordMapper paymentRecordMapper,
                             SysRequestHistoryMapper sysRequestHistoryMapper,
                             FineRecordSearchRepository fineRecordSearchRepository,
                             OffenseRecordService offenseRecordService,
                             SysUserService sysUserService,
                             KafkaTemplate<String, String> kafkaTemplate,
                             ObjectMapper objectMapper) {
        this(fineRecordMapper,
                paymentRecordMapper,
                sysRequestHistoryMapper,
                fineRecordSearchRepository,
                defaultTenantAwareSupport(),
                offenseRecordService,
                sysUserService,
                kafkaTemplate,
                objectMapper);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "FineRecordService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, FineRecord fineRecord, String action) {
        Objects.requireNonNull(fineRecord, "FineRecord must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate fine record request detected");
        }

        SysRequestHistory history = buildCreateHistory(idempotencyKey, fineRecord);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("fine_record_" + action, idempotencyKey, fineRecord);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public FineRecord createFineRecord(FineRecord fineRecord) {
        normalizeManualFineFieldsForCreate(fineRecord);
        validateFineRecord(fineRecord);
        fineRecordMapper.insert(fineRecord);
        syncToIndexAfterCommit(fineRecord);
        return fineRecord;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public FineRecord updateFineRecord(FineRecord fineRecord) {
        throw new IllegalStateException("Fine records are payment evidence and cannot be manually updated");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public FineRecord updateFineRecordSystemManaged(FineRecord fineRecord) {
        requirePositive(fineRecord.getFineId(), "Fine ID");
        FineRecord existing = findFineByIdFromDatabase(fineRecord.getFineId());
        if (existing == null) {
            throw new IllegalStateException("No FineRecord updated for id=" + fineRecord.getFineId());
        }
        ensureOffenseIdentityIsStable(fineRecord, existing);
        normalizePaymentManagedFields(fineRecord);
        validateFineRecord(fineRecord);
        return persistFineRecordUpdate(fineRecord);
    }

    private FineRecord persistFineRecordUpdate(FineRecord fineRecord) {
        int rows = updateFineByIdScoped(fineRecord);
        if (rows == 0) {
            throw new IllegalStateException("No FineRecord updated for id=" + fineRecord.getFineId());
        }
        syncToIndexAfterCommit(fineRecord);
        return fineRecord;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteFineRecord(Long fineId) {
        throw new IllegalStateException("Fine records are payment evidence and cannot be manually deleted");
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('fine', #fineId)", unless = "#result == null")
    public FineRecord findById(Long fineId) {
        requirePositive(fineId, "Fine ID");
        if (databaseOnlyForTenantIsolation()) {
            return findFineByIdFromDatabase(fineId);
        }
        return fineRecordSearchRepository.findById(fineId)
                .map(FineRecordDocument::toEntity)
                .orElseGet(() -> {
                    FineRecord entity = findFineByIdFromDatabase(fineId);
                    if (entity != null) {
                        fineRecordSearchRepository.save(FineRecordDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<FineRecord> findAll() {
        if (databaseOnlyForTenantIsolation()) {
            return loadAllFromDatabase();
        }
        List<FineRecord> fromIndex = StreamSupport.stream(fineRecordSearchRepository.findAll().spliterator(), false)
                .map(FineRecordDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('page', #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<FineRecord> listFines(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("updated_at")
                .orderByDesc("fine_date")
                .orderByDesc("fine_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('offense', #offenseId, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<FineRecord> findByOffenseId(Long offenseId, int page, int size) {
        requirePositive(offenseId, "Offense ID");
        validatePagination(page, size);
        List<FineRecord> index = mapHits(fineRecordSearchRepository.findByOffenseId(offenseId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_id", offenseId)
                .orderByDesc("fine_date");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<FineRecord> findByOffenseIds(Iterable<Long> offenseIds, int page, int size) {
        List<Long> normalizedIds = normalizePositiveIds(offenseIds);
        validatePagination(page, size);
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        wrapper.in("offense_id", normalizedIds)
                .orderByDesc("updated_at")
                .orderByDesc("fine_date");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<Long> findIdsByOffenseIds(Iterable<Long> offenseIds) {
        List<Long> normalizedIds = normalizePositiveIds(offenseIds);
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).select("fine_id")
                .in("offense_id", normalizedIds)
                .orderByDesc("updated_at")
                .orderByDesc("fine_date");
        return fineRecordMapper.selectObjs(wrapper).stream()
                .filter(Objects::nonNull)
                .map(this::toLong)
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('handlerPrefix', #handler, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<FineRecord> searchByHandlerPrefix(String handler, int page, int size) {
        if (isBlank(handler)) {
            return List.of();
        }
        validatePagination(page, size);
        List<FineRecord> index = mapHits(fineRecordSearchRepository.searchByHandlerPrefix(handler, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        wrapper.likeRight("handler", handler)
                .orderByDesc("fine_date");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('handlerFuzzy', #handler, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<FineRecord> searchByHandlerFuzzy(String handler, int page, int size) {
        if (isBlank(handler)) {
            return List.of();
        }
        validatePagination(page, size);
        List<FineRecord> index = mapHits(fineRecordSearchRepository.searchByHandlerFuzzy(handler, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        wrapper.like("handler", handler)
                .orderByDesc("fine_date");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('status', #paymentStatus, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<FineRecord> searchByPaymentStatus(String paymentStatus, int page, int size) {
        if (isBlank(paymentStatus)) {
            return List.of();
        }
        validatePagination(page, size);
        List<FineRecord> index = mapHits(fineRecordSearchRepository.searchByPaymentStatus(paymentStatus, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("payment_status", paymentStatus)
                .orderByDesc("fine_date");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('dateRange', #startDate, #endDate, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<FineRecord> searchByFineDateRange(String startDate, String endDate, int page, int size) {
        validatePagination(page, size);
        LocalDate start = parseDate(startDate, "startDate");
        LocalDate end = parseDate(endDate, "endDate");
        if (start == null || end == null) {
            return List.of();
        }
        List<FineRecord> index = mapHits(fineRecordSearchRepository.searchByFineDateRange(startDate, endDate, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        wrapper.between("fine_date", start, end)
                .orderByDesc("fine_date");
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long fineId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(fineId);
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

    private SysRequestHistory buildCreateHistory(String idempotencyKey, FineRecord fineRecord) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/fines");
        history.setRequestParams(buildCreateRequestParams(fineRecord));
        history.setBusinessType("FINE_CREATE");
        history.setBusinessStatus("PROCESSING");
        history.setUserId(resolveCurrentUserId());
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildCreateRequestParams(FineRecord fineRecord) {
        if (fineRecord == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "offenseId", fineRecord.getOffenseId());
        appendParam(builder, "fineAmount", fineRecord.getFineAmount());
        appendParam(builder, "lateFee", fineRecord.getLateFee());
        appendParam(builder, "paymentDeadline", fineRecord.getPaymentDeadline());
        appendParam(builder, "handler", fineRecord.getHandler());
        return truncate(builder.toString());
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

    private void sendKafkaMessage(String topic, String idempotencyKey, FineRecord fineRecord) {
        try {
            String payload = objectMapper.writeValueAsString(fineRecord);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send FineRecord Kafka message", ex);
            throw new RuntimeException("Failed to send FineRecord event", ex);
        }
    }

    private void syncToIndexAfterCommit(FineRecord fineRecord) {
        if (databaseOnlyForTenantIsolation() || fineRecord == null) {
            return;
        }
        FineRecordDocument doc = FineRecordDocument.fromEntity(fineRecord);
        if (doc == null) {
            return;
        }
        runAfterCommitOrNow(() -> fineRecordSearchRepository.save(doc));
    }

    private void syncBatchToIndexAfterCommit(List<FineRecord> records) {
        if (databaseOnlyForTenantIsolation() || records == null || records.isEmpty()) {
            return;
        }
        List<FineRecordDocument> documents = records.stream()
                .filter(Objects::nonNull)
                .map(FineRecordDocument::fromEntity)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
        if (documents.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> fineRecordSearchRepository.saveAll(documents));
    }

    private List<FineRecord> mapHits(org.springframework.data.elasticsearch.core.SearchHits<FineRecordDocument> hits) {
        if (databaseOnlyForTenantIsolation()) {
            return List.of();
        }
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(FineRecordDocument::toEntity)
                .collect(Collectors.toList());
    }

    private List<FineRecord> fetchFromDatabase(QueryWrapper<FineRecord> wrapper, int page, int size) {
        tenantScope(wrapper);
        Page<FineRecord> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        fineRecordMapper.selectPage(mpPage, wrapper);
        List<FineRecord> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<FineRecord> loadAllFromDatabase() {
        List<FineRecord> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
            tenantScope(wrapper).orderByAsc("fine_id");
            Page<FineRecord> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            fineRecordMapper.selectPage(mpPage, wrapper);
            List<FineRecord> records = mpPage.getRecords();
            if (records == null || records.isEmpty()) {
                break;
            }
            allRecords.addAll(records);
            syncBatchToIndexAfterCommit(records);
            if (records.size() < FULL_LOAD_BATCH_SIZE) {
                break;
            }
            currentPage++;
        }
        return allRecords;
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validateFineRecord(FineRecord fineRecord) {
        Objects.requireNonNull(fineRecord, "FineRecord must not be null");
        requirePositive(fineRecord.getOffenseId(), "Offense ID");
        if (!offenseRecordService.existsById(fineRecord.getOffenseId())) {
            throw new IllegalArgumentException("Offense record does not exist");
        }
        ensureSingleFinePerOffense(fineRecord);
        if (fineRecord.getFineDate() == null) {
            fineRecord.setFineDate(LocalDate.now());
        }
        if (fineRecord.getPaymentStatus() == null || fineRecord.getPaymentStatus().isBlank()) {
            fineRecord.setPaymentStatus("Unpaid");
        }
        requireNonNegative(fineRecord.getFineAmount(), "Fine amount");
        requireNonNegative(fineRecord.getLateFee(), "Late fee");
        requireNonNegative(fineRecord.getPaidAmount(), "Paid amount");
        requireNonNegative(fineRecord.getUnpaidAmount(), "Unpaid amount");
        requireNonNegative(fineRecord.getTotalAmount(), "Total amount");
        if (fineRecord.getTotalAmount() != null
                && fineRecord.getPaidAmount() != null
                && fineRecord.getPaidAmount().compareTo(fineRecord.getTotalAmount()) > 0) {
            throw new IllegalArgumentException("Paid amount cannot exceed total amount");
        }
    }

    private void normalizeManualFineFieldsForCreate(FineRecord fineRecord) {
        Objects.requireNonNull(fineRecord, "FineRecord must not be null");
        fineRecord.setFineId(null);
        normalizePaymentManagedFieldsForManualWrite(
                fineRecord,
                BigDecimal.ZERO,
                false);
    }

    private void normalizePaymentManagedFields(FineRecord fineRecord) {
        if (fineRecord == null) {
            return;
        }
        fineRecord.setFineAmount(normalizeAmount(fineRecord.getFineAmount()));
        fineRecord.setLateFee(normalizeAmount(fineRecord.getLateFee()));
        BigDecimal totalAmount = fineRecord.getFineAmount().add(fineRecord.getLateFee());
        fineRecord.setTotalAmount(totalAmount);
        fineRecord.setPaidAmount(normalizeAmount(fineRecord.getPaidAmount()));
        fineRecord.setUnpaidAmount(normalizeAmount(fineRecord.getUnpaidAmount()));
        if (fineRecord.getPaymentStatus() == null || fineRecord.getPaymentStatus().isBlank()) {
            fineRecord.setPaymentStatus(resolveFinePaymentStatus(
                    fineRecord.getPaymentDeadline(),
                    totalAmount,
                    fineRecord.getPaidAmount(),
                    fineRecord.getUnpaidAmount()));
        }
    }

    private void normalizePaymentManagedFieldsForManualWrite(FineRecord fineRecord,
                                                             BigDecimal existingPaidAmount,
                                                             boolean waived) {
        if (fineRecord == null) {
            return;
        }
        fineRecord.setFineAmount(normalizeAmount(fineRecord.getFineAmount()));
        fineRecord.setLateFee(normalizeAmount(fineRecord.getLateFee()));
        BigDecimal totalAmount = fineRecord.getFineAmount().add(fineRecord.getLateFee());
        fineRecord.setTotalAmount(totalAmount);
        if (waived) {
            fineRecord.setPaidAmount(BigDecimal.ZERO);
            fineRecord.setUnpaidAmount(BigDecimal.ZERO);
            fineRecord.setPaymentStatus(PaymentState.WAIVED.getCode());
            return;
        }
        BigDecimal paidAmount = normalizeAmount(existingPaidAmount);
        BigDecimal unpaidAmount = totalAmount.subtract(paidAmount);
        if (unpaidAmount.signum() < 0) {
            unpaidAmount = BigDecimal.ZERO;
        }
        fineRecord.setPaidAmount(paidAmount);
        fineRecord.setUnpaidAmount(unpaidAmount);
        fineRecord.setPaymentStatus(resolveFinePaymentStatus(
                fineRecord.getPaymentDeadline(),
                totalAmount,
                paidAmount,
                unpaidAmount));
    }

    private String resolveFinePaymentStatus(LocalDate paymentDeadline,
                                            BigDecimal totalAmount,
                                            BigDecimal paidAmount,
                                            BigDecimal unpaidAmount) {
        if (unpaidAmount.signum() <= 0 || totalAmount.signum() <= 0 || paidAmount.compareTo(totalAmount) >= 0) {
            return PaymentState.PAID.getCode();
        }
        if (paidAmount.signum() > 0) {
            return PaymentState.PARTIAL.getCode();
        }
        if (paymentDeadline != null && paymentDeadline.isBefore(LocalDate.now())) {
            return PaymentState.OVERDUE.getCode();
        }
        return PaymentState.UNPAID.getCode();
    }

    private void ensureSingleFinePerOffense(FineRecord fineRecord) {
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", fineRecord.getOffenseId());
        if (fineRecord.getFineId() != null) {
            wrapper.ne("fine_id", fineRecord.getFineId());
        }
        Long duplicateCount = fineRecordMapper.selectCount(wrapper);
        if (duplicateCount != null && duplicateCount > 0) {
            throw new IllegalStateException("Only one fine record is allowed for each offense");
        }
    }

    private void ensureOffenseIdentityIsStable(FineRecord fineRecord, FineRecord existing) {
        if (existing.getOffenseId() != null
                && !Objects.equals(existing.getOffenseId(), fineRecord.getOffenseId())) {
            throw new IllegalArgumentException("Offense ID cannot be changed for an existing fine record");
        }
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private void requirePositive(Number number, String fieldName) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException(fieldName + " must be greater than zero");
        }
    }

    private void requireNonNegative(BigDecimal number, String fieldName) {
        if (number != null && number.signum() < 0) {
            throw new IllegalArgumentException(fieldName + " must not be negative");
        }
    }

    private BigDecimal normalizeAmount(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value.max(BigDecimal.ZERO);
    }

    private LocalDate parseDate(String value, String fieldName) {
        if (isBlank(value)) {
            return null;
        }
        try {
            return LocalDate.parse(value);
        } catch (DateTimeParseException ex) {
            Logger.getLogger(FineRecordService.class.getName())
                    .log(Level.WARNING, "Failed to parse " + fieldName + ": " + value, ex);
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

    private List<Long> normalizePositiveIds(Iterable<Long> ids) {
        LinkedHashSet<Long> normalized = new LinkedHashSet<>();
        if (ids != null) {
            for (Long id : ids) {
                if (id != null && id > 0) {
                    normalized.add(id);
                }
            }
        }
        return new ArrayList<>(normalized);
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

    private void runAfterCommitOrNow(Runnable task) {
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

    private boolean databaseOnlyForTenantIsolation() {
        return tenantAwareSupport.isIsolationEnabled();
    }

    private <T> QueryWrapper<T> tenantScope(QueryWrapper<T> wrapper) {
        return tenantAwareSupport.applyTenantScope(wrapper);
    }

    private FineRecord findFineByIdFromDatabase(Long fineId) {
        if (fineId == null) {
            return null;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return fineRecordMapper.selectById(fineId);
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("fine_id", fineId).last("limit 1");
        return fineRecordMapper.selectOne(wrapper);
    }

    private int updateFineByIdScoped(FineRecord fineRecord) {
        if (fineRecord == null || fineRecord.getFineId() == null) {
            return 0;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return fineRecordMapper.updateById(fineRecord);
        }
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("fine_id", fineRecord.getFineId());
        return fineRecordMapper.update(fineRecord, wrapper);
    }

    private static TenantAwareSupport defaultTenantAwareSupport() {
        ProductGovernanceProperties productGovernanceProperties = new ProductGovernanceProperties();
        productGovernanceProperties.setTenantIsolationEnabled(false);
        return new TenantAwareSupport(productGovernanceProperties, new TenantIsolationProperties());
    }
}
