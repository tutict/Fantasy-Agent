package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.OffenseTypeDict;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.elastic.OffenseTypeDictDocument;
import com.tutict.finalassignmentbackend.mapper.OffenseTypeDictMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.OffenseTypeDictSearchRepository;
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
public class OffenseTypeDictService {

    private static final Logger log = Logger.getLogger(OffenseTypeDictService.class.getName());
    private static final String CACHE_NAME = "offenseTypeDictCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final OffenseTypeDictMapper offenseTypeDictMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final OffenseTypeDictSearchRepository offenseTypeDictSearchRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public OffenseTypeDictService(OffenseTypeDictMapper offenseTypeDictMapper,
                                  SysRequestHistoryMapper sysRequestHistoryMapper,
                                  OffenseTypeDictSearchRepository offenseTypeDictSearchRepository,
                                  KafkaTemplate<String, String> kafkaTemplate,
                                  ObjectMapper objectMapper) {
        this.offenseTypeDictMapper = offenseTypeDictMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.offenseTypeDictSearchRepository = offenseTypeDictSearchRepository;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "OffenseTypeDictService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, OffenseTypeDict dict, String action) {
        Objects.requireNonNull(dict, "OffenseTypeDict must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate offense type dict request detected");
        }
        SysRequestHistory history = buildHistory(idempotencyKey, dict, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("offense_type_dict_" + action, idempotencyKey, dict);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public OffenseTypeDict createDict(OffenseTypeDict dict) {
        validateDict(dict);
        offenseTypeDictMapper.insert(dict);
        syncToIndexAfterCommit(dict);
        return dict;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public OffenseTypeDict updateDict(OffenseTypeDict dict) {
        validateDict(dict);
        requirePositive(dict.getTypeId());
        int rows = offenseTypeDictMapper.updateById(dict);
        if (rows == 0) {
            throw new IllegalStateException("No OffenseTypeDict updated for id=" + dict.getTypeId());
        }
        syncToIndexAfterCommit(dict);
        return dict;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteDict(Integer typeId) {
        requirePositive(typeId);
        int rows = offenseTypeDictMapper.deleteById(typeId);
        if (rows == 0) {
            throw new IllegalStateException("No OffenseTypeDict deleted for id=" + typeId);
        }
        runAfterCommitOrNow(() -> offenseTypeDictSearchRepository.deleteById(typeId));
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#typeId", unless = "#result == null")
    public OffenseTypeDict findById(Integer typeId) {
        requirePositive(typeId);
        return offenseTypeDictSearchRepository.findById(typeId)
                .map(OffenseTypeDictDocument::toEntity)
                .orElseGet(() -> {
                    OffenseTypeDict entity = offenseTypeDictMapper.selectById(typeId);
                    if (entity != null) {
                        offenseTypeDictSearchRepository.save(OffenseTypeDictDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<OffenseTypeDict> findAll() {
        List<OffenseTypeDict> fromIndex = StreamSupport.stream(offenseTypeDictSearchRepository.findAll().spliterator(), false)
                .map(OffenseTypeDictDocument::toEntity)
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
    public List<OffenseTypeDict> findAll(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.orderByAsc("offense_code")
                .orderByAsc("type_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'codePrefix:' + #offenseCode + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByOffenseCodePrefix(String offenseCode, int page, int size) {
        if (isBlank(offenseCode)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByOffenseCodePrefix(offenseCode, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.likeRight("offense_code", offenseCode);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'codeFuzzy:' + #offenseCode + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByOffenseCodeFuzzy(String offenseCode, int page, int size) {
        if (isBlank(offenseCode)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByOffenseCodeFuzzy(offenseCode, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.like("offense_code", offenseCode);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'namePrefix:' + #offenseName + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByOffenseNamePrefix(String offenseName, int page, int size) {
        if (isBlank(offenseName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByOffenseNamePrefix(offenseName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.likeRight("offense_name", offenseName);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'nameFuzzy:' + #offenseName + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByOffenseNameFuzzy(String offenseName, int page, int size) {
        if (isBlank(offenseName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByOffenseNameFuzzy(offenseName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.like("offense_name", offenseName);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'category:' + #category + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByCategory(String category, int page, int size) {
        if (isBlank(category)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByCategory(category, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.eq("category", category);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'severity:' + #severityLevel + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchBySeverityLevel(String severityLevel, int page, int size) {
        if (isBlank(severityLevel)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchBySeverityLevel(severityLevel, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.eq("severity_level", severityLevel);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'status:' + #status + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByStatus(String status, int page, int size) {
        if (isBlank(status)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByStatus(status, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.eq("status", status);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'fineRange:' + #minAmount + ':' + #maxAmount + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByStandardFineAmountRange(double minAmount, double maxAmount, int page, int size) {
        validatePagination(page, size);
        if (minAmount > maxAmount) {
            return List.of();
        }
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByStandardFineAmountRange(minAmount, maxAmount, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.between("standard_fine_amount", minAmount, maxAmount);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'pointsRange:' + #minPoints + ':' + #maxPoints + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<OffenseTypeDict> searchByDeductedPointsRange(int minPoints, int maxPoints, int page, int size) {
        validatePagination(page, size);
        if (minPoints > maxPoints) {
            return List.of();
        }
        List<OffenseTypeDict> index = mapHits(offenseTypeDictSearchRepository.searchByDeductedPointsRange(minPoints, maxPoints, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.between("deducted_points", minPoints, maxPoints);
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Integer typeId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(typeId != null ? typeId.longValue() : null);
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

    private SysRequestHistory buildHistory(String idempotencyKey, OffenseTypeDict dict, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/offense-types");
        history.setRequestParams(buildRequestParams(dict));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(OffenseTypeDict dict) {
        if (dict == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "offenseCode", dict.getOffenseCode());
        appendParam(builder, "offenseName", dict.getOffenseName());
        appendParam(builder, "category", dict.getCategory());
        appendParam(builder, "severityLevel", dict.getSeverityLevel());
        appendParam(builder, "status", dict.getStatus());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "OFFENSE_TYPE_DICT_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, OffenseTypeDict dict) {
        try {
            String payload = objectMapper.writeValueAsString(dict);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send OffenseTypeDict Kafka message", ex);
            throw new RuntimeException("Failed to send OffenseTypeDict event", ex);
        }
    }

    private void syncToIndexAfterCommit(OffenseTypeDict dict) {
        if (dict == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            OffenseTypeDictDocument doc = OffenseTypeDictDocument.fromEntity(dict);
            if (doc != null) {
                offenseTypeDictSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<OffenseTypeDict> dicts) {
        if (dicts == null || dicts.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<OffenseTypeDictDocument> documents = dicts.stream()
                    .filter(Objects::nonNull)
                    .map(OffenseTypeDictDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                offenseTypeDictSearchRepository.saveAll(documents);
            }
        });
    }

    private void validateDict(OffenseTypeDict dict) {
        Objects.requireNonNull(dict, "OffenseTypeDict must not be null");
        if (dict.getOffenseCode() == null || dict.getOffenseCode().isBlank()) {
            throw new IllegalArgumentException("Offense code must not be blank");
        }
        if (dict.getOffenseName() == null || dict.getOffenseName().isBlank()) {
            throw new IllegalArgumentException("Offense name must not be blank");
        }
        if (dict.getStatus() == null || dict.getStatus().isBlank()) {
            dict.setStatus("Active");
        }
        if (dict.getCreatedAt() == null) {
            dict.setCreatedAt(LocalDateTime.now());
        }
        if (dict.getUpdatedAt() == null) {
            dict.setUpdatedAt(LocalDateTime.now());
        }
    }

    private List<OffenseTypeDict> fetchFromDatabase(QueryWrapper<OffenseTypeDict> wrapper, int page, int size) {
        Page<OffenseTypeDict> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        offenseTypeDictMapper.selectPage(mpPage, wrapper);
        List<OffenseTypeDict> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<OffenseTypeDict> loadAllFromDatabase() {
        List<OffenseTypeDict> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
            wrapper.orderByAsc("type_id");
            Page<OffenseTypeDict> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            offenseTypeDictMapper.selectPage(mpPage, wrapper);
            List<OffenseTypeDict> records = mpPage.getRecords();
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

    private List<OffenseTypeDict> mapHits(org.springframework.data.elasticsearch.core.SearchHits<OffenseTypeDictDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(OffenseTypeDictDocument::toEntity)
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
            throw new IllegalArgumentException("Type ID" + " must be greater than zero");
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
