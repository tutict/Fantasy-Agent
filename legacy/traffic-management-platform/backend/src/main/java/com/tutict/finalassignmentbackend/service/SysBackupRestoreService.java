package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.SysBackupRestore;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.elastic.SysBackupRestoreDocument;
import com.tutict.finalassignmentbackend.mapper.SysBackupRestoreMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.SysBackupRestoreSearchRepository;
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
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class SysBackupRestoreService {

    private static final Logger log = Logger.getLogger(SysBackupRestoreService.class.getName());
    private static final String CACHE_NAME = "sysBackupRestoreCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final SysBackupRestoreMapper sysBackupRestoreMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final SysBackupRestoreSearchRepository sysBackupRestoreSearchRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public SysBackupRestoreService(SysBackupRestoreMapper sysBackupRestoreMapper,
                                   SysRequestHistoryMapper sysRequestHistoryMapper,
                                   SysBackupRestoreSearchRepository sysBackupRestoreSearchRepository,
                                   KafkaTemplate<String, String> kafkaTemplate,
                                   ObjectMapper objectMapper) {
        this.sysBackupRestoreMapper = sysBackupRestoreMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.sysBackupRestoreSearchRepository = sysBackupRestoreSearchRepository;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "SysBackupRestoreService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, SysBackupRestore backupRestore, String action) {
        Objects.requireNonNull(backupRestore, "SysBackupRestore must not be null");
        SysRequestHistory existing = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            log.warning(() -> String.format("Duplicate sys backup/restore request detected (key=%s)", idempotencyKey));
            throw new RuntimeException("Duplicate sys backup/restore request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, backupRestore, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("sys_backup_restore_" + action, idempotencyKey, backupRestore);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysBackupRestore createSysBackupRestore(SysBackupRestore backupRestore) {
        validateBackupRestore(backupRestore);
        sysBackupRestoreMapper.insert(backupRestore);
        syncToIndexAfterCommit(backupRestore);
        return backupRestore;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysBackupRestore updateSysBackupRestore(SysBackupRestore backupRestore) {
        validateBackupRestore(backupRestore);
        requirePositive(backupRestore.getBackupId());
        int rows = sysBackupRestoreMapper.updateById(backupRestore);
        if (rows == 0) {
            throw new IllegalStateException("SysBackupRestore not found for id=" + backupRestore.getBackupId());
        }
        syncToIndexAfterCommit(backupRestore);
        return backupRestore;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteSysBackupRestore(Long backupId) {
        requirePositive(backupId);
        int rows = sysBackupRestoreMapper.deleteById(backupId);
        if (rows == 0) {
            throw new IllegalStateException("SysBackupRestore not found for id=" + backupId);
        }
        runAfterCommitOrNow(() -> sysBackupRestoreSearchRepository.deleteById(backupId));
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#backupId", unless = "#result == null")
    public SysBackupRestore findById(Long backupId) {
        requirePositive(backupId);
        return sysBackupRestoreSearchRepository.findById(backupId)
                .map(SysBackupRestoreDocument::toEntity)
                .orElseGet(() -> {
                    SysBackupRestore entity = sysBackupRestoreMapper.selectById(backupId);
                    if (entity != null) {
                        sysBackupRestoreSearchRepository.save(SysBackupRestoreDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<SysBackupRestore> findAll() {
        List<SysBackupRestore> fromIndex = StreamSupport.stream(sysBackupRestoreSearchRepository.findAll().spliterator(), false)
                .map(SysBackupRestoreDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'list:' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> listBackups(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("backup_time")
                .orderByDesc("backup_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'backupType:' + #backupType + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> searchByBackupType(String backupType, int page, int size) {
        if (isBlank(backupType)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysBackupRestore> index = mapHits(sysBackupRestoreSearchRepository.searchByBackupType(backupType, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.eq("backup_type", backupType)
                .orderByDesc("backup_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'fileName:' + #backupFileName + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> searchByBackupFileNamePrefix(String backupFileName, int page, int size) {
        if (isBlank(backupFileName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysBackupRestore> index = mapHits(sysBackupRestoreSearchRepository.searchByBackupFileNamePrefix(backupFileName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.likeRight("backup_file_name", backupFileName)
                .orderByDesc("backup_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'handler:' + #backupHandler + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> searchByBackupHandler(String backupHandler, int page, int size) {
        if (isBlank(backupHandler)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysBackupRestore> index = mapHits(sysBackupRestoreSearchRepository.searchByBackupHandler(backupHandler, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.likeRight("backup_handler", backupHandler)
                .orderByDesc("backup_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'restoreStatus:' + #restoreStatus + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> searchByRestoreStatus(String restoreStatus, int page, int size) {
        if (isBlank(restoreStatus)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysBackupRestore> index = mapHits(sysBackupRestoreSearchRepository.searchByRestoreStatus(restoreStatus, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.eq("restore_status", restoreStatus)
                .orderByDesc("restore_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'status:' + #status + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> searchByStatus(String status, int page, int size) {
        if (isBlank(status)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysBackupRestore> index = mapHits(sysBackupRestoreSearchRepository.searchByStatus(status, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.eq("status", status)
                .orderByDesc("backup_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'backupRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> searchByBackupTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<SysBackupRestore> index = mapHits(sysBackupRestoreSearchRepository.searchByBackupTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.between("backup_time", start, end)
                .orderByDesc("backup_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'restoreRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysBackupRestore> searchByRestoreTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<SysBackupRestore> index = mapHits(sysBackupRestoreSearchRepository.searchByRestoreTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
        wrapper.between("restore_time", start, end)
                .orderByDesc("restore_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long backupId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(backupId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, SysBackupRestore backupRestore, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/sys/backups");
        history.setRequestParams(buildRequestParams(backupRestore));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(SysBackupRestore backupRestore) {
        if (backupRestore == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "backupType", backupRestore.getBackupType());
        appendParam(builder, "backupFileName", backupRestore.getBackupFileName());
        appendParam(builder, "backupHandler", backupRestore.getBackupHandler());
        appendParam(builder, "restoreStatus", backupRestore.getRestoreStatus());
        appendParam(builder, "status", backupRestore.getStatus());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "SYS_BACKUP_RESTORE_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, SysBackupRestore backupRestore) {
        try {
            String payload = objectMapper.writeValueAsString(backupRestore);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send SysBackupRestore Kafka message", ex);
            throw new RuntimeException("Failed to send sys backup/restore event", ex);
        }
    }

    private void syncToIndexAfterCommit(SysBackupRestore backupRestore) {
        if (backupRestore == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            SysBackupRestoreDocument doc = SysBackupRestoreDocument.fromEntity(backupRestore);
            if (doc != null) {
                sysBackupRestoreSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<SysBackupRestore> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<SysBackupRestoreDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(SysBackupRestoreDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                sysBackupRestoreSearchRepository.saveAll(documents);
            }
        });
    }

    private List<SysBackupRestore> fetchFromDatabase(QueryWrapper<SysBackupRestore> wrapper, int page, int size) {
        Page<SysBackupRestore> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        sysBackupRestoreMapper.selectPage(mpPage, wrapper);
        List<SysBackupRestore> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<SysBackupRestore> loadAllFromDatabase() {
        List<SysBackupRestore> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<SysBackupRestore> wrapper = new QueryWrapper<>();
            wrapper.orderByAsc("backup_id");
            Page<SysBackupRestore> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            sysBackupRestoreMapper.selectPage(mpPage, wrapper);
            List<SysBackupRestore> records = mpPage.getRecords();
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

    private List<SysBackupRestore> mapHits(org.springframework.data.elasticsearch.core.SearchHits<SysBackupRestoreDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(SysBackupRestoreDocument::toEntity)
                .collect(Collectors.toList());
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private void validateBackupRestore(SysBackupRestore backupRestore) {
        if (backupRestore == null) {
            throw new IllegalArgumentException("SysBackupRestore must not be null");
        }
        if (backupRestore.getBackupTime() == null) {
            backupRestore.setBackupTime(LocalDateTime.now());
        }
        if (isBlank(backupRestore.getStatus())) {
            backupRestore.setStatus("Pending");
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
            throw new IllegalArgumentException("Backup ID" + " must be greater than zero");
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
}
