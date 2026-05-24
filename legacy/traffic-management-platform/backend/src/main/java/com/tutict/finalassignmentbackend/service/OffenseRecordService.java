package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import com.tutict.finalassignmentbackend.config.statemachine.states.OffenseProcessState;
import com.tutict.finalassignmentbackend.config.tenant.TenantIsolationProperties;
import com.tutict.finalassignmentbackend.config.tenant.TenantAwareSupport;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.OffenseRecordDocument;
import com.tutict.finalassignmentbackend.mapper.AppealRecordMapper;
import com.tutict.finalassignmentbackend.mapper.DeductionRecordMapper;
import com.tutict.finalassignmentbackend.mapper.FineRecordMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.OffenseInformationSearchRepository;
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
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class OffenseRecordService {

    private static final Logger log = Logger.getLogger(OffenseRecordService.class.getName());
    private static final String CACHE_NAME = "offenseRecordCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final OffenseRecordMapper offenseRecordMapper;
    private final FineRecordMapper fineRecordMapper;
    private final AppealRecordMapper appealRecordMapper;
    private final DeductionRecordMapper deductionRecordMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final OffenseInformationSearchRepository offenseInformationSearchRepository;
    private final TenantAwareSupport tenantAwareSupport;
    private final SysUserService sysUserService;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public OffenseRecordService(OffenseRecordMapper offenseRecordMapper,
                                FineRecordMapper fineRecordMapper,
                                AppealRecordMapper appealRecordMapper,
                                DeductionRecordMapper deductionRecordMapper,
                                SysRequestHistoryMapper sysRequestHistoryMapper,
                                OffenseInformationSearchRepository offenseInformationSearchRepository,
                                TenantAwareSupport tenantAwareSupport,
                                SysUserService sysUserService,
                                KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper) {
        this.offenseRecordMapper = offenseRecordMapper;
        this.fineRecordMapper = fineRecordMapper;
        this.appealRecordMapper = appealRecordMapper;
        this.deductionRecordMapper = deductionRecordMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.offenseInformationSearchRepository = offenseInformationSearchRepository;
        this.tenantAwareSupport = tenantAwareSupport;
        this.sysUserService = sysUserService;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    public OffenseRecordService(OffenseRecordMapper offenseRecordMapper,
                                FineRecordMapper fineRecordMapper,
                                AppealRecordMapper appealRecordMapper,
                                DeductionRecordMapper deductionRecordMapper,
                                SysRequestHistoryMapper sysRequestHistoryMapper,
                                OffenseInformationSearchRepository offenseInformationSearchRepository,
                                SysUserService sysUserService,
                                KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper) {
        this(offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                sysRequestHistoryMapper,
                offenseInformationSearchRepository,
                defaultTenantAwareSupport(),
                sysUserService,
                kafkaTemplate,
                objectMapper);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "OffenseRecordService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, OffenseRecord offenseRecord, String action) {
        Objects.requireNonNull(offenseRecord, "OffenseRecord must not be null");
        if (sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey) != null) {
            throw new RuntimeException("Duplicate offense record request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, offenseRecord, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("offense_record_" + action, idempotencyKey, offenseRecord);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public OffenseRecord createOffenseRecord(OffenseRecord offenseRecord) {
        offenseRecord.setProcessStatus(OffenseProcessState.UNPROCESSED.getCode());
        validateOffenseRecord(offenseRecord);
        // 同步写库，成功后再异步刷新 ES
        offenseRecordMapper.insert(offenseRecord);
        syncToIndexAfterCommit(offenseRecord);
        return offenseRecord;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public OffenseRecord updateOffenseRecord(OffenseRecord offenseRecord) {
        requirePositive(offenseRecord.getOffenseId(), "Offense ID");
        OffenseRecord existing = findOffenseByIdFromDatabase(offenseRecord.getOffenseId());
        if (existing == null) {
            throw new IllegalStateException("No OffenseRecord updated for id=" + offenseRecord.getOffenseId());
        }
        offenseRecord.setProcessStatus(existing.getProcessStatus());
        preserveEvidenceFieldsWhenDownstreamRecordsExist(offenseRecord, existing);
        validateOffenseRecord(offenseRecord);
        int rows = updateOffenseByIdScoped(offenseRecord);
        if (rows == 0) {
            throw new IllegalStateException("No OffenseRecord updated for id=" + offenseRecord.getOffenseId());
        }
        syncToIndexAfterCommit(offenseRecord);
        return offenseRecord;
    }

    public OffenseRecord updateProcessStatus(Long offenseId, OffenseProcessState newState) {
        requirePositive(offenseId, "Offense ID");
        OffenseRecord existing = findOffenseByIdFromDatabase(offenseId);
        if (existing == null) {
            throw new IllegalStateException("OffenseRecord not found for id=" + offenseId);
        }
        // 仅允许状态机计算出的状态覆盖数据库的 process_status 字段
        existing.setProcessStatus(newState != null ? newState.getCode() : existing.getProcessStatus());
        existing.setUpdatedAt(LocalDateTime.now());
        updateOffenseByIdScoped(existing);
        syncToIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public OffenseRecord updatePenaltySummary(Long offenseId,
                                              java.math.BigDecimal fineAmount,
                                              Integer deductedPoints,
                                              Integer detentionDays) {
        requirePositive(offenseId, "Offense ID");
        OffenseRecord existing = findOffenseByIdFromDatabase(offenseId);
        if (existing == null) {
            throw new IllegalStateException("OffenseRecord not found for id=" + offenseId);
        }
        if (fineAmount != null) {
            requireNonNegative(fineAmount, "Fine amount");
            existing.setFineAmount(fineAmount);
        }
        if (deductedPoints != null) {
            requireNonNegative(deductedPoints, "Deducted points");
            existing.setDeductedPoints(deductedPoints);
        }
        if (detentionDays != null) {
            requireNonNegative(detentionDays, "Detention days");
            existing.setDetentionDays(detentionDays);
        }
        existing.setUpdatedAt(LocalDateTime.now());
        int rows = updateOffenseByIdScoped(existing);
        if (rows == 0) {
            throw new IllegalStateException("No OffenseRecord updated for id=" + offenseId);
        }
        syncToIndexAfterCommit(existing);
        return existing;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteOffenseRecord(Long offenseId) {
        requirePositive(offenseId, "Offense ID");
        ensureNoDependentFineRecords(offenseId);
        ensureNoDependentDeductions(offenseId);
        ensureNoDependentAppeals(offenseId);
        int rows = deleteOffenseByIdScoped(offenseId);
        if (rows == 0) {
            throw new IllegalStateException("No OffenseRecord deleted for id=" + offenseId);
        }
        if (!databaseOnlyForTenantIsolation()) {
            runAfterCommitOrNow(() -> offenseInformationSearchRepository.deleteById(offenseId));
        }
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('offense', #offenseId)", unless = "#result == null")
    public OffenseRecord findById(Long offenseId) {
        requirePositive(offenseId, "Offense ID");
        if (databaseOnlyForTenantIsolation()) {
            return findOffenseByIdFromDatabase(offenseId);
        }
        return offenseInformationSearchRepository.findById(offenseId)
                .map(OffenseRecordDocument::toEntity)
                .orElseGet(() -> {
                    OffenseRecord entity = findOffenseByIdFromDatabase(offenseId);
                    if (entity != null) {
                        offenseInformationSearchRepository.save(OffenseRecordDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public boolean existsById(Long offenseId) {
        requirePositive(offenseId, "Offense ID");
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", offenseId).last("limit 1");
        Long count = offenseRecordMapper.selectCount(wrapper);
        return count != null && count > 0;
    }

    @Transactional(readOnly = true)
    public List<OffenseRecord> findAll() {
        if (databaseOnlyForTenantIsolation()) {
            return loadAllFromDatabase();
        }
        List<OffenseRecord> fromIndex = StreamSupport.stream(offenseInformationSearchRepository.findAll().spliterator(), false)
                .map(OffenseRecordDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('page', #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> listOffenses(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("updated_at")
                .orderByDesc("offense_time")
                .orderByDesc("offense_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('driver', #driverId, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> findByDriverId(Long driverId, int page, int size) {
        requirePositive(driverId, "Driver ID");
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.findByDriverId(driverId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("driver_id", driverId)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('vehicle', #vehicleId, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> findByVehicleId(Long vehicleId, int page, int size) {
        requirePositive(vehicleId, "Vehicle ID");
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.findByVehicleId(vehicleId, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("vehicle_id", vehicleId)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('code', #offenseCode, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByOffenseCode(String offenseCode, int page, int size) {
        if (isBlank(offenseCode)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByOffenseCode(offenseCode, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.like("offense_code", offenseCode)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('type', #offenseType, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByOffenseType(String offenseType, int page, int size) {
        if (isBlank(offenseType)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByOffenseType(offenseType, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.like("offense_type", offenseType)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('status', #processStatus, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByProcessStatus(String processStatus, int page, int size) {
        if (isBlank(processStatus)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByProcessStatus(processStatus, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("process_status", processStatus)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('timeRange', #startTime, #endTime, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByOffenseTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByOffenseTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.between("offense_time", start, end)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('number', #offenseNumber, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByOffenseNumber(String offenseNumber, int page, int size) {
        if (isBlank(offenseNumber)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByOffenseNumber(offenseNumber, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_number", offenseNumber)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<OffenseRecord> findByDriverIds(Iterable<Long> driverIds, int page, int size) {
        List<Long> normalizedIds = normalizePositiveIds(driverIds);
        validatePagination(page, size);
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.in("driver_id", normalizedIds)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    public List<Long> findIdsByDriverIds(Iterable<Long> driverIds) {
        List<Long> normalizedIds = normalizePositiveIds(driverIds);
        if (normalizedIds.isEmpty()) {
            return List.of();
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).select("offense_id")
                .in("driver_id", normalizedIds)
                .orderByDesc("offense_time");
        return offenseRecordMapper.selectObjs(wrapper).stream()
                .filter(Objects::nonNull)
                .map(this::toLong)
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('location', #offenseLocation, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByOffenseLocation(String offenseLocation, int page, int size) {
        if (isBlank(offenseLocation)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByOffenseLocation(offenseLocation, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.like("offense_location", offenseLocation)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('province', #offenseProvince, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByOffenseProvince(String offenseProvince, int page, int size) {
        if (isBlank(offenseProvince)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByOffenseProvince(offenseProvince, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_province", offenseProvince)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('city', #offenseCity, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByOffenseCity(String offenseCity, int page, int size) {
        if (isBlank(offenseCity)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByOffenseCity(offenseCity, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_city", offenseCity)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('notification', #notificationStatus, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByNotificationStatus(String notificationStatus, int page, int size) {
        if (isBlank(notificationStatus)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByNotificationStatus(notificationStatus, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.eq("notification_status", notificationStatus)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('agency', #enforcementAgency, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByEnforcementAgency(String enforcementAgency, int page, int size) {
        if (isBlank(enforcementAgency)) {
            return List.of();
        }
        validatePagination(page, size);
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByEnforcementAgency(enforcementAgency, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.like("enforcement_agency", enforcementAgency)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('fineRange', #minAmount, #maxAmount, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<OffenseRecord> searchByFineAmountRange(double minAmount, double maxAmount, int page, int size) {
        validatePagination(page, size);
        if (minAmount > maxAmount) {
            return List.of();
        }
        List<OffenseRecord> index = mapHits(offenseInformationSearchRepository.searchByFineAmountRange(minAmount, maxAmount, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        wrapper.between("fine_amount", minAmount, maxAmount)
                .orderByDesc("offense_time");
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long offenseId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(offenseId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, OffenseRecord offenseRecord, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod(resolveRequestMethod("POST"));
        history.setRequestUrl(resolveRequestUrl("/api/offenses"));
        history.setRequestParams(buildRequestParams(offenseRecord));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setUserId(resolveCurrentUserId());
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(OffenseRecord offenseRecord) {
        if (offenseRecord == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "driverId", offenseRecord.getDriverId());
        appendParam(builder, "vehicleId", offenseRecord.getVehicleId());
        appendParam(builder, "offenseCode", offenseRecord.getOffenseCode());
        appendParam(builder, "offenseNumber", offenseRecord.getOffenseNumber());
        appendParam(builder, "offenseTime", offenseRecord.getOffenseTime());
        appendParam(builder, "offenseLocation", offenseRecord.getOffenseLocation());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "OFFENSE_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, OffenseRecord offenseRecord) {
        try {
            String payload = objectMapper.writeValueAsString(offenseRecord);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send OffenseRecord Kafka message", ex);
            throw new RuntimeException("Failed to send OffenseRecord event", ex);
        }
    }

    private void syncToIndexAfterCommit(OffenseRecord offenseRecord) {
        if (databaseOnlyForTenantIsolation() || offenseRecord == null) {
            return;
        }
        OffenseRecordDocument doc = OffenseRecordDocument.fromEntity(offenseRecord);
        if (doc == null) {
            return;
        }
        runAfterCommitOrNow(() -> offenseInformationSearchRepository.save(doc));
    }

    private void syncBatchToIndexAfterCommit(List<OffenseRecord> records) {
        if (databaseOnlyForTenantIsolation() || records == null || records.isEmpty()) {
            return;
        }
        List<OffenseRecordDocument> documents = records.stream()
                .filter(Objects::nonNull)
                .map(OffenseRecordDocument::fromEntity)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
        if (documents.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> offenseInformationSearchRepository.saveAll(documents));
    }

    /**
     * 将 ES 命中结果转换成实体列表，供缓存 miss 时快速返回
     */
    private List<OffenseRecord> mapHits(org.springframework.data.elasticsearch.core.SearchHits<OffenseRecordDocument> hits) {
        if (databaseOnlyForTenantIsolation()) {
            return List.of();
        }
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(OffenseRecordDocument::toEntity)
                .collect(Collectors.toList());
    }

    private List<OffenseRecord> fetchFromDatabase(QueryWrapper<OffenseRecord> wrapper, int page, int size) {
        tenantScope(wrapper);
        Page<OffenseRecord> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        offenseRecordMapper.selectPage(mpPage, wrapper);
        List<OffenseRecord> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<OffenseRecord> loadAllFromDatabase() {
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).orderByAsc("offense_id");

        List<OffenseRecord> allRecords = new ArrayList<>();
        long pageNumber = 1L;
        while (true) {
            Page<OffenseRecord> batchPage = new Page<>(pageNumber, FULL_LOAD_BATCH_SIZE);
            offenseRecordMapper.selectPage(batchPage, wrapper);
            List<OffenseRecord> records = batchPage.getRecords();
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

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validateOffenseRecord(OffenseRecord offenseRecord) {
        Objects.requireNonNull(offenseRecord, "OffenseRecord must not be null");
        requirePositive(offenseRecord.getDriverId(), "Driver ID");
        requirePositive(offenseRecord.getVehicleId(), "Vehicle ID");
        requireNonNegative(offenseRecord.getFineAmount(), "Fine amount");
        requireNonNegative(offenseRecord.getDeductedPoints(), "Deducted points");
        requireNonNegative(offenseRecord.getDetentionDays(), "Detention days");
        if (offenseRecord.getOffenseTime() == null) {
            offenseRecord.setOffenseTime(LocalDateTime.now());
        }
        if (offenseRecord.getProcessStatus() == null || offenseRecord.getProcessStatus().isBlank()) {
            offenseRecord.setProcessStatus("Unprocessed");
        }
    }

    private void preserveEvidenceFieldsWhenDownstreamRecordsExist(OffenseRecord offenseRecord, OffenseRecord existing) {
        if (offenseRecord == null || existing == null || !hasDependentBusinessRecords(existing.getOffenseId())) {
            return;
        }
        offenseRecord.setOffenseCode(existing.getOffenseCode());
        offenseRecord.setOffenseNumber(existing.getOffenseNumber());
        offenseRecord.setOffenseTime(existing.getOffenseTime());
        offenseRecord.setOffenseLocation(existing.getOffenseLocation());
        offenseRecord.setOffenseProvince(existing.getOffenseProvince());
        offenseRecord.setOffenseCity(existing.getOffenseCity());
        offenseRecord.setDriverId(existing.getDriverId());
        offenseRecord.setVehicleId(existing.getVehicleId());
        offenseRecord.setOffenseDescription(existing.getOffenseDescription());
        offenseRecord.setEvidenceType(existing.getEvidenceType());
        offenseRecord.setEvidenceUrls(existing.getEvidenceUrls());
        offenseRecord.setEnforcementAgency(existing.getEnforcementAgency());
        offenseRecord.setEnforcementOfficer(existing.getEnforcementOfficer());
        offenseRecord.setEnforcementDevice(existing.getEnforcementDevice());
        offenseRecord.setFineAmount(existing.getFineAmount());
        offenseRecord.setDeductedPoints(existing.getDeductedPoints());
        offenseRecord.setDetentionDays(existing.getDetentionDays());
    }

    private boolean hasDependentBusinessRecords(Long offenseId) {
        if (offenseId == null || offenseId <= 0) {
            return false;
        }
        return hasDependentFineRecords(offenseId)
                || hasDependentDeductions(offenseId)
                || hasDependentAppeals(offenseId);
    }

    private boolean hasDependentFineRecords(Long offenseId) {
        QueryWrapper<FineRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", offenseId);
        return fineRecordMapper.selectCount(wrapper) > 0;
    }

    private boolean hasDependentAppeals(Long offenseId) {
        QueryWrapper<AppealRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", offenseId);
        return appealRecordMapper.selectCount(wrapper) > 0;
    }

    private boolean hasDependentDeductions(Long offenseId) {
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", offenseId);
        return deductionRecordMapper.selectCount(wrapper) > 0;
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

    private Long toLong(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        try {
            return value == null ? null : Long.parseLong(value.toString());
        } catch (NumberFormatException ex) {
            log.log(Level.WARNING, "Failed to convert offense id value: " + value, ex);
            return null;
        }
    }

    private void requirePositive(Number number, String fieldName) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException(fieldName + " must be greater than zero");
        }
    }

    private void requireNonNegative(Number number, String fieldName) {
        if (number != null && number.doubleValue() < 0) {
            throw new IllegalArgumentException(fieldName + " must not be negative");
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

    private void ensureNoDependentFineRecords(Long offenseId) {
        if (hasDependentFineRecords(offenseId)) {
            throw new IllegalStateException("Cannot delete offense while fine records still exist");
        }
    }

    private void ensureNoDependentAppeals(Long offenseId) {
        if (hasDependentAppeals(offenseId)) {
            throw new IllegalStateException("Cannot delete offense while appeal records still exist");
        }
    }

    private void ensureNoDependentDeductions(Long offenseId) {
        if (hasDependentDeductions(offenseId)) {
            throw new IllegalStateException("Cannot delete offense while deduction records still exist");
        }
    }

    private void runAfterCommitOrNow(Runnable task) {
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

    private boolean databaseOnlyForTenantIsolation() {
        return tenantAwareSupport.isIsolationEnabled();
    }

    private <T> QueryWrapper<T> tenantScope(QueryWrapper<T> wrapper) {
        return tenantAwareSupport.applyTenantScope(wrapper);
    }

    private OffenseRecord findOffenseByIdFromDatabase(Long offenseId) {
        if (offenseId == null) {
            return null;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return offenseRecordMapper.selectById(offenseId);
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", offenseId).last("limit 1");
        return offenseRecordMapper.selectOne(wrapper);
    }

    private int updateOffenseByIdScoped(OffenseRecord offenseRecord) {
        if (offenseRecord == null || offenseRecord.getOffenseId() == null) {
            return 0;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return offenseRecordMapper.updateById(offenseRecord);
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", offenseRecord.getOffenseId());
        return offenseRecordMapper.update(offenseRecord, wrapper);
    }

    private int deleteOffenseByIdScoped(Long offenseId) {
        if (offenseId == null) {
            return 0;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return offenseRecordMapper.deleteById(offenseId);
        }
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("offense_id", offenseId);
        return offenseRecordMapper.delete(wrapper);
    }

    private static TenantAwareSupport defaultTenantAwareSupport() {
        ProductGovernanceProperties productGovernanceProperties = new ProductGovernanceProperties();
        productGovernanceProperties.setTenantIsolationEnabled(false);
        return new TenantAwareSupport(productGovernanceProperties, new TenantIsolationProperties());
    }
}
