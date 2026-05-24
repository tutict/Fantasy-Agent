package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.tutict.finalassignmentbackend.config.statemachine.states.DeductionState;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.DeductionRecordDocument;
import com.tutict.finalassignmentbackend.mapper.DeductionRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.DeductionRecordSearchRepository;
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

import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class DeductionRecordService {

    private static final Logger log = Logger.getLogger(DeductionRecordService.class.getName());
    private static final String CACHE_NAME = "deductionRecordCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final DeductionRecordMapper deductionRecordMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final DeductionRecordSearchRepository deductionRecordSearchRepository;
    private final OffenseRecordService offenseRecordService;
    private final DriverInformationService driverInformationService;
    private final SysUserService sysUserService;
    private final KafkaTemplate<String, DeductionRecord> kafkaTemplate;

    @Autowired
    public DeductionRecordService(DeductionRecordMapper deductionRecordMapper,
                                  SysRequestHistoryMapper sysRequestHistoryMapper,
                                  DeductionRecordSearchRepository deductionRecordSearchRepository,
                                  OffenseRecordService offenseRecordService,
                                  DriverInformationService driverInformationService,
                                  SysUserService sysUserService,
                                  KafkaTemplate<String, DeductionRecord> kafkaTemplate) {
        this.deductionRecordMapper = deductionRecordMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.deductionRecordSearchRepository = deductionRecordSearchRepository;
        this.offenseRecordService = offenseRecordService;
        this.driverInformationService = driverInformationService;
        this.sysUserService = sysUserService;
        this.kafkaTemplate = kafkaTemplate;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "DeductionRecordService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, DeductionRecord deductionRecord, String action) {
        Objects.requireNonNull(deductionRecord, "DeductionRecord must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate deduction record request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, deductionRecord, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("deduction_record_" + action, idempotencyKey, deductionRecord);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public DeductionRecord createDeductionRecord(DeductionRecord deductionRecord) {
        populateDriverIdentityFromOffense(deductionRecord);
        deductionRecord.setStatus(DeductionState.EFFECTIVE.getCode());
        deductionRecord.setRestoreTime(null);
        deductionRecord.setRestoreReason(null);
        validateDeductionRecord(deductionRecord);
        deductionRecordMapper.insert(deductionRecord);
        syncDriverPoints(deductionRecord.getDriverId());
        syncToIndexAfterCommit(deductionRecord);
        return deductionRecord;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public DeductionRecord updateDeductionRecord(DeductionRecord deductionRecord) {
        throw new IllegalStateException("Deduction records are enforcement evidence and cannot be manually updated");
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public DeductionRecord updateDeductionRecordSystemManaged(DeductionRecord deductionRecord) {
        populateDriverIdentityFromOffense(deductionRecord);
        validateDeductionRecord(deductionRecord);
        requirePositive(deductionRecord.getDeductionId(), "Deduction ID");
        return persistDeductionRecordUpdate(deductionRecord);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteDeductionRecord(Long deductionId) {
        throw new IllegalStateException("Deduction records are enforcement evidence and cannot be manually deleted");
    }

    private DeductionRecord persistDeductionRecordUpdate(DeductionRecord deductionRecord) {
        int rows = deductionRecordMapper.updateById(deductionRecord);
        if (rows == 0) {
            throw new IllegalStateException("No DeductionRecord updated for id=" + deductionRecord.getDeductionId());
        }
        syncDriverPoints(deductionRecord.getDriverId());
        syncToIndexAfterCommit(deductionRecord);
        return deductionRecord;
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#deductionId", unless = "#result == null")
    public DeductionRecord findById(Long deductionId) {
        requirePositive(deductionId, "Deduction ID");
        return deductionRecordSearchRepository.findById(deductionId)
                .map(DeductionRecordDocument::toEntity)
                .orElseGet(() -> {
                    DeductionRecord entity = deductionRecordMapper.selectById(deductionId);
                    if (entity != null) {
                        deductionRecordSearchRepository.save(DeductionRecordDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<DeductionRecord> findAll() {
        List<DeductionRecord> fromIndex = StreamSupport.stream(deductionRecordSearchRepository.findAll().spliterator(), false)
                .map(DeductionRecordDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'list:' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DeductionRecord> listDeductions(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("deduction_time")
                .orderByDesc("deduction_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'driver:' + #driverId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DeductionRecord> findByDriverId(Long driverId, int page, int size) {
        requirePositive(driverId, "Driver ID");
        validatePagination(page, size);
        List<DeductionRecord> index = mapHits(deductionRecordSearchRepository.findByDriverId(driverId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("driver_id", driverId)
                .orderByDesc("deduction_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<DeductionRecord> findByDriverIds(Iterable<Long> driverIds, int page, int size) {
        validatePagination(page, size);
        List<Long> normalizedIds = driverIds == null
                ? List.of()
                : StreamSupport.stream(driverIds.spliterator(), false)
                .filter(Objects::nonNull)
                .filter(id -> id > 0)
                .distinct()
                .collect(Collectors.toList());
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.in("driver_id", normalizedIds)
                .orderByDesc("updated_at")
                .orderByDesc("deduction_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<Long> findIdsByDriverIds(Iterable<Long> driverIds) {
        List<Long> normalizedIds = driverIds == null
                ? List.of()
                : StreamSupport.stream(driverIds.spliterator(), false)
                .filter(Objects::nonNull)
                .filter(id -> id > 0)
                .distinct()
                .collect(Collectors.toList());
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.select("deduction_id")
                .in("driver_id", normalizedIds)
                .orderByDesc("updated_at")
                .orderByDesc("deduction_time");
        return deductionRecordMapper.selectObjs(wrapper).stream()
                .filter(Objects::nonNull)
                .map(this::toLong)
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'offense:' + #offenseId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DeductionRecord> findByOffenseId(Long offenseId, int page, int size) {
        requirePositive(offenseId, "Offense ID");
        validatePagination(page, size);
        List<DeductionRecord> index = mapHits(deductionRecordSearchRepository.findByOffenseId(offenseId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_id", offenseId)
                .orderByDesc("deduction_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'handlerPrefix:' + #handler + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DeductionRecord> searchByHandlerPrefix(String handler, int page, int size) {
        if (isBlank(handler)) {
            return List.of();
        }
        validatePagination(page, size);
        List<DeductionRecord> index = mapHits(deductionRecordSearchRepository.searchByHandlerPrefix(handler, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.likeRight("handler", handler);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'handlerFuzzy:' + #handler + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DeductionRecord> searchByHandlerFuzzy(String handler, int page, int size) {
        if (isBlank(handler)) {
            return List.of();
        }
        validatePagination(page, size);
        List<DeductionRecord> index = mapHits(deductionRecordSearchRepository.searchByHandlerFuzzy(handler, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.like("handler", handler);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'status:' + #status + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DeductionRecord> searchByStatus(String status, int page, int size) {
        if (isBlank(status)) {
            return List.of();
        }
        validatePagination(page, size);
        List<DeductionRecord> index = mapHits(deductionRecordSearchRepository.searchByStatus(status, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("status", status)
                .orderByDesc("deduction_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'timeRange:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DeductionRecord> searchByDeductionTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<DeductionRecord> index = mapHits(deductionRecordSearchRepository.searchByDeductionTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.between("deduction_time", start, end)
                .orderByDesc("deduction_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long deductionId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(deductionId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, DeductionRecord deductionRecord, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod(resolveRequestMethod("POST"));
        history.setRequestUrl(resolveRequestUrl("/api/deductions"));
        history.setRequestParams(buildRequestParams(deductionRecord));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setUserId(resolveCurrentUserId());
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(DeductionRecord deductionRecord) {
        if (deductionRecord == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "offenseId", deductionRecord.getOffenseId());
        appendParam(builder, "driverId", deductionRecord.getDriverId());
        appendParam(builder, "deductedPoints", deductionRecord.getDeductedPoints());
        appendParam(builder, "deductionTime", deductionRecord.getDeductionTime());
        appendParam(builder, "handler", deductionRecord.getHandler());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "DEDUCTION_" + normalized;
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

    private void syncToIndexAfterCommit(DeductionRecord deductionRecord) {
        if (deductionRecord == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            DeductionRecordDocument doc = DeductionRecordDocument.fromEntity(deductionRecord);
            if (doc != null) {
                deductionRecordSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<DeductionRecord> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<DeductionRecordDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(DeductionRecordDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                deductionRecordSearchRepository.saveAll(documents);
            }
        });
    }

    private void populateDriverIdentityFromOffense(DeductionRecord deductionRecord) {
        if (deductionRecord == null || deductionRecord.getOffenseId() == null || deductionRecord.getDriverId() != null) {
            return;
        }
        OffenseRecord offenseRecord = offenseRecordService.findById(deductionRecord.getOffenseId());
        if (offenseRecord != null && offenseRecord.getDriverId() != null) {
            deductionRecord.setDriverId(offenseRecord.getDriverId());
        }
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

    private void sendKafkaMessage(String topic, String idempotencyKey, DeductionRecord deductionRecord) {
        try {
            kafkaTemplate.send(topic, idempotencyKey, deductionRecord);
        } catch (Exception ex) {
            log.log(Level.SEVERE,
                    String.format("Failed to send DeductionRecord Kafka message (topic=%s, key=%s)", topic, idempotencyKey),
                    ex);
            throw new RuntimeException("Failed to send deduction record event", ex);
        }
    }

    private List<DeductionRecord> mapHits(org.springframework.data.elasticsearch.core.SearchHits<DeductionRecordDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(DeductionRecordDocument::toEntity)
                .collect(Collectors.toList());
    }

    private List<DeductionRecord> fetchFromDatabase(QueryWrapper<DeductionRecord> wrapper, int page, int size) {
        Page<DeductionRecord> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        deductionRecordMapper.selectPage(mpPage, wrapper);
        List<DeductionRecord> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<DeductionRecord> loadAllFromDatabase() {
        List<DeductionRecord> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
            wrapper.orderByAsc("deduction_id");
            Page<DeductionRecord> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            deductionRecordMapper.selectPage(mpPage, wrapper);
            List<DeductionRecord> records = mpPage.getRecords();
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

    private void validateDeductionRecord(DeductionRecord deductionRecord) {
        Objects.requireNonNull(deductionRecord, "DeductionRecord must not be null");
        requirePositive(deductionRecord.getOffenseId(), "Offense ID");
        requirePositive(deductionRecord.getDriverId(), "Driver ID");
        OffenseRecord offenseRecord = offenseRecordService.findById(deductionRecord.getOffenseId());
        if (offenseRecord == null) {
            throw new IllegalArgumentException("Offense record does not exist");
        }
        DriverInformation driverInformation = driverInformationService.getDriverById(deductionRecord.getDriverId());
        if (driverInformation == null) {
            throw new IllegalArgumentException("Driver does not exist");
        }
        if (offenseRecord.getDriverId() != null
                && !Objects.equals(offenseRecord.getDriverId(), deductionRecord.getDriverId())) {
            throw new IllegalArgumentException("Deduction driver must match the offense driver");
        }
        if (deductionRecord.getDeductionId() != null) {
            DeductionRecord existing = deductionRecordMapper.selectById(deductionRecord.getDeductionId());
            if (existing != null) {
                if (existing.getOffenseId() != null
                        && !Objects.equals(existing.getOffenseId(), deductionRecord.getOffenseId())) {
                    throw new IllegalArgumentException("Offense ID cannot be changed for an existing deduction record");
                }
                if (existing.getDriverId() != null
                        && !Objects.equals(existing.getDriverId(), deductionRecord.getDriverId())) {
                    throw new IllegalArgumentException("Driver ID cannot be changed for an existing deduction record");
                }
            }
        }
        ensureSingleDeductionPerOffense(deductionRecord);
        if (deductionRecord.getDeductedPoints() == null || deductionRecord.getDeductedPoints() <= 0) {
            throw new IllegalArgumentException("Deducted points must be greater than zero");
        }
        if (deductionRecord.getDeductionTime() == null) {
            deductionRecord.setDeductionTime(LocalDateTime.now());
        }
        if (deductionRecord.getStatus() == null || deductionRecord.getStatus().isBlank()) {
            deductionRecord.setStatus(DeductionState.EFFECTIVE.getCode());
        }
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
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
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken
                || isBlank(authentication.getName())) {
            return null;
        }
        SysUser user = sysUserService.findByUsername(authentication.getName());
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

    private void ensureSingleDeductionPerOffense(DeductionRecord deductionRecord) {
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_id", deductionRecord.getOffenseId());
        if (deductionRecord.getDeductionId() != null) {
            wrapper.ne("deduction_id", deductionRecord.getDeductionId());
        }
        if (deductionRecordMapper.selectCount(wrapper) > 0) {
            throw new IllegalStateException("Only one deduction record is allowed for each offense");
        }
    }

    private void syncDriverPoints(Long driverId) {
        if (driverId == null) {
            return;
        }
        driverInformationService.syncPointsFromDeductionRecords(driverId);
    }
}
