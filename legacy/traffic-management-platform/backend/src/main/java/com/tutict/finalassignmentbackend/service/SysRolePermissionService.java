package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysRolePermission;
import com.tutict.finalassignmentbackend.entity.elastic.SysRolePermissionDocument;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.SysRolePermissionMapper;
import com.tutict.finalassignmentbackend.repository.SysRolePermissionSearchRepository;
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

@Service
public class SysRolePermissionService {

    private static final Logger log = Logger.getLogger(SysRolePermissionService.class.getName());
    private static final String CACHE_NAME = "sysRolePermissionCache";

    private final SysRolePermissionMapper sysRolePermissionMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final SysRolePermissionSearchRepository sysRolePermissionSearchRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public SysRolePermissionService(SysRolePermissionMapper sysRolePermissionMapper,
                                    SysRequestHistoryMapper sysRequestHistoryMapper,
                                    SysRolePermissionSearchRepository sysRolePermissionSearchRepository,
                                    KafkaTemplate<String, String> kafkaTemplate,
                                    ObjectMapper objectMapper) {
        this.sysRolePermissionMapper = sysRolePermissionMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.sysRolePermissionSearchRepository = sysRolePermissionSearchRepository;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "SysRolePermissionService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, SysRolePermission relation, String action) {
        Objects.requireNonNull(relation, "SysRolePermission must not be null");
        SysRequestHistory existing = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            log.warning(() -> String.format("Duplicate role-permission request detected (key=%s)", idempotencyKey));
            throw new RuntimeException("Duplicate role-permission request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, relation, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("sys_role_permission_" + action, idempotencyKey, relation);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysRolePermission createRelation(SysRolePermission relation) {
        validateRelation(relation);
        sysRolePermissionMapper.insert(relation);
        syncToIndexAfterCommit(relation);
        return relation;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysRolePermission updateRelation(SysRolePermission relation) {
        throw new IllegalStateException("Role-permission bindings cannot be manually updated; recreate the binding instead");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysRolePermission updateRelationSystemManaged(SysRolePermission relation) {
        validateRelation(relation);
        requirePositive(relation.getId(), "Relation ID");
        SysRolePermission existing = sysRolePermissionMapper.selectById(relation.getId());
        if (existing == null) {
            throw new IllegalStateException("SysRolePermission not found for id=" + relation.getId());
        }
        ensureRelationIdentityIsStable(relation, existing);
        relation.setRoleId(existing.getRoleId());
        relation.setPermissionId(existing.getPermissionId());
        relation.setCreatedAt(existing.getCreatedAt());
        relation.setCreatedBy(existing.getCreatedBy());
        int rows = sysRolePermissionMapper.updateById(relation);
        if (rows == 0) {
            throw new IllegalStateException("SysRolePermission not found for id=" + relation.getId());
        }
        syncToIndexAfterCommit(relation);
        return relation;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteRelation(Long id) {
        requirePositive(id, "Relation ID");
        int rows = sysRolePermissionMapper.deleteById(id);
        if (rows == 0) {
            throw new IllegalStateException("SysRolePermission not found for id=" + id);
        }
        runAfterCommitOrNow(() -> sysRolePermissionSearchRepository.deleteById(id));
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#id", unless = "#result == null")
    public SysRolePermission findById(Long id) {
        requirePositive(id, "Relation ID");
        return sysRolePermissionSearchRepository.findById(id)
                .map(SysRolePermissionDocument::toEntity)
                .orElseGet(() -> {
                    SysRolePermission entity = sysRolePermissionMapper.selectById(id);
                    if (entity != null) {
                        sysRolePermissionSearchRepository.save(SysRolePermissionDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'role:' + #roleId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRolePermission> findByRoleId(Integer roleId, int page, int size) {
        requirePositive(roleId, "Role ID");
        validatePagination(page, size);
        List<SysRolePermission> index = mapHits(sysRolePermissionSearchRepository.findByRoleId(roleId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRolePermission> wrapper = new QueryWrapper<>();
        wrapper.eq("role_id", roleId);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'permission:' + #permissionId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRolePermission> findByPermissionId(Integer permissionId, int page, int size) {
        requirePositive(permissionId, "Permission ID");
        validatePagination(page, size);
        List<SysRolePermission> index = mapHits(sysRolePermissionSearchRepository.findByPermissionId(permissionId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRolePermission> wrapper = new QueryWrapper<>();
        wrapper.eq("permission_id", permissionId);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'rolePermission:' + #roleId + ':' + #permissionId + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysRolePermission> findByRoleIdAndPermissionId(Integer roleId, Integer permissionId, int page, int size) {
        requirePositive(roleId, "Role ID");
        requirePositive(permissionId, "Permission ID");
        validatePagination(page, size);
        List<SysRolePermission> index = mapHits(sysRolePermissionSearchRepository.findByRoleIdAndPermissionId(roleId, permissionId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysRolePermission> wrapper = new QueryWrapper<>();
        wrapper.eq("role_id", roleId)
                .eq("permission_id", permissionId);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'all:' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysRolePermission> findAll(int page, int size) {
        validatePagination(page, size);
        Page<SysRolePermission> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        sysRolePermissionMapper.selectPage(mpPage, new QueryWrapper<>());
        List<SysRolePermission> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long relationId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(relationId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, SysRolePermission relation, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/sys/role-permissions");
        history.setRequestParams(buildRequestParams(relation));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(SysRolePermission relation) {
        if (relation == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "roleId", relation.getRoleId());
        appendParam(builder, "permissionId", relation.getPermissionId());
        appendParam(builder, "createdBy", relation.getCreatedBy());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "SYS_ROLE_PERMISSION_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, SysRolePermission relation) {
        try {
            String payload = objectMapper.writeValueAsString(relation);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send SysRolePermission Kafka message", ex);
            throw new RuntimeException("Failed to send sys role permission event", ex);
        }
    }

    private void syncToIndexAfterCommit(SysRolePermission relation) {
        if (relation == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            SysRolePermissionDocument doc = SysRolePermissionDocument.fromEntity(relation);
            if (doc != null) {
                sysRolePermissionSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<SysRolePermission> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<SysRolePermissionDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(SysRolePermissionDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                sysRolePermissionSearchRepository.saveAll(documents);
            }
        });
    }

    private List<SysRolePermission> fetchFromDatabase(QueryWrapper<SysRolePermission> wrapper, int page, int size) {
        Page<SysRolePermission> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        sysRolePermissionMapper.selectPage(mpPage, wrapper);
        List<SysRolePermission> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<SysRolePermission> mapHits(org.springframework.data.elasticsearch.core.SearchHits<SysRolePermissionDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(SysRolePermissionDocument::toEntity)
                .collect(Collectors.toList());
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validateRelation(SysRolePermission relation) {
        if (relation == null) {
            throw new IllegalArgumentException("SysRolePermission must not be null");
        }
        requirePositive(relation.getRoleId(), "Role ID");
        requirePositive(relation.getPermissionId(), "Permission ID");
        if (relation.getCreatedAt() == null) {
            relation.setCreatedAt(LocalDateTime.now());
        }
    }

    private void ensureRelationIdentityIsStable(SysRolePermission relation, SysRolePermission existing) {
        if (relation == null || existing == null) {
            return;
        }
        if (relation.getRoleId() != null && !relation.getRoleId().equals(existing.getRoleId())) {
            throw new IllegalStateException("Role ID cannot be changed for an existing role-permission binding");
        }
        if (relation.getPermissionId() != null && !relation.getPermissionId().equals(existing.getPermissionId())) {
            throw new IllegalStateException("Permission ID cannot be changed for an existing role-permission binding");
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
