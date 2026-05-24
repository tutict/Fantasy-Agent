package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import com.tutict.finalassignmentbackend.config.tenant.TenantIsolationProperties;
import com.tutict.finalassignmentbackend.config.tenant.TenantAwareSupport;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.DriverVehicle;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.DriverInformationDocument;
import com.tutict.finalassignmentbackend.mapper.DeductionRecordMapper;
import com.tutict.finalassignmentbackend.mapper.DriverInformationMapper;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.DriverInformationSearchRepository;
import jakarta.servlet.http.HttpServletRequest;
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
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class DriverInformationService {

    private static final Logger log = Logger.getLogger(DriverInformationService.class.getName());
    private static final String CACHE_NAME = "driverCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;
    private static final int MAX_SEARCH_CANDIDATES = 500;

    private final DriverInformationMapper driverInformationMapper;
    private final DriverVehicleMapper driverVehicleMapper;
    private final OffenseRecordMapper offenseRecordMapper;
    private final DeductionRecordMapper deductionRecordMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final DriverInformationSearchRepository driverInformationSearchRepository;
    private final TenantAwareSupport tenantAwareSupport;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public DriverInformationService(DriverInformationMapper driverInformationMapper,
                                    DriverVehicleMapper driverVehicleMapper,
                                    OffenseRecordMapper offenseRecordMapper,
                                    DeductionRecordMapper deductionRecordMapper,
                                    SysRequestHistoryMapper sysRequestHistoryMapper,
                                    TenantAwareSupport tenantAwareSupport,
                                    KafkaTemplate<String, String> kafkaTemplate,
                                    DriverInformationSearchRepository driverInformationSearchRepository,
                                    ObjectMapper objectMapper) {
        this.driverInformationMapper = driverInformationMapper;
        this.driverVehicleMapper = driverVehicleMapper;
        this.offenseRecordMapper = offenseRecordMapper;
        this.deductionRecordMapper = deductionRecordMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.tenantAwareSupport = tenantAwareSupport;
        this.kafkaTemplate = kafkaTemplate;
        this.driverInformationSearchRepository = driverInformationSearchRepository;
        this.objectMapper = objectMapper;
    }

    public DriverInformationService(DriverInformationMapper driverInformationMapper,
                                    DriverVehicleMapper driverVehicleMapper,
                                    OffenseRecordMapper offenseRecordMapper,
                                    DeductionRecordMapper deductionRecordMapper,
                                    SysRequestHistoryMapper sysRequestHistoryMapper,
                                    KafkaTemplate<String, String> kafkaTemplate,
                                    DriverInformationSearchRepository driverInformationSearchRepository,
                                    ObjectMapper objectMapper) {
        this(driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                sysRequestHistoryMapper,
                defaultTenantAwareSupport(),
                kafkaTemplate,
                driverInformationSearchRepository,
                objectMapper);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "DriverInformationService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, DriverInformation driverInformation, String action) {
        if (driverInformation == null) {
            throw new IllegalArgumentException("Driver information cannot be null");
        }
        SysRequestHistory existing = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            log.warning(() -> String.format("Duplicate driver request detected (key=%s)", idempotencyKey));
            throw new RuntimeException("Duplicate driver request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, driverInformation, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("driver_" + action, idempotencyKey, driverInformation);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public DriverInformation createDriver(DriverInformation driverInformation) {
        validateDriver(driverInformation);
        normalizeDerivedPointSummaryForCreate(driverInformation);
        log.log(Level.INFO, "Creating driver: {0}", driverInformation);
        driverInformationMapper.insert(driverInformation);
        syncToIndexAfterCommit(driverInformation);
        return driverInformation;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "DriverInformationService", action = "updateDriver")
    public DriverInformation updateDriver(DriverInformation driverInformation) {
        validateDriverId(driverInformation);
        DriverInformation existing = findDriverByIdFromDatabase(driverInformation.getDriverId());
        if (existing == null) {
            throw new IllegalStateException("Driver not found: " + driverInformation.getDriverId());
        }
        applyDerivedPointSummaryFromRecords(driverInformation);
        int rows = updateDriverByIdScoped(driverInformation);
        if (rows == 0) {
            throw new IllegalStateException("Driver not found: " + driverInformation.getDriverId());
        }

        syncToIndexAfterCommit(driverInformation);
        return driverInformation;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "DriverInformationService", action = "deleteDriver")
    public void deleteDriver(Long driverId) {
        validateDriverId(driverId);
        ensureNoDriverVehicleBindings(driverId);
        ensureNoOffenseRecords(driverId);
        ensureNoDeductionRecords(driverId);
        int rows = deleteDriverByIdScoped(driverId);
        if (rows == 0) {
            throw new IllegalStateException("Driver not found: " + driverId);
        }
        if (!databaseOnlyForTenantIsolation()) {
            runAfterCommitOrNow(() -> driverInformationSearchRepository.deleteById(driverId));
        }
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('driver', #driverId)", unless = "#result == null")
    @WsAction(service = "DriverInformationService", action = "getDriverById")
    public DriverInformation getDriverById(Long driverId) {
        validateDriverId(driverId);
        if (databaseOnlyForTenantIsolation()) {
            return findDriverByIdFromDatabase(driverId);
        }
        return driverInformationSearchRepository.findById(driverId)
                .map(DriverInformationDocument::toEntity)
                .orElseGet(() -> {
                    DriverInformation dbEntity = findDriverByIdFromDatabase(driverId);
                    if (dbEntity != null) {
                        driverInformationSearchRepository.save(DriverInformationDocument.fromEntity(dbEntity));
                    }
                    return dbEntity;
                });
    }

    @WsAction(service = "DriverInformationService", action = "getAllDrivers")
    public List<DriverInformation> getAllDrivers() {
        if (databaseOnlyForTenantIsolation()) {
            return loadAllFromDatabase();
        }
        List<DriverInformation> fromIndex = StreamSupport.stream(
                        driverInformationSearchRepository.findAll().spliterator(), false)
                .map(DriverInformationDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('list', #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<DriverInformation> listDrivers(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        wrapper.orderByAsc("name")
                .orderByAsc("driver_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('idCard', #query, #page, #size)")
    @WsAction(service = "DriverInformationService", action = "searchByIdCardNumber")
    public List<DriverInformation> searchByIdCardNumber(String query, int page, int size) {
        return searchByExactField(query, page, size,
                q -> driverInformationSearchRepository.searchByIdCardNumber(q, pageable(page, size)),
                "id_card_number");
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('license', #query, #page, #size)")
    @WsAction(service = "DriverInformationService", action = "searchByDriverLicenseNumber")
    public List<DriverInformation> searchByDriverLicenseNumber(String query, int page, int size) {
        return searchByExactField(query, page, size,
                q -> driverInformationSearchRepository.searchByDriverLicenseNumber(q, pageable(page, size)),
                "driver_license_number");
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('name', #query, #page, #size)")
    @WsAction(service = "DriverInformationService", action = "searchByName")
    public List<DriverInformation> searchByName(String query, int page, int size) {
        if (isBlank(query)) {
            return List.of();
        }
        if (databaseOnlyForTenantIsolation()) {
            QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
            wrapper.like("name", query.trim())
                    .orderByAsc("name")
                    .orderByAsc("driver_id");
            return fetchFromDatabase(wrapper, page, size);
        }
        return aggregatedSearch(query, page, size,
                q -> driverInformationSearchRepository.searchByNamePrefix(q, pageable(page, size)),
                q -> driverInformationSearchRepository.searchByNameFuzzy(q, pageable(page, size)),
                DriverInformationDocument::getName);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "@tenantCacheKeySupport.scope('search', #query, #page, #size)", unless = "#result == null || #result.isEmpty()")
    public List<DriverInformation> searchDrivers(String query, int page, int size) {
        validatePagination(page, size);
        if (isBlank(query)) {
            return listDrivers(page, size);
        }

        String normalizedQuery = query.trim();
        int fetchSize = resolveCandidateFetchSize(page, size);
        Map<Long, DriverInformation> merged = new LinkedHashMap<>();

        appendDriver(merged, findDriverByIdQuery(normalizedQuery));
        appendDrivers(merged, searchByIndexedCandidates(normalizedQuery, fetchSize));
        if (merged.isEmpty()) {
            appendDrivers(merged, searchByContactNumberCandidates(normalizedQuery, fetchSize));
            appendDrivers(merged, searchByExactFieldCandidates(normalizedQuery, fetchSize,
                    q -> driverInformationSearchRepository.searchByIdCardNumber(q, pageable(1, fetchSize)),
                    "id_card_number"));
            appendDrivers(merged, searchByExactFieldCandidates(normalizedQuery, fetchSize,
                    q -> driverInformationSearchRepository.searchByDriverLicenseNumber(q, pageable(1, fetchSize)),
                    "driver_license_number"));
            appendDrivers(merged, searchByNameCandidates(normalizedQuery, fetchSize));
        }

        return merged.values().stream()
                .sorted(driverSearchComparator())
                .skip((long) (page - 1) * size)
                .limit(size)
                .collect(Collectors.toList());
    }

    public DriverInformation findLinkedDriverForUser(SysUser user) {
        if (user == null) {
            return null;
        }
        DriverInformation byIdCard = findByExactIdCardNumber(user.getIdCardNumber());
        if (byIdCard != null) {
            return byIdCard;
        }
        if (user.getUserId() == null) {
            return null;
        }
        DriverInformation byUserId = getDriverById(user.getUserId());
        return isLegacyUserIdLink(user, byUserId) ? byUserId : null;
    }

    public DriverInformation findByExactDriverLicenseNumber(String driverLicenseNumber) {
        if (driverLicenseNumber == null || driverLicenseNumber.isBlank()) {
            return null;
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_license_number", driverLicenseNumber.trim())
                .orderByDesc("updated_at")
                .orderByDesc("created_at")
                .orderByDesc("driver_id")
                .last("limit 1");
        DriverInformation driver = driverInformationMapper.selectOne(wrapper);
        if (driver != null && !databaseOnlyForTenantIsolation()) {
            driverInformationSearchRepository.save(DriverInformationDocument.fromEntity(driver));
        }
        return driver;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public DriverInformation syncPointsFromDeductionRecords(Long driverId) {
        validateDriverId(driverId);
        DriverInformation driver = findDriverByIdFromDatabase(driverId);
        if (driver == null) {
            throw new IllegalStateException("Driver not found: " + driverId);
        }
        applyDerivedPointSummaryFromRecords(driver);
        driver.setUpdatedAt(LocalDateTime.now());
        updateDriverByIdScoped(driver);
        syncToIndexAfterCommit(driver);
        return driver;
    }

    private List<DriverInformation> aggregatedSearch(String query,
                                                     int page,
                                                     int size,
                                                     FunctionWithException<String, SearchHits<DriverInformationDocument>> prefixQuery,
                                                     FunctionWithException<String, SearchHits<DriverInformationDocument>> fuzzyQuery,
                                                     FunctionWithException<DriverInformationDocument, String> fieldSelector) {
        validatePagination(page, size);
        if (query == null || query.trim().isEmpty()) {
            return List.of();
        }
        if (databaseOnlyForTenantIsolation()) {
            QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
            wrapper.like("name", query.trim())
                    .orderByAsc("name")
                    .orderByAsc("driver_id");
            return fetchFromDatabase(wrapper, page, size);
        }

        Set<DriverInformation> buffer = new HashSet<>();
        searchAndCollect(query, prefixQuery, fieldSelector, buffer);
        if (buffer.size() < size) {
            searchAndCollect(query, fuzzyQuery, fieldSelector, buffer);
        }
        return buffer.stream()
                .skip((long) (page - 1) * size)
                .limit(size)
                .collect(Collectors.toList());
    }

    private List<DriverInformation> searchByExactField(String query,
                                                       int page,
                                                       int size,
                                                       FunctionWithException<String, SearchHits<DriverInformationDocument>> exactQuery,
                                                       String columnName) {
        validatePagination(page, size);
        if (isBlank(query)) {
            return List.of();
        }

        List<DriverInformation> fromIndex = collectExactHits(query, exactQuery);
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }

        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        wrapper.eq(columnName, query.trim())
                .orderByAsc("name")
                .orderByAsc("driver_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    private List<DriverInformation> collectExactHits(String query,
                                                     FunctionWithException<String, SearchHits<DriverInformationDocument>> executor) {
        if (databaseOnlyForTenantIsolation()) {
            return List.of();
        }
        try {
            SearchHits<DriverInformationDocument> hits = executor.apply(query);
            if (hits == null || !hits.hasSearchHits()) {
                return List.of();
            }
            return StreamSupport.stream(hits.spliterator(), false)
                    .map(SearchHit::getContent)
                    .filter(Objects::nonNull)
                    .map(DriverInformationDocument::toEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.log(Level.WARNING, "Error executing exact driver search", e);
            return List.of();
        }
    }

    private DriverInformation findDriverByIdQuery(String query) {
        if (isBlank(query) || !query.chars().allMatch(Character::isDigit)) {
            return null;
        }
        try {
            return getDriverById(Long.parseLong(query.trim()));
        } catch (Exception e) {
            return null;
        }
    }

    private List<DriverInformation> searchByContactNumberCandidates(String query, int fetchSize) {
        if (isBlank(query)) {
            return List.of();
        }
        if (!databaseOnlyForTenantIsolation()) {
            try {
                SearchHits<DriverInformationDocument> hits =
                        driverInformationSearchRepository.searchByContactNumber(query, pageable(1, fetchSize));
                if (hits != null && hits.hasSearchHits()) {
                    List<DriverInformation> fromIndex = StreamSupport.stream(hits.spliterator(), false)
                            .map(SearchHit::getContent)
                            .filter(Objects::nonNull)
                            .map(DriverInformationDocument::toEntity)
                            .filter(Objects::nonNull)
                            .collect(Collectors.toList());
                    if (!fromIndex.isEmpty()) {
                        return fromIndex;
                    }
                }
            } catch (Exception e) {
                log.log(Level.WARNING, "Error executing driver contact search", e);
            }
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        wrapper.like("contact_number", query.trim())
                .orderByAsc("name")
                .orderByAsc("driver_id");
        return fetchFromDatabase(wrapper, 1, fetchSize);
    }

    private List<DriverInformation> searchByNameCandidates(String query, int fetchSize) {
        if (isBlank(query)) {
            return List.of();
        }
        Set<DriverInformation> buffer = new HashSet<>();
        searchAndCollect(query,
                q -> driverInformationSearchRepository.searchByNamePrefix(q, pageable(1, fetchSize)),
                DriverInformationDocument::getName,
                buffer);
        if (buffer.size() < fetchSize) {
            searchAndCollect(query,
                    q -> driverInformationSearchRepository.searchByNameFuzzy(q, pageable(1, fetchSize)),
                    DriverInformationDocument::getName,
                    buffer);
        }
        if (!buffer.isEmpty()) {
            return new ArrayList<>(buffer);
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        wrapper.like("name", query.trim())
                .orderByAsc("name")
                .orderByAsc("driver_id");
        return fetchFromDatabase(wrapper, 1, fetchSize);
    }

    private List<DriverInformation> searchByIndexedCandidates(String query, int fetchSize) {
        if (isBlank(query)) {
            return List.of();
        }
        if (databaseOnlyForTenantIsolation()) {
            return List.of();
        }
        try {
            SearchHits<DriverInformationDocument> hits =
                    driverInformationSearchRepository.searchBroadly(query, pageable(1, fetchSize));
            if (hits == null || !hits.hasSearchHits()) {
                return List.of();
            }
            return hits.getSearchHits().stream()
                    .map(SearchHit::getContent)
                    .filter(Objects::nonNull)
                    .map(DriverInformationDocument::toEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.log(Level.WARNING, "Error executing aggregated driver search", e);
            return List.of();
        }
    }

    private List<DriverInformation> searchByExactFieldCandidates(String query,
                                                                 int fetchSize,
                                                                 FunctionWithException<String, SearchHits<DriverInformationDocument>> exactQuery,
                                                                 String columnName) {
        if (isBlank(query)) {
            return List.of();
        }
        List<DriverInformation> fromIndex = collectExactHits(query, exactQuery);
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        wrapper.eq(columnName, query.trim())
                .orderByAsc("name")
                .orderByAsc("driver_id");
        return fetchFromDatabase(wrapper, 1, fetchSize);
    }

    private void appendDriver(Map<Long, DriverInformation> sink, DriverInformation driver) {
        if (driver == null || driver.getDriverId() == null) {
            return;
        }
        sink.putIfAbsent(driver.getDriverId(), driver);
    }

    private void appendDrivers(Map<Long, DriverInformation> sink, List<DriverInformation> drivers) {
        if (drivers == null) {
            return;
        }
        for (DriverInformation driver : drivers) {
            appendDriver(sink, driver);
        }
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long driverId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(driverId);
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

    private SysRequestHistory buildHistory(String idempotencyKey,
                                           DriverInformation driverInformation,
                                           String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod(resolveRequestMethod("POST"));
        history.setRequestUrl(resolveRequestUrl("/api/drivers"));
        history.setRequestParams(buildRequestParams(driverInformation));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(DriverInformation driverInformation) {
        if (driverInformation == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "name", driverInformation.getName());
        appendParam(builder, "idCardNumber", driverInformation.getIdCardNumber());
        appendParam(builder, "driverLicenseNumber", driverInformation.getDriverLicenseNumber());
        appendParam(builder, "contactNumber", driverInformation.getContactNumber());
        appendParam(builder, "email", driverInformation.getEmail());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "DRIVER_" + normalized;
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

    private void searchAndCollect(String query,
                                  FunctionWithException<String, SearchHits<DriverInformationDocument>> executor,
                                  FunctionWithException<DriverInformationDocument, String> fieldSelector,
                                  Set<DriverInformation> sink) {
        if (databaseOnlyForTenantIsolation()) {
            return;
        }
        try {
            SearchHits<DriverInformationDocument> hits = executor.apply(query);
            if (hits == null || !hits.hasSearchHits()) {
                return;
            }
            for (SearchHit<DriverInformationDocument> hit : hits) {
                DriverInformationDocument doc = hit.getContent();
                if (fieldSelector.apply(doc) != null) {
                    sink.add(doc.toEntity());
                }
            }
        } catch (Exception e) {
            log.log(Level.WARNING, "Error executing driver search", e);
        }
    }

    private Pageable pageable(int page, int size) {
        return PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private List<DriverInformation> fetchFromDatabase(QueryWrapper<DriverInformation> wrapper, int page, int size) {
        tenantScope(wrapper);
        Page<DriverInformation> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        driverInformationMapper.selectPage(mpPage, wrapper);
        List<DriverInformation> records = mpPage.getRecords();
        if (records == null || records.isEmpty()) {
            return List.of();
        }
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private int resolveCandidateFetchSize(int page, int size) {
        long requested = (long) Math.max(page, 1) * Math.max(size, 1);
        long normalized = Math.max(requested, size);
        return (int) Math.min(normalized, MAX_SEARCH_CANDIDATES);
    }

    private List<DriverInformation> loadAllFromDatabase() {
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).orderByAsc("driver_id");

        List<DriverInformation> allRecords = new ArrayList<>();
        long pageNumber = 1L;
        while (true) {
            Page<DriverInformation> batchPage = new Page<>(pageNumber, FULL_LOAD_BATCH_SIZE);
            driverInformationMapper.selectPage(batchPage, wrapper);
            List<DriverInformation> records = batchPage.getRecords();
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

    private Comparator<DriverInformation> driverSearchComparator() {
        return Comparator
                .comparing((DriverInformation driver) -> normalized(driver.getName()))
                .thenComparing(driver -> normalized(driver.getContactNumber()))
                .thenComparing(driver -> normalized(driver.getDriverLicenseNumber()))
                .thenComparing(driver -> driver.getDriverId() == null ? Long.MAX_VALUE : driver.getDriverId());
    }

    private boolean isLegacyUserIdLink(SysUser user, DriverInformation driver) {
        if (user == null || driver == null) {
            return false;
        }
        if (equalsNormalized(user.getIdCardNumber(), driver.getIdCardNumber())) {
            return true;
        }
        if (equalsNormalized(user.getRealName(), driver.getName())) {
            return true;
        }
        return equalsNormalized(user.getContactNumber(), driver.getContactNumber());
    }

    private boolean equalsNormalized(String left, String right) {
        return !isBlank(left) && !isBlank(right) && left.trim().equals(right.trim());
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String normalized(String value) {
        return value == null ? "" : value.trim().toLowerCase();
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

    private void normalizeDerivedPointSummaryForCreate(DriverInformation driverInformation) {
        if (driverInformation == null) {
            return;
        }
        driverInformation.setTotalDeductedPoints(0);
        driverInformation.setCurrentPoints(12);
    }

    private void applyDerivedPointSummaryFromRecords(DriverInformation driverInformation) {
        if (driverInformation == null || driverInformation.getDriverId() == null) {
            return;
        }
        int effectivePoints = calculateEffectiveDeductedPoints(driverInformation.getDriverId());
        driverInformation.setTotalDeductedPoints(effectivePoints);
        driverInformation.setCurrentPoints(Math.max(0, 12 - effectivePoints));
    }

    private int calculateEffectiveDeductedPoints(Long driverId) {
        QueryWrapper<DeductionRecord> wrapper = Wrappers.query();
        tenantScope(wrapper).select("deducted_points")
                .eq("driver_id", driverId)
                .apply("UPPER(TRIM(status)) = {0}", "EFFECTIVE");
        return deductionRecordMapper.selectObjs(wrapper).stream()
                .filter(Objects::nonNull)
                .mapToInt(this::toInt)
                .sum();
    }

    private int toInt(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text) {
            try {
                return Integer.parseInt(text.trim());
            } catch (NumberFormatException ignored) {
                return 0;
            }
        }
        return 0;
    }

    public DriverInformation findByExactIdCardNumber(String idCardNumber) {
        if (idCardNumber == null || idCardNumber.isBlank()) {
            return null;
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("id_card_number", idCardNumber.trim())
                .orderByDesc("updated_at")
                .orderByDesc("created_at")
                .orderByDesc("driver_id")
                .last("limit 1");
        DriverInformation driver = driverInformationMapper.selectOne(wrapper);
        if (driver != null && !databaseOnlyForTenantIsolation()) {
            driverInformationSearchRepository.save(DriverInformationDocument.fromEntity(driver));
        }
        return driver;
    }

    private void syncToIndexAfterCommit(DriverInformation driverInformation) {
        if (databaseOnlyForTenantIsolation()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            DriverInformationDocument doc = DriverInformationDocument.fromEntity(driverInformation);
            if (doc != null) {
                driverInformationSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<DriverInformation> records) {
        if (databaseOnlyForTenantIsolation() || records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<DriverInformationDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(DriverInformationDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                driverInformationSearchRepository.saveAll(documents);
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

    private void sendKafkaMessage(String topic, String idempotencyKey, DriverInformation driverInformation) {
        try {
            String payload = objectMapper.writeValueAsString(driverInformation);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception e) {
            log.log(Level.WARNING, "Failed to send driver Kafka message", e);
            throw new RuntimeException("Failed to send driver event", e);
        }
    }

    private void validateDriver(DriverInformation driverInformation) {
        if (driverInformation == null) {
            throw new IllegalArgumentException("Driver information cannot be null");
        }
        ensureUniqueIdCardNumber(driverInformation);
        ensureUniqueDriverLicenseNumber(driverInformation);
    }

    private void validateDriverId(DriverInformation driverInformation) {
        validateDriver(driverInformation);
        validateDriverId(driverInformation.getDriverId());
    }

    private void validateDriverId(Long driverId) {
        if (driverId == null || driverId <= 0) {
            throw new IllegalArgumentException("Invalid driver ID: " + driverId);
        }
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private String truncate(String value) {
        if (value == null) {
            return null;
        }
        return value.length() <= 500 ? value : value.substring(0, 500);
    }

    private void ensureUniqueIdCardNumber(DriverInformation driverInformation) {
        if (driverInformation == null || isBlank(driverInformation.getIdCardNumber())) {
            return;
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("id_card_number", driverInformation.getIdCardNumber().trim());
        if (driverInformation.getDriverId() != null) {
            wrapper.ne("driver_id", driverInformation.getDriverId());
        }
        if (driverInformationMapper.selectCount(wrapper) > 0) {
            throw new IllegalArgumentException("ID card number already exists");
        }
    }

    private void ensureUniqueDriverLicenseNumber(DriverInformation driverInformation) {
        if (driverInformation == null || isBlank(driverInformation.getDriverLicenseNumber())) {
            return;
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_license_number", driverInformation.getDriverLicenseNumber().trim());
        if (driverInformation.getDriverId() != null) {
            wrapper.ne("driver_id", driverInformation.getDriverId());
        }
        if (driverInformationMapper.selectCount(wrapper) > 0) {
            throw new IllegalArgumentException("Driver license number already exists");
        }
    }

    private void ensureNoDriverVehicleBindings(Long driverId) {
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_id", driverId);
        if (driverVehicleMapper.selectCount(wrapper) > 0) {
            throw new IllegalStateException("Cannot delete driver while vehicle bindings still exist");
        }
    }

    private void ensureNoOffenseRecords(Long driverId) {
        QueryWrapper<OffenseRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_id", driverId);
        if (offenseRecordMapper.selectCount(wrapper) > 0) {
            throw new IllegalStateException("Cannot delete driver while offense records still exist");
        }
    }

    private void ensureNoDeductionRecords(Long driverId) {
        QueryWrapper<DeductionRecord> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_id", driverId);
        if (deductionRecordMapper.selectCount(wrapper) > 0) {
            throw new IllegalStateException("Cannot delete driver while deduction records still exist");
        }
    }

    private boolean databaseOnlyForTenantIsolation() {
        return tenantAwareSupport.isIsolationEnabled();
    }

    private <T> QueryWrapper<T> tenantScope(QueryWrapper<T> wrapper) {
        return tenantAwareSupport.applyTenantScope(wrapper);
    }

    private DriverInformation findDriverByIdFromDatabase(Long driverId) {
        if (driverId == null) {
            return null;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return driverInformationMapper.selectById(driverId);
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_id", driverId).last("limit 1");
        return driverInformationMapper.selectOne(wrapper);
    }

    private int updateDriverByIdScoped(DriverInformation driverInformation) {
        if (driverInformation == null || driverInformation.getDriverId() == null) {
            return 0;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return driverInformationMapper.updateById(driverInformation);
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_id", driverInformation.getDriverId());
        return driverInformationMapper.update(driverInformation, wrapper);
    }

    private int deleteDriverByIdScoped(Long driverId) {
        if (driverId == null) {
            return 0;
        }
        if (!databaseOnlyForTenantIsolation()) {
            return driverInformationMapper.deleteById(driverId);
        }
        QueryWrapper<DriverInformation> wrapper = new QueryWrapper<>();
        tenantScope(wrapper).eq("driver_id", driverId);
        return driverInformationMapper.delete(wrapper);
    }

    private static TenantAwareSupport defaultTenantAwareSupport() {
        ProductGovernanceProperties productGovernanceProperties = new ProductGovernanceProperties();
        productGovernanceProperties.setTenantIsolationEnabled(false);
        return new TenantAwareSupport(productGovernanceProperties, new TenantIsolationProperties());
    }

    @FunctionalInterface
    private interface FunctionWithException<T, R> {
        R apply(T t) throws Exception;
    }
}
