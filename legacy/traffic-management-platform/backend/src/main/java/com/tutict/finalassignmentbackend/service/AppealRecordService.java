package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealAcceptanceState;
import com.tutict.finalassignmentbackend.config.statemachine.events.OffenseProcessEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.OffenseProcessState;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.AppealReview;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.AppealRecordDocument;
import com.tutict.finalassignmentbackend.mapper.AppealRecordMapper;
import com.tutict.finalassignmentbackend.mapper.AppealReviewMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.AppealRecordSearchRepository;
import com.tutict.finalassignmentbackend.service.statemachine.StateMachineService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.domain.Pageable;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;

@Service
public class AppealRecordService {

    private static final Logger log = Logger.getLogger(AppealRecordService.class.getName());
    private static final String CACHE = "appealRecordCache";

    private final AppealRecordMapper appealRecordMapper;
    private final AppealReviewMapper appealReviewMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final AppealRecordSearchRepository appealRecordSearchRepository;
    private final OffenseRecordService offenseRecordService;
    private final SysUserService sysUserService;
    private final StateMachineService stateMachineService;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public AppealRecordService(AppealRecordMapper appealRecordMapper,
                               AppealReviewMapper appealReviewMapper,
                               SysRequestHistoryMapper sysRequestHistoryMapper,
                               KafkaTemplate<String, String> kafkaTemplate,
                               AppealRecordSearchRepository appealRecordSearchRepository,
                               OffenseRecordService offenseRecordService,
                               SysUserService sysUserService,
                               StateMachineService stateMachineService,
                               ObjectMapper objectMapper) {
        this.appealRecordMapper = appealRecordMapper;
        this.appealReviewMapper = appealReviewMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.kafkaTemplate = kafkaTemplate;
        this.appealRecordSearchRepository = appealRecordSearchRepository;
        this.offenseRecordService = offenseRecordService;
        this.sysUserService = sysUserService;
        this.stateMachineService = stateMachineService;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE, allEntries = true)
    @WsAction(service = "AppealRecordService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, AppealRecord appealRecord, String action) {
        Objects.requireNonNull(appealRecord, "Appeal record cannot be null");
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history != null) {
            throw new RuntimeException("Duplicate appeal request detected");
        }

