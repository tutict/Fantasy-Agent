package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.DriverVehicle;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.entity.elastic.DriverVehicleDocument;
import com.tutict.finalassignmentbackend.mapper.DriverInformationMapper;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.VehicleInformationMapper;
import com.tutict.finalassignmentbackend.repository.DriverVehicleSearchRepository;
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

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class DriverVehicleService {

    private static final Logger log = Logger.getLogger(DriverVehicleService.class.getName());
    private static final String CACHE_NAME = "driverVehicleCache";
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final DriverVehicleMapper driverVehicleMapper;
    private final DriverInformationMapper driverInformationMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final DriverVehicleSearchRepository driverVehicleSearchRepository;
    private final VehicleInformationMapper vehicleInformationMapper;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public DriverVehicleService(DriverVehicleMapper driverVehicleMapper,
                                DriverInformationMapper driverInformationMapper,
                                SysRequestHistoryMapper sysRequestHistoryMapper,
                                DriverVehicleSearchRepository driverVehicleSearchRepository,
                                VehicleInformationMapper vehicleInformationMapper,
                                KafkaTemplate<String, String> kafkaTemplate,
                                ObjectMapper objectMapper) {
        this.driverVehicleMapper = driverVehicleMapper;
        this.driverInformationMapper = driverInformationMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.driverVehicleSearchRepository = driverVehicleSearchRepository;
        this.vehicleInformationMapper = vehicleInformationMapper;
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "DriverVehicleService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, DriverVehicle binding, String action) {
        Objects.requireNonNull(binding, "DriverVehicle must not be null");
        SysRequestHistory existing = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            log.warning(() -> String.format("Duplicate driver-vehicle binding request detected (key=%s)", idempotencyKey));
            throw new RuntimeException("Duplicate driver-vehicle request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, binding, action);
        sysRequestHistoryMapper.insert(history);

        sendKafkaMessage("driver_vehicle_" + action, idempotencyKey, binding);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public DriverVehicle createBinding(DriverVehicle binding) {
        validateBinding(binding);
        enforcePrimaryConstraints(binding);
        driverVehicleMapper.insert(binding);
        syncToIndexAfterCommit(binding);
        return binding;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public DriverVehicle updateBinding(DriverVehicle binding) {
        validateBinding(binding);
        requirePositive(binding.getId(), "Binding ID");
        enforcePrimaryConstraints(binding);
        int rows = driverVehicleMapper.updateById(binding);
        if (rows == 0) {
            throw new IllegalStateException("Driver-vehicle binding not found for id=" + binding.getId());
        }
        syncToIndexAfterCommit(binding);
        return binding;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteBinding(Long id) {
        requirePositive(id, "Binding ID");
        int rows = driverVehicleMapper.deleteById(id);
        if (rows == 0) {
            throw new IllegalStateException("Driver-vehicle binding not found for id=" + id);
        }
        runAfterCommitOrNow(() -> driverVehicleSearchRepository.deleteById(id));
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#id", unless = "#result == null")
    public DriverVehicle findById(Long id) {
        requirePositive(id, "Binding ID");
        return driverVehicleSearchRepository.findById(id)
                .map(DriverVehicleDocument::toEntity)
                .orElseGet(() -> {
                    DriverVehicle entity = driverVehicleMapper.selectById(id);
                    if (entity != null) {
                        driverVehicleSearchRepository.save(DriverVehicleDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<DriverVehicle> findAll() {
        List<DriverVehicle> fromIndex = StreamSupport.stream(driverVehicleSearchRepository.findAll().spliterator(), false)
                .map(DriverVehicleDocument::toEntity)
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
    public List<DriverVehicle> findAll(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.orderByDesc("is_primary")
                .orderByDesc("id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'driver:' + #driverId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DriverVehicle> findByDriverId(Long driverId, int page, int size) {
        requirePositive(driverId, "Driver ID");
        validatePagination(page, size);
        List<DriverVehicle> fromIndex = mapHits(driverVehicleSearchRepository.findByDriverId(driverId, pageable(page, size)));
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.eq("driver_id", driverId)
                .orderByDesc("is_primary");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'vehicle:' + #vehicleId + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DriverVehicle> findByVehicleId(Long vehicleId, int page, int size) {
        requirePositive(vehicleId, "Vehicle ID");
        validatePagination(page, size);
        List<DriverVehicle> fromIndex = mapHits(driverVehicleSearchRepository.findByVehicleId(vehicleId, pageable(page, size)));
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.eq("vehicle_id", vehicleId)
                .orderByDesc("is_primary");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'primary:' + #driverId", unless = "#result == null || #result.isEmpty()")
    public List<DriverVehicle> findPrimaryBinding(Long driverId) {
        requirePositive(driverId, "Driver ID");
        List<DriverVehicle> fromIndex = mapHits(driverVehicleSearchRepository.findPrimaryBinding(driverId, pageable(1, 5)));
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.eq("driver_id", driverId)
                .eq("is_primary", true);
        return fetchFromDatabase(wrapper, 1, 5);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'relationship:' + #relationship + ':' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<DriverVehicle> searchByRelationship(String relationship, int page, int size) {
        if (isBlank(relationship)) {
            return List.of();
        }
        validatePagination(page, size);
        List<DriverVehicle> fromIndex = mapHits(driverVehicleSearchRepository.searchByRelationship(relationship, pageable(page, size)));
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.like("relationship", relationship);
        return fetchFromDatabase(wrapper, page, size);
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public void markHistorySuccess(String idempotencyKey, Long bindingId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            log.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(bindingId);
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

    private SysRequestHistory buildHistory(String idempotencyKey, DriverVehicle binding, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod(resolveRequestMethod("POST"));
        history.setRequestUrl(resolveRequestUrl(resolveDefaultRequestUrl(binding)));
        history.setRequestParams(buildRequestParams(binding));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setRequestIp(resolveRequestIp());
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String resolveDefaultRequestUrl(DriverVehicle binding) {
        Long vehicleId = binding == null ? null : binding.getVehicleId();
        return vehicleId == null ? "/api/vehicles/drivers" : "/api/vehicles/" + vehicleId + "/drivers";
    }

    private String buildRequestParams(DriverVehicle binding) {
        if (binding == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "driverId", binding.getDriverId());
        appendParam(builder, "vehicleId", binding.getVehicleId());
        appendParam(builder, "relationship", binding.getRelationship());
        appendParam(builder, "isPrimary", binding.getIsPrimary());
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "DRIVER_VEHICLE_" + normalized;
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

    private void sendKafkaMessage(String topic, String idempotencyKey, DriverVehicle binding) {
        try {
            String payload = objectMapper.writeValueAsString(binding);
            kafkaTemplate.send(topic, idempotencyKey, payload);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to send DriverVehicle Kafka message", ex);
            throw new RuntimeException("Failed to send driver-vehicle event", ex);
        }
    }

    private void syncToIndexAfterCommit(DriverVehicle binding) {
        if (binding == null) {
            return;
        }
        runAfterCommitOrNow(() -> {
            DriverVehicleDocument doc = DriverVehicleDocument.fromEntity(binding);
            if (doc != null) {
                driverVehicleSearchRepository.save(doc);
            }
        });
    }

    private void syncBatchToIndexAfterCommit(List<DriverVehicle> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> {
            List<DriverVehicleDocument> documents = records.stream()
                    .filter(Objects::nonNull)
                    .map(DriverVehicleDocument::fromEntity)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            if (!documents.isEmpty()) {
                driverVehicleSearchRepository.saveAll(documents);
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

    private List<DriverVehicle> fetchFromDatabase(QueryWrapper<DriverVehicle> wrapper, int page, int size) {
        Page<DriverVehicle> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        driverVehicleMapper.selectPage(mpPage, wrapper);
        List<DriverVehicle> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<DriverVehicle> loadAllFromDatabase() {
        List<DriverVehicle> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
            wrapper.orderByAsc("id");
            Page<DriverVehicle> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            driverVehicleMapper.selectPage(mpPage, wrapper);
            List<DriverVehicle> records = mpPage.getRecords();
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

    private List<DriverVehicle> mapHits(SearchHits<DriverVehicleDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(SearchHit::getContent)
                .map(DriverVehicleDocument::toEntity)
                .collect(Collectors.toList());
    }

    private Pageable pageable(int page, int size) {
        return PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private void validateBinding(DriverVehicle binding) {
        Objects.requireNonNull(binding, "DriverVehicle must not be null");
        requirePositive(binding.getDriverId(), "Driver ID");
        requirePositive(binding.getVehicleId(), "Vehicle ID");
        DriverInformation driver = driverInformationMapper.selectById(binding.getDriverId());
        if (driver == null) {
            throw new IllegalArgumentException("Driver does not exist: " + binding.getDriverId());
        }
        VehicleInformation vehicle = vehicleInformationMapper.selectById(binding.getVehicleId());
        if (vehicle == null) {
            throw new IllegalArgumentException("Vehicle does not exist: " + binding.getVehicleId());
        }
        if (binding.getId() != null) {
            DriverVehicle existing = driverVehicleMapper.selectById(binding.getId());
            if (existing != null) {
                if (existing.getDriverId() != null
                        && !Objects.equals(existing.getDriverId(), binding.getDriverId())) {
                    throw new IllegalArgumentException("Driver ID cannot be changed for an existing binding");
                }
                if (existing.getVehicleId() != null
                        && !Objects.equals(existing.getVehicleId(), binding.getVehicleId())) {
                    throw new IllegalArgumentException("Vehicle ID cannot be changed for an existing binding");
                }
            }
        }
        if (binding.getBindDate() == null) {
            binding.setBindDate(LocalDate.now());
        }
        if (binding.getUnbindDate() != null && binding.getUnbindDate().isBefore(binding.getBindDate())) {
            throw new IllegalArgumentException("Unbind date cannot be before bind date");
        }
        if (binding.getIsPrimary() == null) {
            binding.setIsPrimary(false);
        }
        if (isBlank(binding.getStatus())) {
            binding.setStatus("Active");
        }
        ensureNoDuplicateActiveBinding(binding);
    }

    private void enforcePrimaryConstraints(DriverVehicle binding) {
        if (!Boolean.TRUE.equals(binding.getIsPrimary())) {
            return;
        }
        // 每位驾驶员仅允许一个主绑定，出现重复时自动降级旧数据
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.eq("driver_id", binding.getDriverId())
                .eq("is_primary", true);
        demoteOtherPrimaryBindings("driver_id", binding.getDriverId(), binding.getId(), "driver");
        demoteOtherPrimaryBindings("vehicle_id", binding.getVehicleId(), binding.getId(), "vehicle");
    }

    private void ensureNoDuplicateActiveBinding(DriverVehicle binding) {
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.eq("driver_id", binding.getDriverId())
                .eq("vehicle_id", binding.getVehicleId());
        List<DriverVehicle> existingBindings = driverVehicleMapper.selectList(wrapper);
        for (DriverVehicle existing : existingBindings) {
            if (existing == null || Objects.equals(existing.getId(), binding.getId())) {
                continue;
            }
            if (!"Inactive".equalsIgnoreCase(trimToEmpty(existing.getStatus()))) {
                throw new IllegalStateException("An active binding already exists for this driver and vehicle");
            }
        }
    }

    private void demoteOtherPrimaryBindings(String fieldName,
                                            Long fieldValue,
                                            Long currentBindingId,
                                            String scope) {
        QueryWrapper<DriverVehicle> wrapper = new QueryWrapper<>();
        wrapper.eq(fieldName, fieldValue)
                .eq("is_primary", true);
        List<DriverVehicle> primaryBindings = driverVehicleMapper.selectList(wrapper);
        for (DriverVehicle existing : primaryBindings) {
            if (existing == null || Objects.equals(existing.getId(), currentBindingId)) {
                continue;
            }
            log.log(Level.INFO, "Demoting existing primary binding {0} for {1} {2}",
                    new Object[]{existing.getId(), scope, fieldValue});
            existing.setIsPrimary(false);
            driverVehicleMapper.updateById(existing);
            syncToIndexAfterCommit(existing);
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

    private String truncate(String value) {
        if (value == null) {
            return null;
        }
        return value.length() <= 500 ? value : value.substring(0, 500);
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
