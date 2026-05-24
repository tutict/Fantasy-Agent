package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.SysPermission;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.elastic.SysPermissionDocument;
import com.tutict.finalassignmentbackend.mapper.SysPermissionMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.SysPermissionSearchRepository;
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
public class SysPermissionService {

    private static final Logger log = Logger.getLogger(SysPermissionService.class.getName());
    private static final String CACHE_NAME = "sysPermissionCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final SysPermissionMapper sysPermissionMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final SysPermissionSearchRepository sysPermissionSearchRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public SysPermissionService(SysPermissionMapper sysPermissionMapper,
                                SysRequestHistoryMapper sysRequestHistoryMapper,
                                SysPermissionSearchRepository sysPermissionSearchRepository,
                                KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper) {
        this.sysPermissionMapper = sysPermissionMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.sysPermissionSearchRepository = sysPermissionSearchRepository;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "SysPermissionService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, SysPermission permission, String action) {
        Objects.requireNonNull(permission, "SysPermission must not be null");
        SysRequestHistory existing = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            log.warning(() -> String.format("Duplicate sys permission request detected (key=%s)", idempotencyKey));
            throw new RuntimeException("Duplicate sys permission request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, permission, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("sys_permission_" + action, idempotencyKey, permission);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysPermission createSysPermission(SysPermission permission) {
        validatePermission(permission);
        sysPermissionMapper.insert(permission);
        syncToIndexAfterCommit(permission);
        return permission;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysPermission updateSysPermission(SysPermission permission) {
        validatePermission(permission);
        requirePositive(permission.getPermissionId());
        int rows = sysPermissionMapper.updateById(permission);
        if (rows == 0) {
            throw new IllegalStateException("SysPermission not found for id=" + permission.getPermissionId());
        }
        syncToIndexAfterCommit(permission);
        return permission;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteSysPermission(Integer permissionId) {
        requirePositive(permissionId);
        int rows = sysPermissionMapper.deleteById(permissionId);
        if (rows == 0) {
            throw new IllegalStateException("SysPermission not found for id=" + permissionId);
        }
        runAfterCommitOrNow(() -> sysPermissionSearchRepository.deleteById(permissionId));
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#permissionId", unless = "#result == null")
    public SysPermission findById(Integer permissionId) {
        requirePositive(permissionId);
        return sysPermissionSearchRepository.findById(permissionId)
                .map(SysPermissionDocument::toEntity)
                .orElseGet(() -> {
                    SysPermission entity = sysPermissionMapper.selectById(permissionId);
                    if (entity != null) {
                        sysPermissionSearchRepository.save(SysPermissionDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<SysPermission> findAll() {
        List<SysPermission> fromIndex = StreamSupport.stream(sysPermissionSearchRepository.findAll().spliterator(), false)
                .map(SysPermissionDocument::toEntity)
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
    public List<SysPermission> findAll(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.orderByAsc("sort_order")
                .orderByAsc("permission_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'parent:' + #parentId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> findByParentId(Integer parentId, int page, int size) {
        requireNonNegative(parentId);
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.findByParentId(parentId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.eq("parent_id", parentId)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'codePrefix:' + #permissionCode + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByPermissionCodePrefix(String permissionCode, int page, int size) {
        if (isBlank(permissionCode)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByPermissionCodePrefix(permissionCode, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.likeRight("permission_code", permissionCode)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'codeFuzzy:' + #permissionCode + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByPermissionCodeFuzzy(String permissionCode, int page, int size) {
        if (isBlank(permissionCode)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByPermissionCodeFuzzy(permissionCode, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.like("permission_code", permissionCode)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'namePrefix:' + #permissionName + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByPermissionNamePrefix(String permissionName, int page, int size) {
        if (isBlank(permissionName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByPermissionNamePrefix(permissionName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.likeRight("permission_name", permissionName)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'nameFuzzy:' + #permissionName + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByPermissionNameFuzzy(String permissionName, int page, int size) {
        if (isBlank(permissionName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByPermissionNameFuzzy(permissionName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.like("permission_name", permissionName)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'type:' + #permissionType + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByPermissionType(String permissionType, int page, int size) {
        if (isBlank(permissionType)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByPermissionType(permissionType, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.eq("permission_type", permissionType)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'apiPath:' + #apiPath + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByApiPathPrefix(String apiPath, int page, int size) {
        if (isBlank(apiPath)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByApiPathPrefix(apiPath, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.likeRight("api_path", apiPath)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'menuPath:' + #menuPath + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByMenuPathPrefix(String menuPath, int page, int size) {
        if (isBlank(menuPath)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByMenuPathPrefix(menuPath, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.likeRight("menu_path", menuPath)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'visible:' + #isVisible + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByIsVisible(boolean isVisible, int page, int size) {
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByIsVisible(isVisible, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.eq("is_visible", isVisible)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'external:' + #isExternal + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByIsExternal(boolean isExternal, int page, int size) {
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByIsExternal(isExternal, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.eq("is_external", isExternal)
                .orderByAsc("sort_order");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'status:' + #status + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysPermission> searchByStatus(String status, int page, int size) {
        if (isBlank(status)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysPermission> index = mapHits(sysPermissionSearchRepository.searchByStatus(status, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
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

    public void markHistorySuccess(String idempotencyKey, Integer permissionId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(permissionId != null ? permissionId.longValue() : null);
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

    private SysRequestHistory buildHistory(String idempotencyKey, SysPermission permission, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/sys/permissions");
        history.setRequestParams(buildRequestParams(permission));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(SysPermission permission) {
        if (permission == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "permissionCode", permission.getPermissionCode());
        appendParam(builder, "permissionName", permission.getPermissionName());
        appendParam(builder, "permissionType", permission.getPermissionType());
        appendParam(builder, "apiPath", permission.getApiPath());
        appendParam(builder, "menuPath", permission.getMenuPath());
        appendParam(builder, "status", permission.getStatus());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "SYS_PERMISSION_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, SysPermission permission) {
        try {
            String payload = objectMapper.writeValueAsString(permission);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send SysPermission Kafka message", ex);
            throw new RuntimeException("Failed to send sys permission event", ex);
        }
    }

    private void syncToIndexAfterCommit(SysPermission permission) {
        if (permission == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            SysPermissionDocument doc = SysPermissionDocument.fromEntity(permission);
            if (doc != null) {
                sysPermissionSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<SysPermission> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<SysPermissionDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(SysPermissionDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                sysPermissionSearchRepository.saveAll(documents);
            }
        });
    }

    private List<SysPermission> fetchFromDatabase(QueryWrapper<SysPermission> wrapper, int page, int size) {
        Page<SysPermission> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        sysPermissionMapper.selectPage(mpPage, wrapper);
        List<SysPermission> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<SysPermission> loadAllFromDatabase() {
        List<SysPermission> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
            wrapper.orderByAsc("permission_id");
            Page<SysPermission> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            sysPermissionMapper.selectPage(mpPage, wrapper);
            List<SysPermission> records = mpPage.getRecords();
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

    private List<SysPermission> mapHits(org.springframework.data.elasticsearch.core.SearchHits<SysPermissionDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(SysPermissionDocument::toEntity)
                .collect(Collectors.toList());
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validatePermission(SysPermission permission) {
        if (permission == null) {
            throw new IllegalArgumentException("SysPermission must not be null");
        }
        if (permission.getPermissionCode() == null || permission.getPermissionCode().isBlank()) {
            throw new IllegalArgumentException("Permission code must not be blank");
        }
        if (permission.getPermissionName() == null || permission.getPermissionName().isBlank()) {
            throw new IllegalArgumentException("Permission name must not be blank");
        }
        if (permission.getCreatedAt() == null) {
            permission.setCreatedAt(LocalDateTime.now());
        }
        if (permission.getUpdatedAt() == null) {
            permission.setUpdatedAt(LocalDateTime.now());
        }
        if (permission.getStatus() == null || permission.getStatus().isBlank()) {
            permission.setStatus("Active");
        }
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private void requirePositive(Number number) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException("Permission ID" + " must be greater than zero");
        }
    }

    private void requireNonNegative(Number number) {
        if (number != null && number.intValue() < 0) {
            throw new IllegalArgumentException("Parent ID" + " must be >= 0");
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