        SysRequestHistory newHistory = buildHistory(idempotencyKey, appealRecord, action);
        sysRequestHistoryMapper.insert(newHistory);
        sendKafkaMessage("appeal_" + action, idempotencyKey, appealRecord);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE, allEntries = true)
    public AppealRecord createAppeal(AppealRecord appealRecord) {
        applyInitialWorkflowState(appealRecord);
        validateAppeal(appealRecord);
        syncOffenseForAppealCreation(appealRecord.getOffenseId());
        appealRecordMapper.insert(appealRecord);
        syncIndexAfterCommit(appealRecord);
        return appealRecord;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE, allEntries = true)
    public AppealRecord updateAppeal(AppealRecord appealRecord) {
        throw new IllegalStateException("Appeal records are audit evidence and cannot be manually updated");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE, allEntries = true)
    public AppealRecord updateSupplementFieldsSystemManaged(Long appealId, AppealRecord supplementDraft) {
        validateAppealId(appealId);
        if (supplementDraft == null) {
            throw new IllegalArgumentException("Appeal supplement draft cannot be null");
        }
        AppealRecord existing = appealRecordMapper.selectById(appealId);
        if (existing == null) {
            throw new IllegalStateException("Appeal not found: " + appealId);
        }
        ensureSupplementUpdateAllowed(existing);

        String normalizedAppealReason = normalizeReason(supplementDraft.getAppealReason());
        if (normalizedAppealReason != null) {
            existing.setAppealReason(normalizedAppealReason);
        }
        if (supplementDraft.getAppealReason() != null && normalizedAppealReason == null) {
            throw new IllegalArgumentException("Appeal reason is required");
        }
        if (supplementDraft.getEvidenceDescription() != null) {
            existing.setEvidenceDescription(normalizeSupplementField(supplementDraft.getEvidenceDescription()));
        }
        if (supplementDraft.getEvidenceUrls() != null) {
            existing.setEvidenceUrls(normalizeSupplementField(supplementDraft.getEvidenceUrls()));
        }

        existing.setUpdatedAt(LocalDateTime.now());
        int rows = appealRecordMapper.updateById(existing);
        if (rows == 0) {
            throw new IllegalStateException("Appeal not found: " + appealId);
        }
        syncIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE, allEntries = true)
    public AppealRecord updateAppealSystemManaged(AppealRecord appealRecord) {
        AppealRecord existing = appealRecordMapper.selectById(appealRecord.getAppealId());
        if (existing == null) {
            throw new IllegalStateException("Appeal not found: " + appealRecord.getAppealId());
        }
        preserveWorkflowManagedFields(appealRecord, existing);
        validateAppealId(appealRecord);
        int rows = appealRecordMapper.updateById(appealRecord);
        if (rows == 0) {
            throw new IllegalStateException("Appeal not found: " + appealRecord.getAppealId());
        }
        syncIndexAfterCommit(appealRecord);
        return appealRecord;
    }

    /**
     * 供工作流调用的状态更新方法，只改 processStatus 字段
     */
    @Transactional
    public AppealRecord updateProcessStatus(Long appealId, AppealProcessState newState) {
        return updateProcessStatus(appealId, newState, null);
    }

    @Transactional
    public AppealRecord updateProcessStatus(Long appealId,
                                            AppealProcessState newState,
                                            String processResult) {
        validateAppealId(appealId);
        AppealRecord existing = appealRecordMapper.selectById(appealId);
        if (existing == null) {
            throw new IllegalStateException("Appeal not found: " + appealId);
        }
        existing.setProcessStatus(newState != null ? newState.getCode() : existing.getProcessStatus());
        if (newState == AppealProcessState.UNPROCESSED) {
            existing.setProcessTime(null);
            existing.setProcessHandler(null);
            existing.setProcessResult(null);
        } else {
            existing.setProcessTime(LocalDateTime.now());
            existing.setProcessHandler(resolveOperatorName(existing.getProcessHandler()));
            existing.setProcessResult(normalizeProcessResult(processResult, newState, existing.getProcessResult()));
        }
        existing.setUpdatedAt(LocalDateTime.now());
        appealRecordMapper.updateById(existing);
        syncOffenseForAppealState(existing.getOffenseId(), newState);
        syncIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    public AppealRecord updateAcceptanceStatus(Long appealId, AppealAcceptanceState newState) {
        return updateAcceptanceStatus(appealId, newState, null);
    }

    @Transactional
    public AppealRecord updateAcceptanceStatus(Long appealId, AppealAcceptanceState newState, String rejectionReason) {
        validateAppealId(appealId);
        AppealRecord existing = appealRecordMapper.selectById(appealId);
        if (existing == null) {
            throw new IllegalStateException("Appeal not found: " + appealId);
        }
        if (rejectionReason != null) {
            existing.setRejectionReason(rejectionReason);
        }
        ensureAcceptanceReasonPresent(existing, newState);
        existing.setAcceptanceStatus(newState != null ? newState.getCode() : existing.getAcceptanceStatus());
        if (newState == AppealAcceptanceState.PENDING) {
            existing.setAcceptanceTime(null);
            existing.setAcceptanceHandler(null);
            existing.setRejectionReason(null);
        } else {
            existing.setAcceptanceTime(LocalDateTime.now());
            existing.setAcceptanceHandler(resolveOperatorName(existing.getAcceptanceHandler()));
            if (newState == AppealAcceptanceState.ACCEPTED) {
                existing.setRejectionReason(null);
            }
        }
        if (newState != AppealAcceptanceState.ACCEPTED) {
            existing.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
            existing.setProcessTime(null);
            existing.setProcessHandler(null);
            existing.setProcessResult(null);
        }
        existing.setRejectionReason(normalizeReason(existing.getRejectionReason()));
        existing.setUpdatedAt(LocalDateTime.now());
        appealRecordMapper.updateById(existing);
        syncOffenseForAcceptanceState(existing.getOffenseId(), newState);
        syncIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE, allEntries = true)
    public void deleteAppeal(Long appealId) {
        throw new IllegalStateException("Appeal records are audit evidence and cannot be manually deleted");
    }

    @Cacheable(cacheNames = CACHE, key = "#appealId", unless = "#result == null")
    public AppealRecord getAppealById(Long appealId) {
        validateAppealId(appealId);
        return appealRecordSearchRepository.findById(appealId)
                .map(AppealRecordDocument::toEntity)
                .orElseGet(() -> {
                    AppealRecord entity = appealRecordMapper.selectById(appealId);
                    if (entity != null) {
                        appealRecordSearchRepository.save(AppealRecordDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Cacheable(cacheNames = CACHE, key = "'offense:' + #offenseId", unless = "#result.isEmpty()")
    public List<AppealRecord> findByOffenseId(Long offenseId, int page, int size) {
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.findByOffenseId(offenseId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_id", offenseId)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<AppealRecord> listAppeals(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("appeal_time")
                .orderByDesc("appeal_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<AppealRecord> findByOffenseIds(Iterable<Long> offenseIds, int page, int size) {
        List<Long> normalizedIds = normalizePositiveIds(offenseIds);
        validatePagination(page, size);
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.in("offense_id", normalizedIds)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<AppealRecord> findByOffenseIds(Iterable<Long> offenseIds) {
        List<Long> normalizedIds = normalizePositiveIds(offenseIds);
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.in("offense_id", normalizedIds)
                .orderByDesc("appeal_time");
        return appealRecordMapper.selectList(wrapper);
    }

    @Cacheable(cacheNames = CACHE, key = "'appealNumberPrefix:' + #appealNumber + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAppealNumberPrefix(String appealNumber, int page, int size) {
        if (isBlank(appealNumber)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAppealNumberPrefix(appealNumber, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.likeRight("appeal_number", appealNumber)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'appealNumberFuzzy:' + #appealNumber + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAppealNumberFuzzy(String appealNumber, int page, int size) {
        if (isBlank(appealNumber)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAppealNumberFuzzy(appealNumber, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.like("appeal_number", appealNumber)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'appealReasonFuzzy:' + #appealReason + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAppealReasonFuzzy(String appealReason, int page, int size) {
        if (isBlank(appealReason)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAppealReasonFuzzy(appealReason, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.like("appeal_reason", appealReason)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'appellantNamePrefix:' + #appellantName + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAppellantNamePrefix(String appellantName, int page, int size) {
        if (isBlank(appellantName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAppellantNamePrefix(appellantName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.likeRight("appellant_name", appellantName)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'appellantNameFuzzy:' + #appellantName + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAppellantNameFuzzy(String appellantName, int page, int size) {
        if (isBlank(appellantName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAppellantNameFuzzy(appellantName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.like("appellant_name", appellantName)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'appellantIdCard:' + #appellantIdCard + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAppellantIdCard(String appellantIdCard, int page, int size) {
        if (isBlank(appellantIdCard)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAppellantIdCard(appellantIdCard, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("appellant_id_card", appellantIdCard)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'acceptanceStatus:' + #acceptanceStatus + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAcceptanceStatus(String acceptanceStatus, int page, int size) {
        if (isBlank(acceptanceStatus)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAcceptanceStatus(acceptanceStatus, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("acceptance_status", acceptanceStatus)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'processStatus:' + #processStatus + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByProcessStatus(String processStatus, int page, int size) {
        if (isBlank(processStatus)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByProcessStatus(processStatus, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("process_status", processStatus)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'appealTimeRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAppealTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAppealTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.between("appeal_time", start, end)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE, key = "'acceptanceHandler:' + #acceptanceHandler + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealRecord> searchByAcceptanceHandler(String acceptanceHandler, int page, int size) {
        if (isBlank(acceptanceHandler)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealRecord> index = mapHits(appealRecordSearchRepository.searchByAcceptanceHandler(acceptanceHandler, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.likeRight("acceptance_handler", acceptanceHandler)
                .orderByDesc("appeal_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    private SysRequestHistory buildHistory(String key, AppealRecord appealRecord, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(key);
        history.setRequestMethod(resolveRequestMethod("POST"));
        history.setRequestUrl(resolveRequestUrl("/api/appeals"));
        history.setRequestParams(buildRequestParams(appealRecord));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setUserId(resolveCurrentUserId());
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long appealId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(appealId);
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

    private String buildRequestParams(AppealRecord appealRecord) {
        if (appealRecord == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "offenseId", appealRecord.getOffenseId());
        appendParam(builder, "appealTime", appealRecord.getAppealTime());
        appendParam(builder, "appellantName", appealRecord.getAppellantName());
        appendParam(builder, "appellantIdCard", appealRecord.getAppellantIdCard());
        appendParam(builder, "appellantContact", appealRecord.getAppellantContact());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "APPEAL_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, AppealRecord appealRecord) {
        try {
            String payload = objectMapper.writeValueAsString(appealRecord);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception e) {
            log.log(Level.WARNING, "Failed to send appeal Kafka message", e);
            throw new RuntimeException("Failed to send appeal record event", e);
        }
    }

    private void syncIndexAfterCommit(AppealRecord appealRecord) {
        runAfterCommitOrNow(() -> {
            AppealRecordDocument doc = AppealRecordDocument.fromEntity(appealRecord);
            if (doc != null) {
                appealRecordSearchRepository.save(doc);
            }
        });
    }

    private String resolveRequestMethod(String fallback) {
        RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
        if (!(requestAttributes instanceof ServletRequestAttributes servletRequestAttributes)) {
            return fallback;
        }
        HttpServletRequest request = servletRequestAttributes.getRequest();
        if (request == null || isBlank(request.getMethod())) {
            return fallback;
        }
        return request.getMethod().trim().toUpperCase();
    }

    private String resolveRequestUrl(String fallback) {
        RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
        if (!(requestAttributes instanceof ServletRequestAttributes servletRequestAttributes)) {
            return fallback;
        }
        HttpServletRequest request = servletRequestAttributes.getRequest();
        if (request == null || isBlank(request.getRequestURI())) {
            return fallback;
        }
        return request.getRequestURI().trim();
    }

    private Long resolveCurrentUserId() {
        String operatorName = resolveOperatorName(null);
        if (isBlank(operatorName)) {
            return null;
        }
        SysUser user = sysUserService.findByUsername(operatorName);
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

    private List<AppealRecord> fetchFromDatabase(QueryWrapper<AppealRecord> wrapper, int page, int size) {
        Page<AppealRecord> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        appealRecordMapper.selectPage(mpPage, wrapper);
        List<AppealRecord> records = mpPage.getRecords();
        records.stream()
                .map(AppealRecordDocument::fromEntity)
                .filter(Objects::nonNull)
                .forEach(appealRecordSearchRepository::save);
        return records;
    }

    private List<AppealRecord> mapHits(SearchHits<AppealRecordDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(SearchHit::getContent)
                .map(AppealRecordDocument::toEntity)
                .collect(Collectors.toList());
    }

    private Pageable pageable(int page, int size) {
        return PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
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

    private void validateAppeal(AppealRecord appealRecord) {
        if (appealRecord == null) {
            throw new IllegalArgumentException("Appeal record cannot be null");
        }
        if (appealRecord.getOffenseId() == null) {
            throw new IllegalArgumentException("Offense ID is required");
        }
        OffenseRecord offense = offenseRecordService.findById(appealRecord.getOffenseId());
        if (offense == null) {
            throw new IllegalArgumentException("Offense record does not exist");
        }
        if (appealRecord.getAppealId() != null) {
            AppealRecord existing = appealRecordMapper.selectById(appealRecord.getAppealId());
            if (existing != null
                    && existing.getOffenseId() != null
                    && !Objects.equals(existing.getOffenseId(), appealRecord.getOffenseId())) {
                throw new IllegalArgumentException("Offense ID cannot be changed for an existing appeal");
            }
        }
        ensureNoDuplicateAppeal(appealRecord);
        if (appealRecord.getAppealTime() == null) {
            appealRecord.setAppealTime(LocalDateTime.now());
        }
        if (isBlank(appealRecord.getAcceptanceStatus())) {
            appealRecord.setAcceptanceStatus("Pending");
        }
        if (isBlank(appealRecord.getProcessStatus())) {
            appealRecord.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
        }
        appealRecord.setAppealReason(normalizeReason(appealRecord.getAppealReason()));
        if (isBlank(appealRecord.getAppealReason())) {
            throw new IllegalArgumentException("Appeal reason is required");
        }
        appealRecord.setRejectionReason(normalizeReason(appealRecord.getRejectionReason()));
        ensureAcceptanceReasonPresent(appealRecord, AppealAcceptanceState.fromCode(appealRecord.getAcceptanceStatus()));
    }

    private void applyInitialWorkflowState(AppealRecord appealRecord) {
        if (appealRecord == null) {
            return;
        }
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.PENDING.getCode());
        appealRecord.setAcceptanceTime(null);
        appealRecord.setAcceptanceHandler(null);
        appealRecord.setRejectionReason(null);
        appealRecord.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
        appealRecord.setProcessTime(null);
        appealRecord.setProcessResult(null);
        appealRecord.setProcessHandler(null);
    }

    private void preserveWorkflowManagedFields(AppealRecord appealRecord, AppealRecord existing) {
        if (appealRecord == null || existing == null) {
            return;
        }
        appealRecord.setOffenseId(existing.getOffenseId());
        appealRecord.setAppealNumber(existing.getAppealNumber());
        appealRecord.setAppellantName(existing.getAppellantName());
        appealRecord.setAppellantIdCard(existing.getAppellantIdCard());
        appealRecord.setAppellantContact(existing.getAppellantContact());
        appealRecord.setAppellantEmail(existing.getAppellantEmail());
        appealRecord.setAppellantAddress(existing.getAppellantAddress());
        appealRecord.setAppealType(existing.getAppealType());
        appealRecord.setAppealReason(existing.getAppealReason());
        appealRecord.setAppealTime(existing.getAppealTime());
        appealRecord.setEvidenceDescription(existing.getEvidenceDescription());
        appealRecord.setEvidenceUrls(existing.getEvidenceUrls());
        appealRecord.setAcceptanceStatus(existing.getAcceptanceStatus());
        appealRecord.setAcceptanceTime(existing.getAcceptanceTime());
        appealRecord.setAcceptanceHandler(existing.getAcceptanceHandler());
        appealRecord.setRejectionReason(existing.getRejectionReason());
        appealRecord.setProcessStatus(existing.getProcessStatus());
        appealRecord.setProcessTime(existing.getProcessTime());
        appealRecord.setProcessResult(existing.getProcessResult());
        appealRecord.setProcessHandler(existing.getProcessHandler());
    }

    private void validateAppealId(AppealRecord appealRecord) {
        validateAppeal(appealRecord);
        validateAppealId(appealRecord.getAppealId());
    }

    private void validateAppealId(Long appealId) {
        if (appealId == null || appealId <= 0) {
            throw new IllegalArgumentException("Invalid appeal ID: " + appealId);
        }
    }

    private String truncate(String value) {
        if (value == null) {
            return null;
        }
        return value.length() <= 500 ? value : value.substring(0, 500);
    }

    private void ensureNoDuplicateAppeal(AppealRecord appealRecord) {
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_id", appealRecord.getOffenseId())
                .orderByDesc("appeal_time")
                .orderByDesc("appeal_id");
        List<AppealRecord> existingAppeals = appealRecordMapper.selectList(wrapper);
        for (AppealRecord existing : existingAppeals) {
            if (existing == null) {
                continue;
            }
            if (Objects.equals(existing.getAppealId(), appealRecord.getAppealId())) {
                continue;
            }
            AppealProcessState processState = AppealProcessState.fromCode(trimToEmpty(existing.getProcessStatus()));
            if (processState == AppealProcessState.WITHDRAWN) {
                continue;
            }
            AppealAcceptanceState acceptanceState =
                    AppealAcceptanceState.fromCode(trimToEmpty(existing.getAcceptanceStatus()));
            if (acceptanceState == AppealAcceptanceState.REJECTED) {
                throw new IllegalStateException(
                        "A rejected appeal already exists for this offense; please resubmit the existing appeal");
            }
            if (acceptanceState == AppealAcceptanceState.NEED_SUPPLEMENT) {
                throw new IllegalStateException(
                        "An appeal for this offense is waiting for supplemental materials");
            }
            throw new IllegalStateException("An active appeal already exists for this offense");
        }
    }

    private void syncOffenseForAppealCreation(Long offenseId) {
        OffenseRecord offense = requireOffense(offenseId);
        OffenseProcessState currentState = resolveOffenseState(offense.getProcessStatus());
        OffenseProcessEvent event = OffenseProcessEvent.SUBMIT_APPEAL;
        if (!stateMachineService.canTransitionOffenseState(currentState, event)) {
            throw new IllegalStateException("Offense is not eligible for appeal");
        }
        OffenseProcessState newState = stateMachineService.processOffenseState(offenseId, currentState, event);
        if (newState == currentState) {
            throw new IllegalStateException("Offense state did not transition to appealing");
        }
        offenseRecordService.updateProcessStatus(offenseId, newState);
    }

    private void syncOffenseForAppealState(Long offenseId, AppealProcessState appealState) {
        if (offenseId == null || appealState == null) {
            return;
        }
        OffenseRecord offense = requireOffense(offenseId);
        OffenseProcessState currentState = resolveOffenseState(offense.getProcessStatus());
        OffenseProcessState targetState = targetOffenseStateForAppeal(appealState);
        if (targetState == null || currentState == targetState) {
            return;
        }

        OffenseProcessEvent event = offenseEventForAppeal(appealState);
        if (event == null || !stateMachineService.canTransitionOffenseState(currentState, event)) {
            throw new IllegalStateException("Offense state is out of sync with appeal state");
        }

        OffenseProcessState newState = stateMachineService.processOffenseState(offenseId, currentState, event);
        if (newState != targetState) {
            throw new IllegalStateException("Offense state did not transition to the expected appeal status");
        }
        offenseRecordService.updateProcessStatus(offenseId, newState);
    }

    private OffenseRecord requireOffense(Long offenseId) {
        OffenseRecord offense = offenseRecordService.findById(offenseId);
        if (offense == null) {
            throw new IllegalStateException("Offense not found: " + offenseId);
        }
        return offense;
    }

    private OffenseProcessState resolveOffenseState(String code) {
        OffenseProcessState state = OffenseProcessState.fromCode(code);
        return state != null ? state : OffenseProcessState.UNPROCESSED;
    }

    private OffenseProcessState targetOffenseStateForAppeal(AppealProcessState appealState) {
        return switch (appealState) {
            case UNPROCESSED, UNDER_REVIEW -> OffenseProcessState.APPEALING;
            case APPROVED -> OffenseProcessState.APPEAL_APPROVED;
            case REJECTED -> OffenseProcessState.APPEAL_REJECTED;
            case WITHDRAWN -> OffenseProcessState.PROCESSED;
        };
    }

    private OffenseProcessEvent offenseEventForAppeal(AppealProcessState appealState) {
        return switch (appealState) {
            case UNPROCESSED, UNDER_REVIEW -> OffenseProcessEvent.SUBMIT_APPEAL;
            case APPROVED -> OffenseProcessEvent.APPROVE_APPEAL;
            case REJECTED -> OffenseProcessEvent.REJECT_APPEAL;
            case WITHDRAWN -> OffenseProcessEvent.WITHDRAW_APPEAL;
        };
    }

    private void syncOffenseForAcceptanceState(Long offenseId, AppealAcceptanceState acceptanceState) {
        if (offenseId == null || acceptanceState == null) {
            return;
        }
        OffenseRecord offense = requireOffense(offenseId);
        OffenseProcessState currentState = resolveOffenseState(offense.getProcessStatus());
        OffenseProcessState targetState = targetOffenseStateForAcceptance(acceptanceState);
        if (targetState == null || currentState == targetState) {
            return;
        }
        OffenseProcessEvent event = offenseEventForAcceptance(currentState, acceptanceState);
        if (event == null || !stateMachineService.canTransitionOffenseState(currentState, event)) {
            throw new IllegalStateException("Offense state is out of sync with appeal acceptance state");
        }
        OffenseProcessState newState = stateMachineService.processOffenseState(offenseId, currentState, event);
        if (newState != targetState) {
            throw new IllegalStateException("Offense state did not transition to the expected acceptance status");
        }
        offenseRecordService.updateProcessStatus(offenseId, newState);
    }

    private OffenseProcessState targetOffenseStateForAcceptance(AppealAcceptanceState acceptanceState) {
        return switch (acceptanceState) {
            case PENDING, ACCEPTED, NEED_SUPPLEMENT -> OffenseProcessState.APPEALING;
            case REJECTED -> OffenseProcessState.PROCESSED;
        };
    }

    private OffenseProcessEvent offenseEventForAcceptance(OffenseProcessState currentState,
                                                          AppealAcceptanceState acceptanceState) {
        if (acceptanceState == null) {
            return null;
        }
        return switch (acceptanceState) {
            case PENDING, ACCEPTED, NEED_SUPPLEMENT -> switch (currentState) {
                case PROCESSED, APPEAL_REJECTED -> OffenseProcessEvent.SUBMIT_APPEAL;
                default -> null;
            };
            case REJECTED -> currentState == OffenseProcessState.APPEALING
                    ? OffenseProcessEvent.WITHDRAW_APPEAL
                    : null;
        };
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private String resolveOperatorName(String fallback) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken
                || authentication.getName() == null
                || authentication.getName().isBlank()) {
            return fallback;
        }
        return authentication.getName();
    }

    private String normalizeReason(String value) {
        if (isBlank(value)) {
            return null;
        }
        return truncate(value.trim());
    }

    private String normalizeProcessResult(String processResult,
                                          AppealProcessState newState,
                                          String existingProcessResult) {
        String normalized = normalizeReason(processResult);
        if (newState == AppealProcessState.UNPROCESSED || newState == AppealProcessState.UNDER_REVIEW) {
            return null;
        }
        if (normalized != null) {
            return normalized;
        }
        if (!isBlank(existingProcessResult)) {
            return truncate(existingProcessResult.trim());
        }
        return newState == null ? null : newState.getCode();
    }

    private void ensureAcceptanceReasonPresent(AppealRecord appealRecord, AppealAcceptanceState targetState) {
        if (targetState != AppealAcceptanceState.REJECTED
                && targetState != AppealAcceptanceState.NEED_SUPPLEMENT) {
            return;
        }
        if (appealRecord == null || isBlank(appealRecord.getRejectionReason())) {
            throw new IllegalArgumentException("Rejection reason is required for rejected or supplement-needed appeals");
        }
    }

    private void ensureSupplementUpdateAllowed(AppealRecord appealRecord) {
        AppealAcceptanceState acceptanceState =
                AppealAcceptanceState.fromCode(trimToEmpty(appealRecord.getAcceptanceStatus()));
        if (acceptanceState != AppealAcceptanceState.NEED_SUPPLEMENT
                && acceptanceState != AppealAcceptanceState.REJECTED) {
            throw new IllegalStateException("Appeal supplement content can only be updated while awaiting user action");
        }
    }

    private String normalizeSupplementField(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private void syncOffenseAfterAppealDeletion(Long offenseId) {
        if (offenseId == null) {
            return;
        }
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_id", offenseId)
                .orderByDesc("appeal_time")
                .orderByDesc("appeal_id");
        List<AppealRecord> remainingAppeals = appealRecordMapper.selectList(wrapper);
        for (AppealRecord remaining : remainingAppeals) {
            if (remaining == null) {
                continue;
            }
            AppealProcessState appealState = AppealProcessState.fromCode(trimToEmpty(remaining.getProcessStatus()));
            if (appealState != null && appealState != AppealProcessState.WITHDRAWN) {
                syncOffenseForAppealState(offenseId, appealState);
                return;
            }
        }
        OffenseRecord offense = requireOffense(offenseId);
        OffenseProcessState currentState = resolveOffenseState(offense.getProcessStatus());
        if (currentState == OffenseProcessState.APPEALING
                || currentState == OffenseProcessState.APPEAL_APPROVED
                || currentState == OffenseProcessState.APPEAL_REJECTED) {
            offenseRecordService.updateProcessStatus(offenseId, OffenseProcessState.PROCESSED);
        }
    }

    private void ensureAppealCanBeDeleted(AppealRecord appealRecord) {
        QueryWrapper<AppealReview> reviewWrapper = new QueryWrapper<>();
        reviewWrapper.eq("appeal_id", appealRecord.getAppealId());
        if (appealReviewMapper.selectCount(reviewWrapper) > 0) {
            throw new IllegalStateException("Cannot delete appeal after review records have been created");
        }
        AppealProcessState processState = AppealProcessState.fromCode(trimToEmpty(appealRecord.getProcessStatus()));
        if (processState != null
                && processState != AppealProcessState.UNPROCESSED
                && processState != AppealProcessState.WITHDRAWN) {
            throw new IllegalStateException("Cannot delete appeal after processing has started");
        }
        AppealAcceptanceState acceptanceState = AppealAcceptanceState.fromCode(trimToEmpty(appealRecord.getAcceptanceStatus()));
        if (acceptanceState == AppealAcceptanceState.ACCEPTED) {
            throw new IllegalStateException("Cannot delete appeal after acceptance");
        }
    }
}
