package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.AuditLoginLog;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.elastic.AuditLoginLogDocument;
import com.tutict.finalassignmentbackend.mapper.AuditLoginLogMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.AuditLoginLogSearchRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class AuditLoginLogService {

    private static final Logger log = Logger.getLogger(AuditLoginLogService.class.getName());
    private static final String CACHE_NAME = "auditLoginLogCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final AuditLoginLogMapper auditLoginLogMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final AuditLoginLogSearchRepository auditLoginLogSearchRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public AuditLoginLogService(AuditLoginLogMapper auditLoginLogMapper,
                                SysRequestHistoryMapper sysRequestHistoryMapper,
                                AuditLoginLogSearchRepository auditLoginLogSearchRepository,
                                KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper) {
        this.auditLoginLogMapper = auditLoginLogMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.auditLoginLogSearchRepository = auditLoginLogSearchRepository;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "AuditLoginLogService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, AuditLoginLog loginLog, String action) {
        Objects.requireNonNull(loginLog, "AuditLoginLog must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate audit login log request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, loginLog, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("audit_login_log_" + action, idempotencyKey, loginLog);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public AuditLoginLog createAuditLoginLog(AuditLoginLog loginLog) {
        throw new IllegalStateException("Audit login logs are security evidence and cannot be manually created");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public AuditLoginLog createAuditLoginLogSystemManaged(AuditLoginLog loginLog) {
        validateLoginLog(loginLog);
        auditLoginLogMapper.insert(loginLog);
        syncToIndexAfterCommit(loginLog);
        return loginLog;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public AuditLoginLog updateAuditLoginLog(AuditLoginLog loginLog) {
        throw new IllegalStateException("Audit login logs are security evidence and cannot be manually updated");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public AuditLoginLog updateAuditLoginLogSystemManaged(AuditLoginLog loginLog) {
        validateLoginLog(loginLog);
        requirePositive(loginLog.getLogId());
        int rows = auditLoginLogMapper.updateById(loginLog);
        if (rows == 0) {
            throw new IllegalStateException("Audit login log not found for id=" + loginLog.getLogId());
        }
        syncToIndexAfterCommit(loginLog);
        return loginLog;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteAuditLoginLog(Long logId) {
        throw new IllegalStateException("Audit login logs are security evidence and cannot be manually deleted");
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#logId", unless = "#result == null")
    public AuditLoginLog findById(Long logId) {
        requirePositive(logId);
        return auditLoginLogSearchRepository.findById(logId)
                .map(AuditLoginLogDocument::toEntity)
                .orElseGet(() -> {
                    AuditLoginLog entity = auditLoginLogMapper.selectById(logId);
                    if (entity != null) {
                        auditLoginLogSearchRepository.save(AuditLoginLogDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<AuditLoginLog> findAll() {
        List<AuditLoginLog> fromIndex = StreamSupport.stream(auditLoginLogSearchRepository.findAll().spliterator(), false)
                .map(AuditLoginLogDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'countAll'")
    public long countAll() {
        long indexCount = auditLoginLogSearchRepository.count();
        if (indexCount > 0) {
            return indexCount;
        }
        return auditLoginLogMapper.selectCount(null);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'list:' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> listLogs(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("login_time")
                .orderByDesc("log_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'username:' + #username + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByUsername(String username, int page, int size) {
        if (isBlank(username)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByUsername(username, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.like("username", username)
                .orderByDesc("login_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'result:' + #loginResult + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByLoginResult(String loginResult, int page, int size) {
        if (isBlank(loginResult)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByLoginResult(loginResult, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.eq("login_result", loginResult)
                .orderByDesc("login_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'timeRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByLoginTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByLoginTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.between("login_time", start, end)
                .orderByDesc("login_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'ip:' + #loginIp + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByLoginIp(String loginIp, int page, int size) {
        if (isBlank(loginIp)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByLoginIp(loginIp, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.eq("login_ip", loginIp)
                .orderByDesc("login_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'location:' + #loginLocation + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByLoginLocation(String loginLocation, int page, int size) {
        if (isBlank(loginLocation)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByLoginLocation(loginLocation, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.like("login_location", loginLocation)
                .orderByDesc("login_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'device:' + #deviceType + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByDeviceType(String deviceType, int page, int size) {
        if (isBlank(deviceType)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByDeviceType(deviceType, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.like("device_type", deviceType)
                .orderByDesc("login_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'browser:' + #browserType + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByBrowserType(String browserType, int page, int size) {
        if (isBlank(browserType)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByBrowserType(browserType, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.like("browser_type", browserType)
                .orderByDesc("login_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'logoutRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AuditLoginLog> searchByLogoutTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<AuditLoginLog> index = mapHits(auditLoginLogSearchRepository.searchByLogoutTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.between("logout_time", start, end)
                .orderByDesc("logout_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long logId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(logId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, AuditLoginLog loginLog, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/audit/login-logs");
        history.setRequestParams(buildRequestParams(loginLog));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(AuditLoginLog loginLog) {
        if (loginLog == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "username", loginLog.getUsername());
        appendParam(builder, "loginIp", loginLog.getLoginIp());
        appendParam(builder, "loginResult", loginLog.getLoginResult());
        appendParam(builder, "deviceType", loginLog.getDeviceType());
        appendParam(builder, "browserType", loginLog.getBrowserType());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "AUDIT_LOGIN_LOG_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, AuditLoginLog loginLog) {
        try {
            String payload = objectMapper.writeValueAsString(loginLog);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send AuditLoginLog Kafka message", ex);
            throw new RuntimeException("Failed to send AuditLoginLog event", ex);
        }
    }

    private void syncToIndexAfterCommit(AuditLoginLog loginLog) {
        runAfterCommitOrNow(() -> {
            AuditLoginLogDocument doc = AuditLoginLogDocument.fromEntity(loginLog);
            if (doc != null) {
                auditLoginLogSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<AuditLoginLog> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<AuditLoginLogDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(AuditLoginLogDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                auditLoginLogSearchRepository.saveAll(documents);
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

    private List<AuditLoginLog> fetchFromDatabase(QueryWrapper<AuditLoginLog> wrapper, int page, int size) {
        Page<AuditLoginLog> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        auditLoginLogMapper.selectPage(mpPage, wrapper);
        List<AuditLoginLog> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<AuditLoginLog> loadAllFromDatabase() {
        QueryWrapper<AuditLoginLog> wrapper = new QueryWrapper<>();
        wrapper.orderByAsc("log_id");

        List<AuditLoginLog> allRecords = new java.util.ArrayList<>();
        long pageNumber = 1L;
        while (true) {
            Page<AuditLoginLog> batchPage = new Page<>(pageNumber, FULL_LOAD_BATCH_SIZE);
            auditLoginLogMapper.selectPage(batchPage, wrapper);
            List<AuditLoginLog> records = batchPage.getRecords();
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

    private List<AuditLoginLog> mapHits(SearchHits<AuditLoginLogDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(SearchHit::getContent)
                .map(AuditLoginLogDocument::toEntity)
                .collect(Collectors.toList());
    }

    private Pageable pageable(int page, int size) {
        return PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validateLoginLog(AuditLoginLog loginLog) {
        if (loginLog == null) {
            throw new IllegalArgumentException("Audit login log must not be null");
        }
        if (loginLog.getLoginTime() == null) {
            loginLog.setLoginTime(LocalDateTime.now());
        }
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private void requirePositive(Number number) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException("Log ID" + " must be greater than zero");
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
}
