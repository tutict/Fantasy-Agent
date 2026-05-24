package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.elastic.SysRequestHistoryDocument;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.SysRequestHistorySearchRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class SysRequestHistoryService {

    private static final Logger log = Logger.getLogger(SysRequestHistoryService.class.getName());
    private static final String CACHE_NAME = "sysRequestHistoryCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;
    private static final List<String> REFUND_BUSINESS_TYPES = List.of(
            "PARTIAL_REFUND",
            "WAIVE_AND_REFUND",
            "PARTIAL_REFUND_FAILED",
            "WAIVE_AND_REFUND_FAILED"
    );

    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final SysRequestHistorySearchRepository sysRequestHistorySearchRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public SysRequestHistoryService(SysRequestHistoryMapper sysRequestHistoryMapper,
                                    SysRequestHistorySearchRepository sysRequestHistorySearchRepository,
                                    KafkaTemplate<String, String> kafkaTemplate,
                                    ObjectMapper objectMapper) {
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.sysRequestHistorySearchRepository = sysRequestHistorySearchRepository;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "SysRequestHistoryService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, SysRequestHistory historyPayload, String action) {
        Objects.requireNonNull(historyPayload, "SysRequestHistory must not be null");
        SysRequestHistory existing = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            log.warning(() -> String.format("Duplicate sys request history request detected (key=%s)", idempotencyKey));
            throw new RuntimeException("Duplicate sys request history request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, historyPayload, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("sys_request_history_" + action, idempotencyKey, historyPayload);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysRequestHistory createSysRequestHistory(SysRequestHistory history) {
        throw new IllegalStateException(
                "Request history records are system-managed audit data and cannot be created manually");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysRequestHistory updateSysRequestHistory(SysRequestHistory history) {
        throw new IllegalStateException(
                "Request history records are read-only audit data and cannot be edited manually");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteSysRequestHistory(Long id) {
        throw new IllegalStateException(
                "Request history records are audit evidence and cannot be deleted manually");
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#id", unless = "#result == null")
    public SysRequestHistory findById(Long id) {
        requirePositive(id);
        return sysRequestHistorySearchRepository.findById(id)
                .map(SysRequestHistoryDocument::toEntity)
                .orElseGet(() -> {
                    SysRequestHistory entity = sysRequestHistoryMapper.selectById(id);
                    if (entity != null) {
                        sysRequestHistorySearchRepository.save(SysRequestHistoryDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<SysRequestHistory> findAll() {
        List<SysRequestHistory> fromIndex = StreamSupport.stream(sysRequestHistorySearchRepository.findAll().spliterator(), false)
                .map(SysRequestHistoryDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'countAll'")
    public long countAll() {
        long indexCount = sysRequestHistorySearchRepository.count();
        if (indexCount > 0) {
            return indexCount;
        }
        return sysRequestHistoryMapper.selectCount(null);
    }

    @Transactional(readOnly = true)
    @Cacheable(
            cacheNames = CACHE_NAME,
            key = "'all:' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> findAll(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("updated_at")
                .orderByDesc("created_at")
                .orderByDesc("id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'status:' + #status + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> findByBusinessStatus(String status, int page, int size) {
        if (isBlank(status)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.searchByBusinessStatus(status, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.eq("business_status", status)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'idempotency:' + #key + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> searchByIdempotencyKey(String key, int page, int size) {
        if (isBlank(key)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.searchByIdempotencyKey(key, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.eq("idempotency_key", key)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'method:' + #requestMethod + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> searchByRequestMethod(String requestMethod, int page, int size) {
        if (isBlank(requestMethod)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.searchByRequestMethod(requestMethod, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.eq("request_method", requestMethod)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'urlPrefix:' + #requestUrl + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> searchByRequestUrlPrefix(String requestUrl, int page, int size) {
        if (isBlank(requestUrl)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.searchByRequestUrlPrefix(requestUrl, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.likeRight("request_url", requestUrl)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'businessType:' + #businessType + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> searchByBusinessType(String businessType, int page, int size) {
        if (isBlank(businessType)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.searchByBusinessType(businessType, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.eq("business_type", businessType)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'businessId:' + #businessId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> findByBusinessId(Long businessId, int page, int size) {
        if (businessId == null || businessId <= 0) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.findByBusinessId(businessId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.eq("business_id", businessId)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'userId:' + #userId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> findByUserId(Long userId, int page, int size) {
        if (userId == null || userId <= 0) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.findByUserId(userId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<SysRequestHistory> findByBusinessIds(Iterable<Long> businessIds, int page, int size) {
        List<Long> normalizedIds = normalizePositiveIds(businessIds);
        validatePagination(page, size);
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.in("business_id", normalizedIds)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'requestIp:' + #requestIp + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> searchByRequestIp(String requestIp, int page, int size) {
        if (isBlank(requestIp)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.searchByRequestIp(requestIp, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.eq("request_ip", requestIp)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'createdRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> searchByCreatedAtRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<SysRequestHistory> index = mapHits(sysRequestHistorySearchRepository.searchByCreatedAtRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.between("created_at", start, end)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'refundAudits:' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> findRefundAudits(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.in("business_type", REFUND_BUSINESS_TYPES)
                .orderByDesc("updated_at");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'refundAuditsStatus:' + #status + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> findRefundAuditsByStatus(String status, int page, int size) {
        validatePagination(page, size);
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.in("business_type", REFUND_BUSINESS_TYPES)
                .orderByDesc("updated_at");
        if (!isBlank(status)) {
            wrapper.eq("business_status", status);
        }
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(
            cacheNames = CACHE_NAME,
            key = "'refundAuditsFilter:' + #status + ':' + #fineId + ':' + #paymentId + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysRequestHistory> findRefundAudits(String status, Long fineId, Long paymentId, int page, int size) {
        validatePagination(page, size);
        validateOptionalPositive(fineId, "Fine ID");
        validateOptionalPositive(paymentId, "Payment ID");

        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.in("business_type", REFUND_BUSINESS_TYPES)
                .orderByDesc("updated_at");
        if (!isBlank(status)) {
            wrapper.eq("business_status", status);
        }
        if (fineId != null) {
            wrapper.likeRight("request_params", "fineId=" + fineId + ",");
        }
        if (paymentId != null) {
            wrapper.eq("business_id", paymentId);
        }
        return fetchFromDatabase(wrapper, page, size);
    }

    public Optional<SysRequestHistory> findByIdempotencyKey(String key) {
        if (isBlank(key)) {
            return Optional.empty();
        }
        return Optional.ofNullable(sysRequestHistoryMapper.selectByIdempotencyKey(key));
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long historyId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(historyId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, SysRequestHistory historyPayload, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/sys/request-history");
        history.setRequestParams(buildRequestParams(historyPayload));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(SysRequestHistory historyPayload) {
        if (historyPayload == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "requestMethod", historyPayload.getRequestMethod());
        appendParam(builder, "requestUrl", historyPayload.getRequestUrl());
        appendParam(builder, "businessType", historyPayload.getBusinessType());
        appendParam(builder, "businessStatus", historyPayload.getBusinessStatus());
        appendParam(builder, "businessId", historyPayload.getBusinessId());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "SYS_REQUEST_HISTORY_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, SysRequestHistory history) {
        try {
            String payload = objectMapper.writeValueAsString(history);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send SysRequestHistory Kafka message", ex);
            throw new RuntimeException("Failed to send sys request history event", ex);
        }
    }

    private void syncToIndexAfterCommit(SysRequestHistory history) {
        if (history == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            SysRequestHistoryDocument doc = SysRequestHistoryDocument.fromEntity(history);
            if (doc != null) {
                sysRequestHistorySearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<SysRequestHistory> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<SysRequestHistoryDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(SysRequestHistoryDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                sysRequestHistorySearchRepository.saveAll(documents);
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

    private List<SysRequestHistory> fetchFromDatabase(QueryWrapper<SysRequestHistory> wrapper, int page, int size) {
        Page<SysRequestHistory> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        sysRequestHistoryMapper.selectPage(mpPage, wrapper);
        List<SysRequestHistory> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<SysRequestHistory> loadAllFromDatabase() {
        QueryWrapper<SysRequestHistory> wrapper = new QueryWrapper<>();
        wrapper.orderByAsc("id");

        List<SysRequestHistory> allRecords = new java.util.ArrayList<>();
        long pageNumber = 1L;
        while (true) {
            Page<SysRequestHistory> batchPage = new Page<>(pageNumber, FULL_LOAD_BATCH_SIZE);
            sysRequestHistoryMapper.selectPage(batchPage, wrapper);
            List<SysRequestHistory> records = batchPage.getRecords();
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

    private List<SysRequestHistory> mapHits(org.springframework.data.elasticsearch.core.SearchHits<SysRequestHistoryDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(SysRequestHistoryDocument::toEntity)
                .collect(Collectors.toList());
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validateHistory(SysRequestHistory history) {
        if (history == null) {
            throw new IllegalArgumentException("SysRequestHistory must not be null");
        }
        if (isBlank(history.getIdempotencyKey())) {
            throw new IllegalArgumentException("Idempotency key must not be blank");
        }
        if (history.getCreatedAt() == null) {
            history.setCreatedAt(LocalDateTime.now());
        }
        if (history.getUpdatedAt() == null) {
            history.setUpdatedAt(LocalDateTime.now());
        }
        if (isBlank(history.getBusinessStatus())) {
            history.setBusinessStatus("PENDING");
        }
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
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

    private void requirePositive(Number number) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException("History ID" + " must be greater than zero");
        }
    }

    private void validateOptionalPositive(Number number, String fieldName) {
        if (number == null) {
            return;
        }
        if (number.longValue() <= 0) {
            throw new IllegalArgumentException(fieldName + " must be greater than zero");
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private List<Long> normalizePositiveIds(Iterable<Long> ids) {
        if (ids == null) {
            return List.of();
        }
        return StreamSupport.stream(ids.spliterator(), false)
                .filter(Objects::nonNull)
                .filter(id -> id > 0)
                .distinct()
                .collect(Collectors.toList());
    }

    private String truncate(String value) {
        if (value == null) {
            return null;
        }
        return value.length() <= 500 ? value : value.substring(0, 500);
    }
}
