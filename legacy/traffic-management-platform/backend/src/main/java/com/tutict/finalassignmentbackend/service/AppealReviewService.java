package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealAcceptanceState;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.AppealReview;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.AppealReviewDocument;
import com.tutict.finalassignmentbackend.mapper.AppealReviewMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.AppealReviewSearchRepository;
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
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class AppealReviewService {

    private static final Logger log = Logger.getLogger(AppealReviewService.class.getName());
    private static final String CACHE_NAME = "appealReviewCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final AppealReviewMapper appealReviewMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final AppealReviewSearchRepository appealReviewSearchRepository;
    private final AppealRecordService appealRecordService;
    private final OffenseRecordService offenseRecordService;
    private final FineRecordService fineRecordService;
    private final DeductionRecordService deductionRecordService;
    private final PaymentRecordService paymentRecordService;
    private final SysUserService sysUserService;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public AppealReviewService(AppealReviewMapper appealReviewMapper,
                               SysRequestHistoryMapper sysRequestHistoryMapper,
                               AppealReviewSearchRepository appealReviewSearchRepository,
                               AppealRecordService appealRecordService,
                               OffenseRecordService offenseRecordService,
                               FineRecordService fineRecordService,
                               DeductionRecordService deductionRecordService,
                               PaymentRecordService paymentRecordService,
                               SysUserService sysUserService,
                               KafkaTemplate<String, String> kafkaTemplate,
                               ObjectMapper objectMapper) {
        this.appealReviewMapper = appealReviewMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.appealReviewSearchRepository = appealReviewSearchRepository;
        this.appealRecordService = appealRecordService;
        this.offenseRecordService = offenseRecordService;
        this.fineRecordService = fineRecordService;
        this.deductionRecordService = deductionRecordService;
        this.paymentRecordService = paymentRecordService;
        this.sysUserService = sysUserService;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "AppealReviewService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, AppealReview appealReview, String action) {
        Objects.requireNonNull(appealReview, "AppealReview must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate appeal review request detected");
        }
        SysRequestHistory history = buildHistory(idempotencyKey, appealReview, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("appeal_review_" + action, idempotencyKey, appealReview);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public AppealReview createReview(AppealReview appealReview) {
        normalizeCreateSystemManagedFields(appealReview);
        validateAppealReview(appealReview, null);
        appealReviewMapper.insert(appealReview);
        applyReviewOutcome(null, appealReview);
        syncToIndexAfterCommit(appealReview);
        return appealReview;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public AppealReview updateReview(AppealReview appealReview) {
        throw new IllegalStateException("Appeal review records are audit evidence and cannot be manually updated");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public AppealReview updateReviewSystemManaged(AppealReview appealReview) {
        requirePositive(appealReview.getReviewId());
        AppealReview existingReview = appealReviewMapper.selectById(appealReview.getReviewId());
        validateAppealReview(appealReview, existingReview);
        int rows = appealReviewMapper.updateById(appealReview);
        if (rows == 0) {
            throw new IllegalStateException("No AppealReview updated for id=" + appealReview.getReviewId());
        }
        applyReviewOutcome(existingReview, appealReview);
        syncToIndexAfterCommit(appealReview);
        return appealReview;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteReview(Long reviewId) {
        throw new IllegalStateException("Appeal review records are audit evidence and cannot be manually deleted");
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "#reviewId", unless = "#result == null")
    public AppealReview findById(Long reviewId) {
        requirePositive(reviewId);
        return appealReviewSearchRepository.findById(reviewId)
                .map(AppealReviewDocument::toEntity)
                .orElseGet(() -> {
                    AppealReview entity = appealReviewMapper.selectById(reviewId);
                    if (entity != null) {
                        appealReviewSearchRepository.save(AppealReviewDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    public List<AppealReview> findAll() {
        List<AppealReview> fromIndex = StreamSupport.stream(appealReviewSearchRepository.findAll().spliterator(), false)
                .map(AppealReviewDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Cacheable(
            cacheNames = CACHE_NAME,
            key = "'all:' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<AppealReview> findAll(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("review_time")
                .orderByDesc("review_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(
            cacheNames = CACHE_NAME,
            key = "'appealId:' + #appealId + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<AppealReview> findByAppealId(Long appealId, int page, int size) {
        requirePositive(appealId);
        validatePagination(page, size);
        QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
        wrapper.eq("appeal_id", appealId)
                .orderByDesc("review_time")
                .orderByDesc("review_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'reviewer:' + #reviewer + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealReview> searchByReviewer(String reviewer, int page, int size) {
        if (isBlank(reviewer)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealReview> index = mapHits(appealReviewSearchRepository.searchByReviewer(reviewer, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
        wrapper.likeRight("reviewer", reviewer)
                .orderByDesc("review_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'reviewerDept:' + #reviewerDept + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealReview> searchByReviewerDept(String reviewerDept, int page, int size) {
        if (isBlank(reviewerDept)) {
            return List.of();
        }
        validatePagination(page, size);
        List<AppealReview> index = mapHits(appealReviewSearchRepository.searchByReviewerDept(reviewerDept, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
        wrapper.likeRight("reviewer_dept", reviewerDept)
                .orderByDesc("review_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'reviewTimeRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<AppealReview> searchByReviewTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<AppealReview> index = mapHits(appealReviewSearchRepository.searchByReviewTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
        wrapper.between("review_time", start, end)
                .orderByDesc("review_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    public long countByReviewLevel(String reviewLevel) {
        if (isBlank(reviewLevel)) {
            return 0L;
        }
        try {
            org.springframework.data.elasticsearch.core.SearchHits<AppealReviewDocument> hits =
                    appealReviewSearchRepository.findByReviewLevel(
                            reviewLevel,
                            org.springframework.data.domain.PageRequest.of(0, 1));
            if (hits != null && hits.getTotalHits() > 0) {
                return hits.getTotalHits();
            }
        } catch (Exception ex) {
            log.log(Level.WARNING, "Failed to count appeal reviews from Elasticsearch", ex);
        }

        QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
        wrapper.eq("review_level", reviewLevel.trim());
        Long count = appealReviewMapper.selectCount(wrapper);
        return count == null ? 0L : count;
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long reviewId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(reviewId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, AppealReview appealReview, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod(resolveRequestMethod("POST"));
        history.setRequestUrl(resolveRequestUrl(resolveDefaultRequestUrl(appealReview)));
        history.setRequestParams(buildRequestParams(appealReview));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setUserId(resolveCurrentUserId());
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String resolveDefaultRequestUrl(AppealReview appealReview) {
        Long appealId = appealReview == null ? null : appealReview.getAppealId();
        return appealId == null ? "/api/appeals/reviews" : "/api/appeals/" + appealId + "/reviews";
    }

    private String buildRequestParams(AppealReview appealReview) {
        if (appealReview == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "appealId", appealReview.getAppealId());
        appendParam(builder, "reviewLevel", appealReview.getReviewLevel());
        appendParam(builder, "reviewResult", appealReview.getReviewResult());
        appendParam(builder, "suggestedAction", appealReview.getSuggestedAction());
        appendParam(builder, "reviewer", appealReview.getReviewer());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "APPEAL_REVIEW_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, AppealReview appealReview) {
        try {
            String payload = objectMapper.writeValueAsString(appealReview);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send AppealReview Kafka message", ex);
            throw new RuntimeException("Failed to send AppealReview event", ex);
        }
    }

    private void syncToIndexAfterCommit(AppealReview appealReview) {
        if (appealReview == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            AppealReviewDocument doc = AppealReviewDocument.fromEntity(appealReview);
            if (doc != null) {
                appealReviewSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<AppealReview> reviews) {
        if (reviews == null || reviews.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<AppealReviewDocument> documents = reviews.stream()
                    .filter(Objects::nonNull)
                    .map(AppealReviewDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                appealReviewSearchRepository.saveAll(documents);
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

    private List<AppealReview> fetchFromDatabase(QueryWrapper<AppealReview> wrapper, int page, int size) {
        Page<AppealReview> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        appealReviewMapper.selectPage(mpPage, wrapper);
        List<AppealReview> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<AppealReview> loadAllFromDatabase() {
        List<AppealReview> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
            wrapper.orderByAsc("review_id");
            Page<AppealReview> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            appealReviewMapper.selectPage(mpPage, wrapper);
            List<AppealReview> records = mpPage.getRecords();
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

    private List<AppealReview> mapHits(org.springframework.data.elasticsearch.core.SearchHits<AppealReviewDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(AppealReviewDocument::toEntity)
                .collect(Collectors.toList());
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void normalizeCreateSystemManagedFields(AppealReview appealReview) {
        if (appealReview == null) {
            return;
        }
        appealReview.setReviewId(null);
        appealReview.setTenantId(null);
        appealReview.setOrganizationCode(null);
        appealReview.setRegionCode(null);
        appealReview.setDepartmentCode(null);
        appealReview.setReviewTime(LocalDateTime.now());
        appealReview.setReviewer(resolveOperatorName());
        appealReview.setReviewerDept(resolveOperatorDepartment());
        appealReview.setCreatedAt(null);
        appealReview.setUpdatedAt(null);
        appealReview.setDeletedAt(null);
    }

    private void validateAppealReview(AppealReview appealReview, AppealReview existingReview) {
        Objects.requireNonNull(appealReview, "AppealReview must not be null");
        requirePositive(appealReview.getAppealId(), "Appeal ID");
        AppealRecord appealRecord = appealRecordService.getAppealById(appealReview.getAppealId());
        if (appealRecord == null) {
            throw new IllegalArgumentException("Appeal does not exist");
        }
        AppealProcessState processState = AppealProcessState.fromCode(appealRecord.getProcessStatus());
        if (existingReview != null) {
            if (existingReview.getAppealId() != null
                    && !Objects.equals(existingReview.getAppealId(), appealReview.getAppealId())) {
                throw new IllegalArgumentException("Appeal ID cannot be changed for an existing review");
            }
            if (isAppealFinalized(processState) && isReviewContentChanged(existingReview, appealReview)) {
                throw new IllegalStateException("Cannot change review records after the appeal has been finalized");
            }
        } else if (isAppealFinalized(processState)) {
            throw new IllegalStateException("Cannot create new reviews after the appeal has been finalized");
        }
        if (AppealAcceptanceState.fromCode(appealRecord.getAcceptanceStatus()) != AppealAcceptanceState.ACCEPTED) {
            throw new IllegalStateException("Appeal must be accepted before reviews can be created");
        }
        if (processState == null || processState == AppealProcessState.UNPROCESSED || processState == AppealProcessState.WITHDRAWN) {
            throw new IllegalStateException("Appeal review cannot be created before the review workflow starts");
        }
        if (appealReview.getReviewLevel() == null || appealReview.getReviewLevel().isBlank()) {
            throw new IllegalArgumentException("Review level must not be blank");
        }
        if (appealReview.getReviewResult() == null || appealReview.getReviewResult().isBlank()) {
            throw new IllegalArgumentException("Review result must not be blank");
        }
        if (appealReview.getReviewTime() == null) {
            appealReview.setReviewTime(LocalDateTime.now());
        }
        if (isBlank(appealReview.getReviewer())) {
            appealReview.setReviewer(resolveOperatorName());
        }
        if (appealReview.getSuggestedFineAmount() != null && appealReview.getSuggestedFineAmount().signum() < 0) {
            throw new IllegalArgumentException("Suggested fine amount must not be negative");
        }
        if (appealReview.getSuggestedPoints() != null && appealReview.getSuggestedPoints() < 0) {
            throw new IllegalArgumentException("Suggested points must not be negative");
        }
        validateSuggestedActionBounds(appealReview, appealRecord);
        ensureSingleReviewPerLevel(appealReview, existingReview);
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private void requirePositive(Number number) {
        requirePositive(number, "Review ID");
    }

    private void requirePositive(Number number, String fieldName) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException(fieldName + " must be greater than zero");
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

    private String resolveOperatorDepartment() {
        String operatorName = resolveOperatorName();
        if (isBlank(operatorName)) {
            return null;
        }
        SysUser user = sysUserService.findByUsername(operatorName);
        if (user == null) {
            return null;
        }
        return firstNonBlank(user.getDepartment(), user.getDepartmentCode());
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
        String operatorName = resolveOperatorName();
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

    private void applyReviewOutcome(AppealReview existingReview, AppealReview appealReview) {
        if (appealReview == null || !isFinalReview(appealReview.getReviewLevel())) {
            return;
        }
        if (existingReview != null && !isReviewDecisionChanged(existingReview, appealReview)) {
            return;
        }
        AppealRecord appealRecord = appealRecordService.getAppealById(appealReview.getAppealId());
        if (appealRecord == null) {
            throw new IllegalStateException("Appeal does not exist");
        }
        AppealProcessState processState = AppealProcessState.fromCode(appealRecord.getProcessStatus());
        if (processState == null) {
            processState = AppealProcessState.UNPROCESSED;
        }

        String reviewResult = trimToEmpty(appealReview.getReviewResult());
        if ("Approved".equalsIgnoreCase(reviewResult)) {
            if (processState == AppealProcessState.UNDER_REVIEW) {
                appealRecord = appealRecordService.updateProcessStatus(
                        appealRecord.getAppealId(),
                        AppealProcessState.APPROVED,
                        resolveProcessResult(appealReview, "Approved"));
            }
            applyApprovedReviewAction(appealReview, appealRecord);
            return;
        }

        if (("Rejected".equalsIgnoreCase(reviewResult) || "Need_Resubmit".equalsIgnoreCase(reviewResult))
                && processState == AppealProcessState.UNDER_REVIEW) {
            appealRecordService.updateProcessStatus(
                    appealRecord.getAppealId(),
                    AppealProcessState.REJECTED,
                    resolveProcessResult(appealReview, reviewResult));
        }
    }

    private void ensureReviewCanBeDeleted(AppealReview review) {
        if (review == null || review.getAppealId() == null) {
            return;
        }
        AppealRecord appealRecord = appealRecordService.getAppealById(review.getAppealId());
        if (appealRecord == null) {
            return;
        }
        AppealProcessState processState = AppealProcessState.fromCode(appealRecord.getProcessStatus());
        if (isAppealFinalized(processState)) {
            throw new IllegalStateException("Cannot delete review records after the appeal has been finalized");
        }
    }

    private void applyApprovedReviewAction(AppealReview appealReview, AppealRecord appealRecord) {
        String suggestedAction = trimToEmpty(appealReview.getSuggestedAction());
        if (suggestedAction.isEmpty() || appealRecord == null || appealRecord.getOffenseId() == null) {
            return;
        }
        Long offenseId = appealRecord.getOffenseId();
        if ("Cancel_Offense".equalsIgnoreCase(suggestedAction)) {
            waiveFinesByOffense(offenseId);
            restoreDeductionsByOffense(offenseId, "Appeal approved via final review");
            offenseRecordService.updatePenaltySummary(offenseId, BigDecimal.ZERO, 0, 0);
            return;
        }
        if ("Reduce_Fine".equalsIgnoreCase(suggestedAction)) {
            reduceFineByOffense(offenseId, appealReview.getSuggestedFineAmount());
            return;
        }
        if ("Reduce_Points".equalsIgnoreCase(suggestedAction)) {
            reduceDeductionByOffense(offenseId, appealReview.getSuggestedPoints());
        }
    }

    private void validateSuggestedActionBounds(AppealReview appealReview, AppealRecord appealRecord) {
        if (appealReview == null || appealRecord == null || appealRecord.getOffenseId() == null) {
            return;
        }
        String suggestedAction = trimToEmpty(appealReview.getSuggestedAction());
        if ("Reduce_Fine".equalsIgnoreCase(suggestedAction)) {
            validateReducedFineAmount(appealRecord.getOffenseId(), appealReview.getSuggestedFineAmount());
            return;
        }
        if ("Reduce_Points".equalsIgnoreCase(suggestedAction)) {
            validateReducedPoints(appealRecord.getOffenseId(), appealReview.getSuggestedPoints());
        }
    }

    private void validateReducedFineAmount(Long offenseId, BigDecimal suggestedFineAmount) {
        if (suggestedFineAmount == null || suggestedFineAmount.signum() < 0) {
            throw new IllegalArgumentException("Suggested fine amount must be provided for Reduce_Fine");
        }
        List<FineRecord> fineRecords = fineRecordService.findByOffenseId(offenseId, 1, 200);
        if (fineRecords.size() != 1 || fineRecords.get(0) == null) {
            throw new IllegalStateException("Reduce_Fine requires exactly one fine record for the offense");
        }
        BigDecimal currentFineAmount = normalizeAmount(fineRecords.get(0).getFineAmount());
        if (suggestedFineAmount.compareTo(currentFineAmount) > 0) {
            throw new IllegalArgumentException("Suggested fine amount cannot exceed the current fine amount");
        }
    }

    private void validateReducedPoints(Long offenseId, Integer suggestedPoints) {
        if (suggestedPoints == null || suggestedPoints < 0) {
            throw new IllegalArgumentException("Suggested points must be provided for Reduce_Points");
        }
        List<DeductionRecord> deductionRecords = deductionRecordService.findByOffenseId(offenseId, 1, 200);
        if (deductionRecords.size() != 1 || deductionRecords.get(0) == null) {
            throw new IllegalStateException("Reduce_Points requires exactly one deduction record for the offense");
        }
        Integer currentPoints = deductionRecords.get(0).getDeductedPoints();
        int normalizedCurrentPoints = currentPoints == null ? 0 : currentPoints;
        if (suggestedPoints > normalizedCurrentPoints) {
            throw new IllegalArgumentException("Suggested points cannot exceed the current deducted points");
        }
    }

    private void waiveFinesByOffense(Long offenseId) {
        List<FineRecord> fineRecords = fineRecordService.findByOffenseId(offenseId, 1, 200);
        for (FineRecord fineRecord : fineRecords) {
            if (fineRecord == null) {
                continue;
            }
            paymentRecordService.waiveAndRefundPaymentsByFineId(
                    fineRecord.getFineId(),
                    "Appeal approved with offense cancellation");
            FineRecord refreshed = fineRecordService.findById(fineRecord.getFineId());
            if (refreshed != null && PaymentState.WAIVED.getCode().equalsIgnoreCase(trimToEmpty(refreshed.getPaymentStatus()))) {
                continue;
            }
            fineRecord.setPaymentStatus(PaymentState.WAIVED.getCode());
            fineRecord.setUnpaidAmount(BigDecimal.ZERO);
            fineRecord.setPaidAmount(BigDecimal.ZERO);
            fineRecord.setUpdatedAt(LocalDateTime.now());
            fineRecordService.updateFineRecordSystemManaged(fineRecord);
        }
    }

    private void restoreDeductionsByOffense(Long offenseId, String reason) {
        List<DeductionRecord> deductionRecords = deductionRecordService.findByOffenseId(offenseId, 1, 200);
        for (DeductionRecord deductionRecord : deductionRecords) {
            if (deductionRecord == null) {
                continue;
            }
            deductionRecord.setStatus("Restored");
            deductionRecord.setRestoreTime(LocalDateTime.now());
            deductionRecord.setRestoreReason(truncate(reason));
            deductionRecord.setUpdatedAt(LocalDateTime.now());
            deductionRecordService.updateDeductionRecordSystemManaged(deductionRecord);
        }
    }

    private void reduceFineByOffense(Long offenseId, BigDecimal suggestedFineAmount) {
        if (suggestedFineAmount == null || suggestedFineAmount.signum() < 0) {
            throw new IllegalArgumentException("Suggested fine amount must be provided for Reduce_Fine");
        }
        List<FineRecord> fineRecords = fineRecordService.findByOffenseId(offenseId, 1, 200);
        if (fineRecords.size() != 1) {
            throw new IllegalStateException("Reduce_Fine requires exactly one fine record for the offense");
        }
        FineRecord fineRecord = fineRecords.get(0);
        BigDecimal lateFee = normalizeAmount(fineRecord.getLateFee());
        BigDecimal paidAmount = normalizeAmount(fineRecord.getPaidAmount());
        BigDecimal totalAmount = suggestedFineAmount.add(lateFee);
        BigDecimal refundAmount = paidAmount.subtract(totalAmount);
        if (refundAmount.signum() > 0) {
            paymentRecordService.refundPaymentsByFineId(
                    fineRecord.getFineId(),
                    refundAmount,
                    "Appeal approved with fine reduction");
            fineRecord = fineRecordService.findById(fineRecord.getFineId());
            paidAmount = normalizeAmount(fineRecord == null ? null : fineRecord.getPaidAmount());
        }
        BigDecimal unpaidAmount = totalAmount.subtract(paidAmount);
        if (unpaidAmount.signum() < 0) {
            unpaidAmount = BigDecimal.ZERO;
        }
        if (fineRecord == null) {
            throw new IllegalStateException("Fine record not found after refund processing");
        }
        fineRecord.setFineAmount(suggestedFineAmount);
        fineRecord.setTotalAmount(totalAmount);
        fineRecord.setUnpaidAmount(unpaidAmount);
        fineRecord.setPaymentStatus(resolveFinePaymentStatus(fineRecord.getPaymentDeadline(), totalAmount, paidAmount));
        fineRecord.setUpdatedAt(LocalDateTime.now());
        fineRecordService.updateFineRecordSystemManaged(fineRecord);
        offenseRecordService.updatePenaltySummary(offenseId, suggestedFineAmount, null, null);
    }

    private void reduceDeductionByOffense(Long offenseId, Integer suggestedPoints) {
        if (suggestedPoints == null || suggestedPoints < 0) {
            throw new IllegalArgumentException("Suggested points must be provided for Reduce_Points");
        }
        List<DeductionRecord> deductionRecords = deductionRecordService.findByOffenseId(offenseId, 1, 200);
        if (deductionRecords.size() != 1) {
            throw new IllegalStateException("Reduce_Points requires exactly one deduction record for the offense");
        }
        DeductionRecord deductionRecord = deductionRecords.get(0);
        if (suggestedPoints == 0) {
            deductionRecord.setStatus("Restored");
            deductionRecord.setRestoreTime(LocalDateTime.now());
            deductionRecord.setRestoreReason("Appeal approved with zero points");
        } else {
            deductionRecord.setDeductedPoints(suggestedPoints);
            deductionRecord.setStatus("Effective");
            deductionRecord.setRestoreTime(null);
            deductionRecord.setRestoreReason(null);
        }
        deductionRecord.setUpdatedAt(LocalDateTime.now());
        deductionRecordService.updateDeductionRecordSystemManaged(deductionRecord);
        offenseRecordService.updatePenaltySummary(offenseId, null, suggestedPoints, null);
    }

    private boolean isFinalReview(String reviewLevel) {
        return "Final".equalsIgnoreCase(trimToEmpty(reviewLevel));
    }

    private boolean isAppealFinalized(AppealProcessState state) {
        return state == AppealProcessState.APPROVED || state == AppealProcessState.REJECTED;
    }

    private String firstNonBlank(String... values) {
        if (values == null) {
            return null;
        }
        for (String value : values) {
            if (!isBlank(value)) {
                return value.trim();
            }
        }
        return null;
    }

    private boolean isReviewContentChanged(AppealReview existing, AppealReview incoming) {
        return !trimToEmpty(existing.getReviewLevel()).equalsIgnoreCase(trimToEmpty(incoming.getReviewLevel()))
                || !trimToEmpty(existing.getReviewResult()).equalsIgnoreCase(trimToEmpty(incoming.getReviewResult()))
                || !trimToEmpty(existing.getSuggestedAction()).equalsIgnoreCase(trimToEmpty(incoming.getSuggestedAction()))
                || !Objects.equals(existing.getSuggestedFineAmount(), incoming.getSuggestedFineAmount())
                || !Objects.equals(existing.getSuggestedPoints(), incoming.getSuggestedPoints())
                || !trimToEmpty(existing.getReviewer()).equalsIgnoreCase(trimToEmpty(incoming.getReviewer()))
                || !trimToEmpty(existing.getReviewerDept()).equalsIgnoreCase(trimToEmpty(incoming.getReviewerDept()))
                || !Objects.equals(existing.getReviewTime(), incoming.getReviewTime())
                || !trimToEmpty(existing.getRemarks()).equalsIgnoreCase(trimToEmpty(incoming.getRemarks()));
    }

    private boolean isReviewDecisionChanged(AppealReview existing, AppealReview incoming) {
        return !trimToEmpty(existing.getReviewLevel()).equalsIgnoreCase(trimToEmpty(incoming.getReviewLevel()))
                || !trimToEmpty(existing.getReviewResult()).equalsIgnoreCase(trimToEmpty(incoming.getReviewResult()))
                || !trimToEmpty(existing.getSuggestedAction()).equalsIgnoreCase(trimToEmpty(incoming.getSuggestedAction()))
                || !Objects.equals(existing.getSuggestedFineAmount(), incoming.getSuggestedFineAmount())
                || !Objects.equals(existing.getSuggestedPoints(), incoming.getSuggestedPoints());
    }

    private void ensureSingleReviewPerLevel(AppealReview appealReview, AppealReview existingReview) {
        QueryWrapper<AppealReview> wrapper = new QueryWrapper<>();
        wrapper.eq("appeal_id", appealReview.getAppealId())
                .eq("review_level", trimToEmpty(appealReview.getReviewLevel()));
        if (existingReview != null && existingReview.getReviewId() != null) {
            wrapper.ne("review_id", existingReview.getReviewId());
        }
        if (appealReviewMapper.selectCount(wrapper) > 0) {
            throw new IllegalStateException("Only one review per level is allowed for the same appeal");
        }
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private BigDecimal normalizeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }

    private String resolveFinePaymentStatus(LocalDate paymentDeadline, BigDecimal totalAmount, BigDecimal paidAmount) {
        if (totalAmount.signum() <= 0 || paidAmount.compareTo(totalAmount) >= 0) {
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

    private String resolveProcessResult(AppealReview appealReview, String fallback) {
        if (appealReview == null) {
            return fallback;
        }
        String normalizedOpinion = trimToEmpty(appealReview.getReviewOpinion());
        if (!normalizedOpinion.isEmpty()) {
            return truncate(normalizedOpinion);
        }
        String normalizedResult = trimToEmpty(appealReview.getReviewResult());
        if (!normalizedResult.isEmpty()) {
            return truncate(normalizedResult);
        }
        return isBlank(fallback) ? null : truncate(fallback.trim());
    }
}
