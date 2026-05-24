package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.SysDict;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.elastic.SysDictDocument;
import com.tutict.finalassignmentbackend.mapper.SysDictMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.SysDictSearchRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class SysDictService {

    private static final Logger log = Logger.getLogger(SysDictService.class.getName());
    private static final String CACHE_NAME = "sysDictCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final SysDictMapper sysDictMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final SysDictSearchRepository sysDictSearchRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public SysDictService(SysDictMapper sysDictMapper,
                          SysRequestHistoryMapper sysRequestHistoryMapper,
                          SysDictSearchRepository sysDictSearchRepository,
                          KafkaTemplate<String, String> kafkaTemplate,
                          ObjectMapper objectMapper) {
        this.sysDictMapper = sysDictMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.sysDictSearchRepository = sysDictSearchRepository;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "SysDictService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, SysDict sysDict, String action) {
        Objects.requireNonNull(sysDict, "SysDict must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate SysDict request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, sysDict, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("sys_dict_" + action, idempotencyKey, sysDict);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysDict createSysDict(SysDict sysDict) {
        validateSysDict(sysDict);
        sysDictMapper.insert(sysDict);
        syncToIndexAfterCommit(sysDict);
        return sysDict;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysDict updateSysDict(SysDict sysDict) {
        validateSysDict(sysDict);
        requirePositive(sysDict.getDictId());
        int rows = sysDictMapper.updateById(sysDict);
        if (rows == 0) {
            throw new IllegalStateException("No SysDict updated for id=" + sysDict.getDictId());
        }
        syncToIndexAfterCommit(sysDict);
        return sysDict;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteSysDict(Integer dictId) {
        requirePositive(dictId);
        int rows = sysDictMapper.deleteById(dictId);
        if (rows == 0) {
            throw new IllegalStateException("No SysDict deleted for id=" + dictId);
        }
        runAfterCommitOrNow(() -> sysDictSearchRepository.deleteById(dictId));
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#dictId", unless = "#result == null")
    public SysDict findById(Integer dictId) {
        requirePositive(dictId);
        return sysDictSearchRepository.findById(dictId)
                .map(SysDictDocument::toEntity)
                .orElseGet(() -> {
                    SysDict entity = sysDictMapper.selectById(dictId);
                    if (entity != null) {
                        sysDictSearchRepository.save(SysDictDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<SysDict> findAll() {
        List<SysDict> fromIndex = StreamSupport.stream(sysDictSearchRepository.findAll().spliterator(), false)
                .map(SysDictDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(
            cacheNames = CACHE_NAME,
            key = "'all:' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> findAll(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.orderByAsc("sort_order")
                .orderByAsc("dict_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'type:' + #dictType + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> searchByDictType(String dictType, int page, int size) {
        if (isBlank(dictType)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysDict> index = mapHits(sysDictSearchRepository.searchByDictType(dictType, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.eq("dict_type", dictType)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'codePrefix:' + #dictCode + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> searchByDictCodePrefix(String dictCode, int page, int size) {
        if (isBlank(dictCode)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysDict> index = mapHits(sysDictSearchRepository.searchByDictCodePrefix(dictCode, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.likeRight("dict_code", dictCode)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'labelPrefix:' + #dictLabel + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> searchByDictLabelPrefix(String dictLabel, int page, int size) {
        if (isBlank(dictLabel)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysDict> index = mapHits(sysDictSearchRepository.searchByDictLabelPrefix(dictLabel, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.likeRight("dict_label", dictLabel)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'labelFuzzy:' + #dictLabel + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> searchByDictLabelFuzzy(String dictLabel, int page, int size) {
        if (isBlank(dictLabel)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysDict> index = mapHits(sysDictSearchRepository.searchByDictLabelFuzzy(dictLabel, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.like("dict_label", dictLabel)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'parent:' + #parentId + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> findByParentId(Integer parentId, int page, int size) {
        validatePagination(page, size);
        List<SysDict> index = mapHits(sysDictSearchRepository.findByParentId(parentId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.eq("parent_id", parentId)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'default:' + #isDefault + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> searchByIsDefault(boolean isDefault, int page, int size) {
        validatePagination(page, size);
        List<SysDict> index = mapHits(sysDictSearchRepository.searchByIsDefault(isDefault, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.eq("is_default", isDefault)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'status:' + #status + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysDict> searchByStatus(String status, int page, int size) {
        if (isBlank(status)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysDict> index = mapHits(sysDictSearchRepository.searchByStatus(status, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.eq("status", status)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Integer dictId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(dictId != null ? dictId.longValue() : null);
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

    private SysRequestHistory buildHistory(String idempotencyKey, SysDict sysDict, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/sys/dicts");
        history.setRequestParams(buildRequestParams(sysDict));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(SysDict sysDict) {
        if (sysDict == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "dictType", sysDict.getDictType());
        appendParam(builder, "dictCode", sysDict.getDictCode());
        appendParam(builder, "dictLabel", sysDict.getDictLabel());
        appendParam(builder, "parentId", sysDict.getParentId());
        appendParam(builder, "status", sysDict.getStatus());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "SYS_DICT_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, SysDict sysDict) {
        try {
            String payload = objectMapper.writeValueAsString(sysDict);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send SysDict Kafka message", ex);
            throw new RuntimeException("Failed to send SysDict event", ex);
        }
    }

    private void syncToIndexAfterCommit(SysDict sysDict) {
        if (sysDict == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            SysDictDocument doc = SysDictDocument.fromEntity(sysDict);
            if (doc != null) {
                sysDictSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<SysDict> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<SysDictDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(SysDictDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                sysDictSearchRepository.saveAll(documents);
            }
        });
    }

    private void validateSysDict(SysDict sysDict) {
        Objects.requireNonNull(sysDict, "SysDict must not be null");
        if (sysDict.getDictType() == null || sysDict.getDictType().isBlank()) {
            throw new IllegalArgumentException("Dictionary type must not be blank");
        }
        if (sysDict.getDictCode() == null || sysDict.getDictCode().isBlank()) {
            throw new IllegalArgumentException("Dictionary code must not be blank");
        }
    }

    private List<SysDict> fetchFromDatabase(QueryWrapper<SysDict> wrapper, int page, int size) {
        Page<SysDict> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        sysDictMapper.selectPage(mpPage, wrapper);
        List<SysDict> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<SysDict> loadAllFromDatabase() {
        List<SysDict> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
            wrapper.orderByAsc("dict_id");
            Page<SysDict> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            sysDictMapper.selectPage(mpPage, wrapper);
            List<SysDict> records = mpPage.getRecords();
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

    private List<SysDict> mapHits(org.springframework.data.elasticsearch.core.SearchHits<SysDictDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(SysDictDocument::toEntity)
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

    private void requirePositive(Number number) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException("Dictionary ID" + " must be greater than zero");
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
