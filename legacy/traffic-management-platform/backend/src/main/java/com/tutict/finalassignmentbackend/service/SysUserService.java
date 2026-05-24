package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.tutict.finalassignmentbackend.config.tenant.TenantAwareSupport;
import com.tutict.finalassignmentbackend.config.login.jwt.AuthenticationSnapshotService;
import com.tutict.finalassignmentbackend.config.websocket.WsAction;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.elastic.SysUserDocument;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.SysUserMapper;
import com.tutict.finalassignmentbackend.repository.SysUserSearchRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.StringUtils;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.Collections;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class SysUserService {

    private static final Logger LOG = Logger.getLogger(SysUserService.class.getName());
    private static final String CACHE_NAME = "sysUserCache";
    private static final Pattern BCRYPT_PATTERN = Pattern.compile("^\\$2[aby]?\\$.{56}$");
    private static final int FULL_LOAD_BATCH_SIZE = 500;

    private final SysUserMapper sysUserMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final SysUserSearchRepository sysUserSearchRepository;
    private final PasswordEncoder passwordEncoder;
    private final CacheManager cacheManager;
    private final AuthenticationSnapshotService authenticationSnapshotService;
    private final TenantAwareSupport tenantAwareSupport;

    @Autowired
    public SysUserService(SysUserMapper sysUserMapper,
                          SysRequestHistoryMapper sysRequestHistoryMapper,
                          SysUserSearchRepository sysUserSearchRepository,
                          PasswordEncoder passwordEncoder,
                          CacheManager cacheManager,
                          AuthenticationSnapshotService authenticationSnapshotService,
                          TenantAwareSupport tenantAwareSupport) {
        this.sysUserMapper = sysUserMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.sysUserSearchRepository = sysUserSearchRepository;
        this.passwordEncoder = passwordEncoder;
        this.cacheManager = cacheManager;
        this.authenticationSnapshotService = authenticationSnapshotService;
        this.tenantAwareSupport = tenantAwareSupport;
    }

    public SysUserService(SysUserMapper sysUserMapper,
                          SysRequestHistoryMapper sysRequestHistoryMapper,
                          SysUserSearchRepository sysUserSearchRepository,
                          PasswordEncoder passwordEncoder,
                          CacheManager cacheManager) {
        this(sysUserMapper, sysRequestHistoryMapper, sysUserSearchRepository, passwordEncoder, cacheManager, null, null);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    @WsAction(service = "SysUserService", action = "checkAndInsertIdempotency")
    public void checkAndInsertIdempotency(String idempotencyKey, SysUser sysUser, String action) {
        Objects.requireNonNull(sysUser, "SysUser must not be null");
        SysRequestHistory existing = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (existing != null) {
            LOG.warning(() -> String.format("Duplicate sys user request detected (key=%s)", idempotencyKey));
            throw new RuntimeException("Duplicate sys user request detected");
        }

        SysRequestHistory history = buildHistory(idempotencyKey, sysUser, action);
        sysRequestHistoryMapper.insert(history);
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysUser createSysUser(SysUser sysUser) {
        validateSysUser(sysUser);
        preparePasswordForPersistence(sysUser);
        sysUserMapper.insert(sysUser);
        evictAuthenticationSnapshots();
        syncToIndexAfterCommit(sysUser);
        return sysUser;
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public SysUser updateSysUser(SysUser sysUser) {
        return persistExistingUser(sysUser);
    }

    @Transactional
    public SysUser updatePassword(SysUser sysUser, String rawPassword) {
        if (sysUser == null) {
            throw new IllegalArgumentException("SysUser must not be null");
        }
        if (isBlank(rawPassword)) {
            throw new IllegalArgumentException("Password must not be blank");
        }
        sysUser.setPassword(rawPassword.trim());
        sysUser.setPasswordUpdateTime(LocalDateTime.now());
        sysUser.setUpdatedAt(LocalDateTime.now());
        SysUser updated = persistExistingUser(sysUser);
        evictUserCache();
        return updated;
    }

    @Transactional
    public boolean verifyPassword(SysUser sysUser, String rawPassword) {
        if (sysUser == null || isBlank(rawPassword) || isBlank(sysUser.getPassword())) {
            return false;
        }
        String candidate = rawPassword.trim();
        String storedPassword = sysUser.getPassword().trim();
        if (isEncodedPassword(storedPassword)) {
            return passwordEncoder.matches(candidate, storedPassword);
        }
        boolean matched = Objects.equals(storedPassword, candidate);
        if (matched) {
            LOG.log(Level.INFO, "Upgrading legacy plaintext password for userId={0}", sysUser.getUserId());
            sysUser.setPassword(candidate);
            sysUser.setPasswordUpdateTime(LocalDateTime.now());
            sysUser.setUpdatedAt(LocalDateTime.now());
            persistExistingUser(sysUser);
            evictUserCache();
        }
        return matched;
    }

    @Transactional
    public void recordLoginFailure(SysUser sysUser) {
        if (sysUser == null || sysUser.getUserId() == null) {
            return;
        }
        Integer currentFailures = sysUser.getLoginFailures();
        sysUser.setLoginFailures(currentFailures == null ? 1 : currentFailures + 1);
        sysUser.setUpdatedAt(LocalDateTime.now());
        persistExistingUser(sysUser);
        evictUserCache();
    }

    @Transactional
    public void resetLoginFailures(SysUser sysUser) {
        if (sysUser == null || sysUser.getUserId() == null) {
            return;
        }
        sysUser.setLoginFailures(0);
        sysUser.setUpdatedAt(LocalDateTime.now());
        persistExistingUser(sysUser);
        evictUserCache();
    }

    @Transactional
    public void recordSuccessfulLogin(SysUser sysUser, String loginIp) {
        if (sysUser == null || sysUser.getUserId() == null) {
            return;
        }
        sysUser.setLoginFailures(0);
        sysUser.setLastLoginTime(LocalDateTime.now());
        sysUser.setLastLoginIp(isBlank(loginIp) ? "127.0.0.1" : loginIp.trim());
        sysUser.setUpdatedAt(LocalDateTime.now());
        persistExistingUser(sysUser);
        evictUserCache();
    }

    @Transactional
    @CacheEvict(cacheNames = CACHE_NAME, allEntries = true)
    public void deleteSysUser(Long userId) {
        requirePositive(userId);
        int rows = sysUserMapper.deleteById(userId);
        if (rows == 0) {
            throw new IllegalStateException("SysUser not found for id=" + userId);
        }
        evictAuthenticationSnapshots();
        runAfterCommitOrNow(() -> sysUserSearchRepository.deleteById(userId));
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "#userId", unless = "#result == null")
    public SysUser findById(Long userId) {
        requirePositive(userId);
        if (tenantAwareSupport != null && tenantAwareSupport.isIsolationEnabled()) {
            QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
            wrapper.eq("user_id", userId).last("limit 1");
            tenantAwareSupport.applyTenantScope(wrapper);
            return sysUserMapper.selectOne(wrapper);
        }
        return sysUserSearchRepository.findById(userId)
                .map(SysUserDocument::toEntity)
                .orElseGet(() -> {
                    SysUser entity = sysUserMapper.selectById(userId);
                    if (entity != null) {
                        sysUserSearchRepository.save(SysUserDocument.fromEntity(entity));
                    }
                    return entity;
                });
    }

    @Transactional(readOnly = true)
    public List<SysUser> findAll() {
        List<SysUser> fromIndex = StreamSupport.stream(
                        sysUserSearchRepository.findAll().spliterator(), false)
                .map(SysUserDocument::toEntity)
                .collect(Collectors.toList());
        if (!fromIndex.isEmpty()) {
            return fromIndex;
        }
        return loadAllFromDatabase();
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'list:' + #page + ':' + #size", unless = "#result == null || #result.isEmpty()")
    public List<SysUser> listUsers(int page, int size) {
        validatePagination(page, size);
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        if (tenantAwareSupport != null) {
            tenantAwareSupport.applyTenantScope(wrapper);
        }
        wrapper.orderByAsc("username")
                .orderByAsc("user_id");
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'usernamePrefix:' + #username + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByUsernamePrefix(String username, int page, int size) {
        if (isBlank(username)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByUsernamePrefix(username, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.likeRight("username", username);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'usernameFuzzy:' + #username + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByUsernameFuzzy(String username, int page, int size) {
        if (isBlank(username)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByUsernameFuzzy(username, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.like("username", username);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'realNamePrefix:' + #realName + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByRealNamePrefix(String realName, int page, int size) {
        if (isBlank(realName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByRealNamePrefix(realName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.likeRight("real_name", realName);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'realNameFuzzy:' + #realName + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByRealNameFuzzy(String realName, int page, int size) {
        if (isBlank(realName)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByRealNameFuzzy(realName, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.like("real_name", realName);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'idCard:' + #idCardNumber + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByIdCardNumber(String idCardNumber, int page, int size) {
        if (isBlank(idCardNumber)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByIdCardNumber(idCardNumber, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("id_card_number", idCardNumber);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'contact:' + #contactNumber + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByContactNumber(String contactNumber, int page, int size) {
        if (isBlank(contactNumber)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByContactNumber(contactNumber, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.likeRight("contact_number", contactNumber);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'email:' + #email + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByEmail(String email, int page, int size) {
        if (isBlank(email)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByEmail(email, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.likeRight("email", email);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'deptPrefix:' + #department + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByDepartmentPrefix(String department, int page, int size) {
        if (isBlank(department)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByDepartment(department, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.likeRight("department", department);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'employee:' + #employeeNumber + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByEmployeeNumber(String employeeNumber, int page, int size) {
        if (isBlank(employeeNumber)) {
            return List.of();
        }
        validatePagination(page, size);
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByEmployeeNumber(employeeNumber, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("employee_number", employeeNumber);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'username:' + #username", unless = "#result == null")
    public SysUser findByUsername(String username) {
        if (isBlank(username)) {
            return null;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("username", username);
        if (tenantAwareSupport != null) {
            tenantAwareSupport.applyTenantScope(wrapper);
        }
        SysUser entity = sysUserMapper.selectOne(wrapper);
        if (entity != null) {
            syncToIndexAfterCommit(entity);
        }
        return entity;
    }

    public boolean isUsernameExists(String username) {
        if (isBlank(username)) {
            return false;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("username", username);
        if (tenantAwareSupport != null) {
            tenantAwareSupport.applyTenantScope(wrapper);
        }
        return sysUserMapper.selectCount(wrapper) > 0;
    }

    @Transactional(readOnly = true)
    public SysUser findByExactEmail(String email) {
        if (isBlank(email)) {
            return null;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("email", email.trim()).last("limit 1");
        return sysUserMapper.selectOne(wrapper);
    }

    @Transactional(readOnly = true)
    public SysUser findByExactIdCardNumber(String idCardNumber) {
        if (isBlank(idCardNumber)) {
            return null;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("id_card_number", idCardNumber.trim()).last("limit 1");
        return sysUserMapper.selectOne(wrapper);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'status:' + #status + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> findByStatus(String status, int page, int size) {
        validatePagination(page, size);
        if (isBlank(status)) {
            return Collections.emptyList();
        }
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByStatus(status, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("status", status);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Transactional(readOnly = true)
    @Cacheable(cacheNames = CACHE_NAME, key = "'dept:' + #department + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> findByDepartment(String department, int page, int size) {
        validatePagination(page, size);
        if (isBlank(department)) {
            return Collections.emptyList();
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.eq("department", department);
        return fetchFromDatabase(wrapper, page, size);
    }

    @Cacheable(cacheNames = CACHE_NAME, key = "'lastLogin:' + #startTime + ':' + #endTime + ':' + #page + ':' + #size",
            unless = "#result == null || #result.isEmpty()")
    public List<SysUser> searchByLastLoginTimeRange(String startTime, String endTime, int page, int size) {
        validatePagination(page, size);
        LocalDateTime start = parseDateTime(startTime, "startTime");
        LocalDateTime end = parseDateTime(endTime, "endTime");
        if (start == null || end == null) {
            return List.of();
        }
        List<SysUser> index = mapHits(sysUserSearchRepository.searchByLastLoginTimeRange(startTime, endTime, pageable(page, size)));
        if (!index.isEmpty()) {
            return index;
        }
        QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
        wrapper.between("last_login_time", start, end);
        return fetchFromDatabase(wrapper, page, size);
    }

    public List<SysUser> getAllUsers() {
        return findAll();
    }

    public boolean shouldSkipProcessing(String idempotencyKey) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        return history != null
                && "SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && history.getBusinessId() > 0;
    }

    public PasswordChangeIdempotencyStatus beginPasswordChange(String idempotencyKey,
                                                               Long userId,
                                                               String fingerprint) {
        if (isBlank(idempotencyKey)) {
            return PasswordChangeIdempotencyStatus.STARTED;
        }
        if (userId == null || userId <= 0) {
            throw new IllegalArgumentException("User ID must be positive");
        }
        if (isBlank(fingerprint)) {
            throw new IllegalArgumentException("Password change fingerprint must not be blank");
        }

        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            sysRequestHistoryMapper.insert(buildPasswordChangeHistory(idempotencyKey, userId, fingerprint));
            return PasswordChangeIdempotencyStatus.STARTED;
        }
        if (!"SYS_USER_PASSWORD_UPDATE".equalsIgnoreCase(history.getBusinessType())
                || (history.getUserId() != null && !Objects.equals(history.getUserId(), userId))) {
            return PasswordChangeIdempotencyStatus.CONFLICT;
        }
        String recordedFingerprint = extractRequestParam(history.getRequestParams(), "fingerprint");
        if (StringUtils.hasText(recordedFingerprint) && !recordedFingerprint.equals(fingerprint)) {
            return PasswordChangeIdempotencyStatus.CONFLICT;
        }
        if ("SUCCESS".equalsIgnoreCase(history.getBusinessStatus())
                && history.getBusinessId() != null
                && Objects.equals(history.getBusinessId(), userId)) {
            return PasswordChangeIdempotencyStatus.ALREADY_SUCCEEDED;
        }
        if ("PROCESSING".equalsIgnoreCase(history.getBusinessStatus())) {
            return PasswordChangeIdempotencyStatus.ALREADY_PROCESSING;
        }
        history.setBusinessStatus("PROCESSING");
        history.setBusinessId(null);
        history.setRequestParams(buildPasswordChangeRequestParams(userId, fingerprint));
        history.setUpdatedAt(LocalDateTime.now());
        sysRequestHistoryMapper.updateById(history);
        return PasswordChangeIdempotencyStatus.STARTED;
    }

    public String buildPasswordChangeFingerprint(String currentPassword, String newPassword) {
        if (isBlank(currentPassword) || isBlank(newPassword)) {
            throw new IllegalArgumentException("Password values must not be blank");
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest((currentPassword.trim() + "\n" + newPassword.trim())
                    .getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(bytes);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is not available", e);
        }
    }

    public void markPasswordChangeSuccess(String idempotencyKey, Long userId) {
        if (!isBlank(idempotencyKey)) {
            markHistorySuccess(idempotencyKey, userId);
        }
    }

    public void markPasswordChangeFailure(String idempotencyKey, String reason) {
        if (!isBlank(idempotencyKey)) {
            markHistoryFailure(idempotencyKey, reason);
        }
    }

    public void markHistorySuccess(String idempotencyKey, Long userId) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            LOG.log(Level.WARNING, "Cannot mark success for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("SUCCESS");
        history.setBusinessId(userId);
        history.setUpdatedAt(LocalDateTime.now());
        sysRequestHistoryMapper.updateById(history);
    }

    public void markHistoryFailure(String idempotencyKey, String reason) {
        SysRequestHistory history = sysRequestHistoryMapper.selectByIdempotencyKey(idempotencyKey);
        if (history == null) {
            LOG.log(Level.WARNING, "Cannot mark failure for missing idempotency key {0}", idempotencyKey);
            return;
        }
        history.setBusinessStatus("FAILED");
        history.setRequestParams(appendFailureReason(history.getRequestParams(), reason));
        history.setUpdatedAt(LocalDateTime.now());
        sysRequestHistoryMapper.updateById(history);
    }

    private SysRequestHistory buildHistory(String idempotencyKey, SysUser sysUser, String action) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("POST");
        history.setRequestUrl("/api/sys/users");
        history.setRequestParams(buildRequestParams(sysUser));
        history.setBusinessType(resolveBusinessType(action));
        history.setBusinessStatus("PROCESSING");
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private SysRequestHistory buildPasswordChangeHistory(String idempotencyKey, Long userId, String fingerprint) {
        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey(idempotencyKey);
        history.setRequestMethod("PUT");
        history.setRequestUrl("/api/users/me/password");
        history.setRequestParams(buildPasswordChangeRequestParams(userId, fingerprint));
        history.setBusinessType("SYS_USER_PASSWORD_UPDATE");
        history.setBusinessStatus("PROCESSING");
        history.setBusinessId(null);
        history.setUserId(userId);
        history.setCreatedAt(LocalDateTime.now());
        history.setUpdatedAt(LocalDateTime.now());
        return history;
    }

    private String buildRequestParams(SysUser sysUser) {
        if (sysUser == null) {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "username", sysUser.getUsername());
        appendParam(builder, "realName", sysUser.getRealName());
        appendParam(builder, "department", sysUser.getDepartment());
        appendParam(builder, "employeeNumber", sysUser.getEmployeeNumber());
        appendParam(builder, "status", sysUser.getStatus());
        return truncate(builder.toString());
    }

    private String buildPasswordChangeRequestParams(Long userId, String fingerprint) {
        StringBuilder builder = new StringBuilder();
        appendParam(builder, "userId", userId);
        appendParam(builder, "operation", "PASSWORD_CHANGE");
        appendParam(builder, "fingerprint", fingerprint);
        return truncate(builder.toString());
    }

    private String resolveBusinessType(String action) {
        String normalized = isBlank(action) ? "CREATE" : action.trim().toUpperCase();
        return "SYS_USER_" + normalized;
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

    private String extractRequestParam(String requestParams, String key) {
        if (isBlank(requestParams) || isBlank(key)) {
            return null;
        }
        for (String part : requestParams.split(",")) {
            int separator = part.indexOf('=');
            if (separator <= 0) {
                continue;
            }
            String candidateKey = part.substring(0, separator).trim();
            if (!candidateKey.equalsIgnoreCase(key)) {
                continue;
            }
            String value = part.substring(separator + 1).trim();
            return value.isEmpty() ? null : value;
        }
        return null;
    }

    private void syncToIndexAfterCommit(SysUser sysUser) {
        if (sysUser == null) {
            return;
        }
        SysUserDocument doc = SysUserDocument.fromEntity(sysUser);
        if (doc == null) {
            return;
        }
        runAfterCommitOrNow(() -> sysUserSearchRepository.save(doc));
    }

    private void syncBatchToIndexAfterCommit(List<SysUser> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        List<SysUserDocument> documents = records.stream()
                .filter(Objects::nonNull)
                .map(SysUserDocument::fromEntity)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
        if (documents.isEmpty()) {
            return;
        }
        runAfterCommitOrNow(() -> sysUserSearchRepository.saveAll(documents));
    }

    private void validateSysUser(SysUser sysUser) {
        if (sysUser == null) {
            throw new IllegalArgumentException("SysUser must not be null");
        }
        if (isBlank(sysUser.getUsername())) {
            throw new IllegalArgumentException("Username must not be blank");
        }
        if (isBlank(sysUser.getPassword())) {
            throw new IllegalArgumentException("Password must not be blank");
        }
        sysUser.setUsername(sysUser.getUsername().trim());
        if (sysUser.getCreatedAt() == null) {
            sysUser.setCreatedAt(LocalDateTime.now());
        }
        if (sysUser.getUpdatedAt() == null) {
            sysUser.setUpdatedAt(LocalDateTime.now());
        }
        if (isBlank(sysUser.getStatus())) {
            sysUser.setStatus("Active");
        }
    }

    private void preparePasswordForPersistence(SysUser sysUser) {
        String normalizedPassword = sysUser.getPassword().trim();
        boolean needsEncoding = !isEncodedPassword(normalizedPassword);
        if (needsEncoding) {
            sysUser.setPassword(passwordEncoder.encode(normalizedPassword));
            if (sysUser.getPasswordUpdateTime() == null) {
                sysUser.setPasswordUpdateTime(LocalDateTime.now());
            }
            return;
        }
        sysUser.setPassword(normalizedPassword);
    }

    private SysUser persistExistingUser(SysUser sysUser) {
        validateSysUser(sysUser);
        requirePositive(sysUser.getUserId());
        preparePasswordForPersistence(sysUser);
        int rows = sysUserMapper.updateById(sysUser);
        if (rows == 0) {
            throw new IllegalStateException("SysUser not found for id=" + sysUser.getUserId());
        }
        evictAuthenticationSnapshots();
        syncToIndexAfterCommit(sysUser);
        return sysUser;
    }

    private void validatePagination(int page, int size) {
        if (page < 1 || size < 1) {
            throw new IllegalArgumentException("Page must be >= 1 and size must be >= 1");
        }
    }

    private List<SysUser> fetchFromDatabase(QueryWrapper<SysUser> wrapper, int page, int size) {
        Page<SysUser> mpPage = new Page<>(Math.max(page, 1), Math.max(size, 1));
        sysUserMapper.selectPage(mpPage, wrapper);
        List<SysUser> records = mpPage.getRecords();
        syncBatchToIndexAfterCommit(records);
        return records;
    }

    private List<SysUser> loadAllFromDatabase() {
        List<SysUser> allRecords = new java.util.ArrayList<>();
        long currentPage = 1L;
        while (true) {
            QueryWrapper<SysUser> wrapper = new QueryWrapper<>();
            if (tenantAwareSupport != null) {
                tenantAwareSupport.applyTenantScope(wrapper);
            }
            wrapper.orderByAsc("user_id");
            Page<SysUser> mpPage = new Page<>(currentPage, FULL_LOAD_BATCH_SIZE);
            sysUserMapper.selectPage(mpPage, wrapper);
            List<SysUser> records = mpPage.getRecords();
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

    private List<SysUser> mapHits(org.springframework.data.elasticsearch.core.SearchHits<SysUserDocument> hits) {
        if (hits == null || !hits.hasSearchHits()) {
            return List.of();
        }
        return hits.getSearchHits().stream()
                .map(org.springframework.data.elasticsearch.core.SearchHit::getContent)
                .map(SysUserDocument::toEntity)
                .collect(Collectors.toList());
    }

    private org.springframework.data.domain.Pageable pageable(int page, int size) {
        return org.springframework.data.domain.PageRequest.of(Math.max(page - 1, 0), Math.max(size, 1));
    }

    private LocalDateTime parseDateTime(String value, String fieldName) {
        if (isBlank(value)) {
            return null;
        }
        try {
            return LocalDateTime.parse(value);
        } catch (DateTimeParseException ex) {
            LOG.log(Level.WARNING, "Failed to parse " + fieldName + ": " + value, ex);
            return null;
        }
    }

    private void requirePositive(Number number) {
        if (number == null || number.longValue() <= 0) {
            throw new IllegalArgumentException("User ID" + " must be greater than zero");
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private boolean isEncodedPassword(String password) {
        return !isBlank(password) && BCRYPT_PATTERN.matcher(password.trim()).matches();
    }

    private void evictUserCache() {
        Cache cache = cacheManager.getCache(CACHE_NAME);
        if (cache != null) {
            cache.clear();
        }
    }

    private void evictAuthenticationSnapshots() {
        if (authenticationSnapshotService != null) {
            authenticationSnapshotService.evictAll();
        }
    }

    private String truncate(String value) {
        if (value == null) {
            return null;
        }
        return value.length() <= 500 ? value : value.substring(0, 500);
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

    public enum PasswordChangeIdempotencyStatus {
        STARTED,
        ALREADY_SUCCEEDED,
        ALREADY_PROCESSING,
        CONFLICT
    }
}
