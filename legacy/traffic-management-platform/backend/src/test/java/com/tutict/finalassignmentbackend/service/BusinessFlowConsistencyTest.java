package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.login.jwt.TokenProvider;
import com.tutict.finalassignmentbackend.config.statemachine.events.AppealAcceptanceEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.AppealProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.OffenseProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.PaymentEvent;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealAcceptanceState;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.OffenseProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.controller.DriverInformationController;
import com.tutict.finalassignmentbackend.controller.OffenseInformationController;
import com.tutict.finalassignmentbackend.controller.AppealManagementController;
import com.tutict.finalassignmentbackend.controller.PaymentRecordController;
import com.tutict.finalassignmentbackend.controller.TrafficViolationController;
import com.tutict.finalassignmentbackend.controller.VehicleInformationController;
import com.tutict.finalassignmentbackend.controller.WorkflowController;
import com.tutict.finalassignmentbackend.controller.view.OffenseDetailsController;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.AppealReview;
import com.tutict.finalassignmentbackend.entity.AuditLoginLog;
import com.tutict.finalassignmentbackend.entity.AuditOperationLog;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.DriverVehicle;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.OffenseTypeDict;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysRolePermission;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.SysUserRole;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.enums.DataScope;
import com.tutict.finalassignmentbackend.enums.RoleType;
import com.tutict.finalassignmentbackend.controller.ProgressItemController;
import com.tutict.finalassignmentbackend.mapper.AppealRecordMapper;
import com.tutict.finalassignmentbackend.mapper.AppealReviewMapper;
import com.tutict.finalassignmentbackend.mapper.AuditLoginLogMapper;
import com.tutict.finalassignmentbackend.mapper.AuditOperationLogMapper;
import com.tutict.finalassignmentbackend.mapper.DeductionRecordMapper;
import com.tutict.finalassignmentbackend.mapper.DriverInformationMapper;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.FineRecordMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.PaymentRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRolePermissionMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.SysUserMapper;
import com.tutict.finalassignmentbackend.mapper.SysUserRoleMapper;
import com.tutict.finalassignmentbackend.mapper.VehicleInformationMapper;
import com.tutict.finalassignmentbackend.repository.AppealRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.AppealReviewSearchRepository;
import com.tutict.finalassignmentbackend.repository.AuditLoginLogSearchRepository;
import com.tutict.finalassignmentbackend.repository.AuditOperationLogSearchRepository;
import com.tutict.finalassignmentbackend.repository.DeductionRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.DriverInformationSearchRepository;
import com.tutict.finalassignmentbackend.repository.DriverVehicleSearchRepository;
import com.tutict.finalassignmentbackend.repository.FineRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.OffenseInformationSearchRepository;
import com.tutict.finalassignmentbackend.repository.PaymentRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysRolePermissionSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysRequestHistorySearchRepository;
import com.tutict.finalassignmentbackend.repository.SysUserSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysUserRoleSearchRepository;
import com.tutict.finalassignmentbackend.repository.VehicleInformationSearchRepository;
import com.tutict.finalassignmentbackend.service.statemachine.StateMachineService;
import jakarta.annotation.security.RolesAllowed;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.cache.CacheManager;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.lang.reflect.Method;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class BusinessFlowConsistencyTest {

    @AfterEach
    void tearDown() {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.clearSynchronization();
        }
        SecurityContextHolder.clearContext();
        RequestContextHolder.resetRequestAttributes();
    }

    @Test
    void updateOffenseShouldKeepExistingProcessStatus() {
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        OffenseInformationSearchRepository searchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        OffenseRecordService service = new OffenseRecordService(
                offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        OffenseRecord existing = new OffenseRecord();
        existing.setOffenseId(10L);
        existing.setProcessStatus(OffenseProcessState.PROCESSED.getCode());
        when(offenseRecordMapper.selectById(10L)).thenReturn(existing);
        when(offenseRecordMapper.updateById(any(OffenseRecord.class))).thenReturn(1);

        OffenseRecord request = new OffenseRecord();
        request.setOffenseId(10L);
        request.setDriverId(101L);
        request.setVehicleId(201L);
        request.setProcessStatus(OffenseProcessState.CANCELLED.getCode());

        service.updateOffenseRecord(request);

        ArgumentCaptor<OffenseRecord> captor = ArgumentCaptor.forClass(OffenseRecord.class);
        verify(offenseRecordMapper).updateById(captor.capture());
        assertEquals(OffenseProcessState.PROCESSED.getCode(), captor.getValue().getProcessStatus());
    }

    @Test
    void createOffenseShouldRejectMissingDriverOrVehicle() {
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        OffenseInformationSearchRepository searchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        OffenseRecordService service = new OffenseRecordService(
                offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        OffenseRecord request = new OffenseRecord();
        request.setVehicleId(201L);

        assertThrows(IllegalArgumentException.class, () -> service.createOffenseRecord(request));
        verify(offenseRecordMapper, never()).insert(any(OffenseRecord.class));
    }

    @Test
    void createOffenseShouldRejectNegativePenaltyFields() {
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        OffenseInformationSearchRepository searchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        OffenseRecordService service = new OffenseRecordService(
                offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        OffenseRecord request = new OffenseRecord();
        request.setDriverId(101L);
        request.setVehicleId(201L);
        request.setFineAmount(BigDecimal.valueOf(-1));
        request.setDeductedPoints(-2);

        assertThrows(IllegalArgumentException.class, () -> service.createOffenseRecord(request));
        verify(offenseRecordMapper, never()).insert(any(OffenseRecord.class));
    }

    @Test
    void searchOffenseByNumberShouldUseExactMatchInDatabaseFallback() {
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        OffenseInformationSearchRepository searchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        OffenseRecordService service = new OffenseRecordService(
                offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        when(searchRepository.searchByOffenseNumber("OFF-001", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByOffenseNumber("OFF-001", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<OffenseRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(offenseRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void updateOffenseShouldPreserveEvidenceFieldsWhenDependentsExist() {
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        OffenseInformationSearchRepository searchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        OffenseRecordService service = new OffenseRecordService(
                offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        OffenseRecord existing = new OffenseRecord();
        existing.setOffenseId(11L);
        existing.setProcessStatus(OffenseProcessState.PROCESSED.getCode());
        existing.setDriverId(101L);
        existing.setVehicleId(201L);
        existing.setOffenseLocation("Old Location");
        existing.setOffenseDescription("Old Description");
        existing.setEvidenceType("Photo");
        existing.setEvidenceUrls("[\"old\"]");
        existing.setFineAmount(BigDecimal.valueOf(200));
        existing.setDeductedPoints(6);
        existing.setDetentionDays(3);
        when(offenseRecordMapper.selectById(11L)).thenReturn(existing);
        when(fineRecordMapper.selectCount(any())).thenReturn(1L);
        when(offenseRecordMapper.updateById(any(OffenseRecord.class))).thenReturn(1);

        OffenseRecord request = new OffenseRecord();
        request.setOffenseId(11L);
        request.setProcessStatus(OffenseProcessState.CANCELLED.getCode());
        request.setDriverId(999L);
        request.setVehicleId(888L);
        request.setOffenseLocation("New Location");
        request.setOffenseDescription("New Description");
        request.setEvidenceType("Video");
        request.setEvidenceUrls("[\"new\"]");
        request.setFineAmount(BigDecimal.valueOf(999));
        request.setDeductedPoints(12);
        request.setDetentionDays(9);

        service.updateOffenseRecord(request);

        ArgumentCaptor<OffenseRecord> captor = ArgumentCaptor.forClass(OffenseRecord.class);
        verify(offenseRecordMapper).updateById(captor.capture());
        assertEquals(101L, captor.getValue().getDriverId());
        assertEquals(201L, captor.getValue().getVehicleId());
        assertEquals("Old Location", captor.getValue().getOffenseLocation());
        assertEquals("Old Description", captor.getValue().getOffenseDescription());
        assertEquals("Photo", captor.getValue().getEvidenceType());
        assertEquals("[\"old\"]", captor.getValue().getEvidenceUrls());
        assertEquals(BigDecimal.valueOf(200), captor.getValue().getFineAmount());
        assertEquals(6, captor.getValue().getDeductedPoints());
        assertEquals(3, captor.getValue().getDetentionDays());
        assertEquals(OffenseProcessState.PROCESSED.getCode(), captor.getValue().getProcessStatus());
    }

    @Test
    void checkAndInsertOffenseIdempotencyShouldPopulateRequestHistoryMetadata() {
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        OffenseInformationSearchRepository searchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        OffenseRecordService service = new OffenseRecordService(
                offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("police", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(55L);
        when(sysUserService.findByUsername("police")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/offenses");
        request.addHeader("X-Real-IP", "198.51.100.5");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        OffenseRecord offenseRecord = new OffenseRecord();
        offenseRecord.setDriverId(101L);
        offenseRecord.setVehicleId(201L);
        offenseRecord.setOffenseCode("SPD001");
        offenseRecord.setOffenseLocation("West Road");

        service.checkAndInsertIdempotency("offense-key", offenseRecord, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/offenses", history.getRequestUrl());
        assertEquals("OFFENSE_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals(55L, history.getUserId());
        assertEquals("198.51.100.5", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("driverId=101"));
        assertTrue(history.getRequestParams().contains("vehicleId=201"));
    }

    @Test
    void updateAppealSystemManagedShouldKeepWorkflowManagedFields() {
        TransactionSynchronizationManager.initSynchronization();

        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(20L);
        when(offenseRecordService.findById(20L)).thenReturn(offense);

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(30L);
        existing.setOffenseId(20L);
        existing.setAppealReason("Original appeal reason");
        existing.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        existing.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        existing.setAcceptanceHandler("reviewer-a");
        existing.setProcessHandler("reviewer-b");
        when(appealRecordMapper.selectById(30L)).thenReturn(existing);
        when(appealRecordMapper.selectList(any())).thenReturn(List.of(existing));
        when(appealRecordMapper.updateById(any(AppealRecord.class))).thenReturn(1);

        AppealRecord request = new AppealRecord();
        request.setAppealId(30L);
        request.setOffenseId(20L);
        request.setAcceptanceStatus(AppealAcceptanceState.REJECTED.getCode());
        request.setProcessStatus(AppealProcessState.APPROVED.getCode());

        service.updateAppealSystemManaged(request);

        ArgumentCaptor<AppealRecord> captor = ArgumentCaptor.forClass(AppealRecord.class);
        verify(appealRecordMapper).updateById(captor.capture());
        assertEquals(AppealAcceptanceState.ACCEPTED.getCode(), captor.getValue().getAcceptanceStatus());
        assertEquals(AppealProcessState.UNDER_REVIEW.getCode(), captor.getValue().getProcessStatus());
    }

    @Test
    void updateAppealShouldRejectManualMutation() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        AppealRecord request = new AppealRecord();
        request.setAppealId(30L);

        assertThrows(IllegalStateException.class, () -> service.updateAppeal(request));
        verify(appealRecordMapper, never()).updateById(any(AppealRecord.class));
    }

    @Test
    void updateAppealSupplementFieldsShouldAllowOnlyEditableEvidenceFields() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(30L);
        existing.setOffenseId(20L);
        existing.setAppealReason("Old reason");
        existing.setEvidenceDescription("Old evidence");
        existing.setEvidenceUrls("[\"old\"]");
        existing.setAcceptanceStatus(AppealAcceptanceState.NEED_SUPPLEMENT.getCode());
        existing.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
        when(appealRecordMapper.selectById(30L)).thenReturn(existing);
        when(appealRecordMapper.updateById(any(AppealRecord.class))).thenReturn(1);

        AppealRecord draft = new AppealRecord();
        draft.setAppealReason("Updated reason");
        draft.setEvidenceDescription("Updated evidence");
        draft.setEvidenceUrls("[\"new\"]");
        draft.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        draft.setProcessStatus(AppealProcessState.APPROVED.getCode());

        AppealRecord result = service.updateSupplementFieldsSystemManaged(30L, draft);

        assertEquals("Updated reason", result.getAppealReason());
        assertEquals("Updated evidence", result.getEvidenceDescription());
        assertEquals("[\"new\"]", result.getEvidenceUrls());
        assertEquals(AppealAcceptanceState.NEED_SUPPLEMENT.getCode(), result.getAcceptanceStatus());
        assertEquals(AppealProcessState.UNPROCESSED.getCode(), result.getProcessStatus());
        verify(appealRecordMapper).updateById(existing);
    }

    @Test
    void updateAppealSupplementFieldsShouldRejectNonAwaitingAppeal() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(30L);
        existing.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        when(appealRecordMapper.selectById(30L)).thenReturn(existing);

        AppealRecord draft = new AppealRecord();
        draft.setAppealReason("Updated reason");

        assertThrows(IllegalStateException.class,
                () -> service.updateSupplementFieldsSystemManaged(30L, draft));
        verify(appealRecordMapper, never()).updateById(any(AppealRecord.class));
    }

    @Test
    void searchAppealByAppellantIdCardShouldUseExactMatchInDatabaseFallback() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        when(searchRepository.searchByAppellantIdCard("110101199001010022", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByAppellantIdCard("110101199001010022", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<AppealRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(appealRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void createAppealShouldRejectBlankAppealReason() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(20L);
        when(offenseRecordService.findById(20L)).thenReturn(offense);
        when(appealRecordMapper.selectList(any())).thenReturn(List.of());

        AppealRecord request = new AppealRecord();
        request.setOffenseId(20L);
        request.setAppealReason("   ");

        assertThrows(IllegalArgumentException.class, () -> service.createAppeal(request));
        verify(appealRecordMapper, never()).insert(any(AppealRecord.class));
        verify(stateMachineService, never()).canTransitionOffenseState(any(), any());
    }

    @Test
    void createAppealShouldExplainRejectedAppealMustBeResubmitted() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(20L);
        when(offenseRecordService.findById(20L)).thenReturn(offense);

        AppealRecord rejectedAppeal = new AppealRecord();
        rejectedAppeal.setAppealId(21L);
        rejectedAppeal.setOffenseId(20L);
        rejectedAppeal.setAcceptanceStatus(AppealAcceptanceState.REJECTED.getCode());
        rejectedAppeal.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
        when(appealRecordMapper.selectList(any())).thenReturn(List.of(rejectedAppeal));

        AppealRecord request = new AppealRecord();
        request.setOffenseId(20L);
        request.setAppealReason("Need to explain the earlier evidence");

        IllegalStateException ex = assertThrows(IllegalStateException.class, () -> service.createAppeal(request));
        assertEquals("A rejected appeal already exists for this offense; please resubmit the existing appeal",
                ex.getMessage());
        verify(appealRecordMapper, never()).insert(any(AppealRecord.class));
    }

    @Test
    void searchAppealByNumberShouldUseExactMatchInDatabaseFallback() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        when(searchRepository.searchByAppealNumberPrefix("APL-001", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByAppealNumberPrefix("APL-001", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<AppealRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(appealRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertTrue(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchAppealByNumberFuzzyEndpointShouldUseLikeMatchInDatabaseFallback() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        when(searchRepository.searchByAppealNumberFuzzy("APL-001", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByAppealNumberFuzzy("APL-001", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<AppealRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(appealRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertTrue(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void deleteAppealShouldRejectManualDeletion() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        assertThrows(IllegalStateException.class, () -> service.deleteAppeal(30L));
        verify(appealRecordMapper, never()).deleteById(any());
    }

    @Test
    void checkAndInsertAppealIdempotencyShouldPopulateRequestHistoryMetadata() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(77L);
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/appeals/me");
        request.addHeader("X-Forwarded-For", "203.0.113.77");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setOffenseId(300L);
        appealRecord.setAppellantName("Carol Driver");
        appealRecord.setAppellantIdCard("110101199001010033");
        appealRecord.setAppellantContact("13700000000");

        service.checkAndInsertIdempotency("appeal-key", appealRecord, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/appeals/me", history.getRequestUrl());
        assertEquals("APPEAL_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals(77L, history.getUserId());
        assertEquals("203.0.113.77", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("offenseId=300"));
        assertTrue(history.getRequestParams().contains("appellantName=Carol Driver"));
    }

    @Test
    void transitionPaymentStatusShouldRejectPaidWithoutNetAmount() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord existing = new PaymentRecord();
        existing.setPaymentId(40L);
        existing.setPaymentStatus(PaymentState.UNPAID.getCode());
        existing.setPaymentAmount(BigDecimal.ZERO);
        existing.setRefundAmount(BigDecimal.ZERO);
        when(paymentRecordMapper.selectById(40L)).thenReturn(existing);
        when(stateMachineService.canTransitionPaymentState(any(), any())).thenReturn(true);
        when(stateMachineService.processPaymentState(any(), any(), any())).thenReturn(PaymentState.PAID);

        assertThrows(IllegalStateException.class, () -> service.transitionPaymentStatus(40L, PaymentState.PAID));

        verify(paymentRecordMapper, never()).updateById(any(PaymentRecord.class));
    }

    @Test
    void updatePaymentShouldRejectManualMutation() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord request = new PaymentRecord();
        request.setPaymentId(41L);

        assertThrows(IllegalStateException.class, () -> service.updatePaymentRecord(request));
        verify(paymentRecordMapper, never()).updateById(any(PaymentRecord.class));
    }

    @Test
    void createPaymentShouldRejectBlankPayerIdentity() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(91L);
        when(fineRecordService.findById(91L)).thenReturn(fineRecord);

        PaymentRecord request = new PaymentRecord();
        request.setFineId(91L);
        request.setPaymentAmount(BigDecimal.valueOf(120));
        request.setPayerName(" ");
        request.setPayerIdCard(null);

        assertThrows(IllegalArgumentException.class, () -> service.createPaymentRecord(request));
        verify(paymentRecordMapper, never()).insert(any(PaymentRecord.class));
    }

    @Test
    void searchPaymentByPayerIdCardShouldUseExactMatchInDatabaseFallback() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        when(searchRepository.searchByPayerIdCard("110101199001010091", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByPayerIdCard("110101199001010091", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<PaymentRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(paymentRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchPaymentByFineIdAndPayerIdCardShouldUseExactMatchInDatabaseFallback() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        when(searchRepository.findByFineIdAndPayerIdCard(
                801L,
                "110101199001010091",
                org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.findByFineIdAndPayerIdCard(801L, "110101199001010091", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<PaymentRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(paymentRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
        assertTrue(sqlSegment.contains("fine_id"));
        assertTrue(sqlSegment.contains("payer_id_card"));
    }

    @Test
    void searchPaymentByTransactionIdShouldUseExactMatchInDatabaseFallback() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        when(searchRepository.searchByTransactionId("txn-001", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByTransactionId("txn-001", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<PaymentRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(paymentRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchPaymentByNumberShouldUseExactMatchInDatabaseFallback() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        when(searchRepository.searchByPaymentNumber("PAY-001", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByPaymentNumber("PAY-001", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<PaymentRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(paymentRecordMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchRequestHistoryByIdempotencyKeyShouldUseExactMatchInDatabaseFallback() {
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysRequestHistorySearchRepository searchRepository = Mockito.mock(SysRequestHistorySearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        SysRequestHistoryService service = new SysRequestHistoryService(
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        when(searchRepository.searchByIdempotencyKey("req-001", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByIdempotencyKey("req-001", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<SysRequestHistory>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(requestHistoryMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchRequestHistoryByIpShouldUseExactMatchInDatabaseFallback() {
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysRequestHistorySearchRepository searchRepository = Mockito.mock(SysRequestHistorySearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        SysRequestHistoryService service = new SysRequestHistoryService(
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        when(searchRepository.searchByRequestIp("198.51.100.8", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByRequestIp("198.51.100.8", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<SysRequestHistory>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(requestHistoryMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void deletePaymentShouldRejectManualDeletion() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        assertThrows(IllegalStateException.class, () -> service.deletePaymentRecord(41L));
        verify(paymentRecordMapper, never()).deleteById(any());
    }

    @Test
    void checkAndInsertPaymentIdempotencyShouldPopulateRequestHistoryMetadata() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("finance", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(88L);
        when(sysUserService.findByUsername("finance")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Forwarded-For", "203.0.113.8");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setFineId(91L);
        paymentRecord.setPaymentAmount(BigDecimal.valueOf(120));
        paymentRecord.setPaymentMethod("ALIPAY");
        paymentRecord.setPayerName("Carol Driver");
        paymentRecord.setTransactionId("txn-001");

        service.checkAndInsertIdempotency("payment-key", paymentRecord, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/payments", history.getRequestUrl());
        assertEquals("PAYMENT_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals(88L, history.getUserId());
        assertEquals("203.0.113.8", history.getRequestIp());
        assertNotNull(history.getRequestParams());
        assertTrue(history.getRequestParams().contains("fineId=91"));
        assertTrue(history.getRequestParams().contains("paymentAmount=120"));
    }

    @Test
    void checkAndInsertPaymentConfirmIdempotencyShouldPopulateConfirmHistoryMetadata() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(99L);
        when(sysUserService.findByUsername("driver")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Forwarded-For", "203.0.113.9");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        PaymentRecord confirmationDraft = new PaymentRecord();
        confirmationDraft.setPaymentId(902L);
        confirmationDraft.setTransactionId("WX-20260410-0002");
        confirmationDraft.setReceiptUrl("https://example.com/proof/902");

        service.checkAndInsertIdempotency("payment-confirm-key", confirmationDraft, "confirm");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("/api/payments/me/902/confirm", history.getRequestUrl());
        assertEquals("PAYMENT_CONFIRM", history.getBusinessType());
        assertEquals(902L, history.getBusinessId());
        assertTrue(history.getRequestParams().contains("paymentId=902"));
        assertTrue(history.getRequestParams().contains("transactionId=WX-20260410-0002"));
    }

    @Test
    void checkAndInsertPaymentReviewIdempotencyShouldPopulateReviewHistoryMetadata() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("finance", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(77L);
        when(sysUserService.findByUsername("finance")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Forwarded-For", "203.0.113.10");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        PaymentRecord reviewDraft = new PaymentRecord();
        reviewDraft.setPaymentId(902L);
        reviewDraft.setRemarks("reviewResult=NEED_PROOF,reviewOpinion=Upload receipt");

        service.checkAndInsertIdempotency("payment-review-key", reviewDraft, "review");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("/api/payments/902/finance-review", history.getRequestUrl());
        assertEquals("PAYMENT_REVIEW", history.getBusinessType());
        assertEquals(902L, history.getBusinessId());
        assertEquals(77L, history.getUserId());
        assertEquals("203.0.113.10", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("paymentId=902"));
        assertTrue(history.getRequestParams().contains("remarks=reviewResult=NEED_PROOF"));
    }

    @Test
    void checkAndInsertPaymentProofIdempotencyShouldPopulateProofHistoryMetadata() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(55L);
        when(sysUserService.findByUsername("driver")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Forwarded-For", "203.0.113.11");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        PaymentRecord proofDraft = new PaymentRecord();
        proofDraft.setPaymentId(902L);
        proofDraft.setReceiptUrl("https://example.com/proof/updated-902");

        service.checkAndInsertIdempotency("payment-proof-key", proofDraft, "proof");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("/api/payments/me/902/proof", history.getRequestUrl());
        assertEquals("PAYMENT_PROOF_UPDATE", history.getBusinessType());
        assertEquals(902L, history.getBusinessId());
        assertEquals(55L, history.getUserId());
        assertTrue(history.getRequestParams().contains("paymentId=902"));
        assertTrue(history.getRequestParams().contains("receiptUrl=https://example.com/proof/updated-902"));
    }

    @Test
    void listFinanceReviewTasksShouldReturnOnlyPendingFinanceItems() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord pendingInitialReview = new PaymentRecord();
        pendingInitialReview.setPaymentId(901L);
        pendingInitialReview.setPaymentChannel("APP");
        pendingInitialReview.setPaymentStatus(PaymentState.PAID.getCode());
        pendingInitialReview.setReceiptUrl("https://example.com/proof/901");

        PaymentRecord needProofReview = new PaymentRecord();
        needProofReview.setPaymentId(902L);
        needProofReview.setPaymentChannel("USER_SELF_SERVICE");
        needProofReview.setPaymentStatus(PaymentState.PARTIAL.getCode());
        needProofReview.setRemarks("[FINANCE_REVIEW]|NEED_PROOF|finance|2026-04-10T12:00:00|Upload receipt");

        PaymentRecord approvedReview = new PaymentRecord();
        approvedReview.setPaymentId(903L);
        approvedReview.setPaymentChannel("APP");
        approvedReview.setPaymentStatus(PaymentState.PAID.getCode());
        approvedReview.setRemarks("[FINANCE_REVIEW]|APPROVED|finance|2026-04-10T12:05:00|Verified");

        PaymentRecord nonSelfService = new PaymentRecord();
        nonSelfService.setPaymentId(904L);
        nonSelfService.setPaymentChannel("COUNTER");
        nonSelfService.setPaymentStatus(PaymentState.PAID.getCode());

        Page<PaymentRecord> resultPage = new Page<>(1, 50);
        resultPage.setRecords(List.of(
                pendingInitialReview,
                needProofReview,
                approvedReview,
                nonSelfService));
        when(paymentRecordMapper.selectPage(any(Page.class), any(QueryWrapper.class))).thenReturn(resultPage);
        when(paymentRecordMapper.selectBatchIds(List.of(901L, 902L))).thenReturn(List.of(
                buildFinanceReviewTaskRecord(902L, "USER_SELF_SERVICE", PaymentState.PARTIAL.getCode(), "full-proof-902"),
                buildFinanceReviewTaskRecord(901L, "APP", PaymentState.PAID.getCode(), "full-proof-901")));

        List<PaymentRecord> tasks = service.listFinanceReviewTasks(1, 20);

        assertEquals(2, tasks.size());
        assertEquals(List.of(901L, 902L), tasks.stream().map(PaymentRecord::getPaymentId).toList());
        assertEquals("full-proof-901", tasks.get(0).getReceiptUrl());
        assertEquals("full-proof-902", tasks.get(1).getReceiptUrl());
        assertFalse(tasks.stream().anyMatch(task -> Objects.equals(task.getPaymentId(), 903L)));
        assertFalse(tasks.stream().anyMatch(task -> Objects.equals(task.getPaymentId(), 904L)));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<PaymentRecord>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(paymentRecordMapper).selectPage(any(Page.class), wrapperCaptor.capture());
        assertEquals("payment_id,payment_channel,payment_status,remarks,updated_at,payment_time",
                wrapperCaptor.getValue().getSqlSelect());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertTrue(sqlSegment.contains("remarks"));
        assertTrue(sqlSegment.toUpperCase().contains("NOT LIKE"));
        java.util.Collection<Object> sqlParams = wrapperCaptor.getValue().getParamNameValuePairs().values();
        assertTrue(sqlParams.stream().anyMatch(value ->
                Objects.toString(value, "").contains("[FINANCE_REVIEW]|APPROVED|")));
        assertTrue(sqlParams.stream().anyMatch(value ->
                Objects.toString(value, "").contains("[FINANCE_REVIEW]|NEED_PROOF|")));
        verify(paymentRecordMapper).selectBatchIds(List.of(901L, 902L));
    }

    @Test
    void listCurrentUserProgressShouldIncludePaymentHistoryByFineContext() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(100L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber()).thenReturn("110101199001010100");
        when(sysRequestHistoryService.findByUserId(100L, 1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserVehicleIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(List.of(200L));
        when(sysRequestHistoryService.findRefundAudits(null, 200L, null, 1, 100)).thenReturn(List.of());
        when(paymentRecordService.findIdsByPayerIdCardAndFineIds(eq("110101199001010100"), any()))
                .thenReturn(List.of(300L));

        SysRequestHistory paymentHistory = new SysRequestHistory();
        paymentHistory.setId(2L);
        paymentHistory.setBusinessType("PAYMENT_CREATE");
        paymentHistory.setBusinessId(300L);
        paymentHistory.setUpdatedAt(java.time.LocalDateTime.now());

        ArgumentCaptor<Iterable<Long>> businessIdsCaptor = iterableLongCaptor();
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200)))
                .thenReturn(List.of(paymentHistory));

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        verify(sysRequestHistoryService).findByBusinessIds(businessIdsCaptor.capture(), eq(1), eq(200));
        LinkedHashSet<Long> businessIds = new LinkedHashSet<>();
        businessIdsCaptor.getValue().forEach(businessIds::add);
        assertTrue(businessIds.contains(200L));
        assertTrue(businessIds.contains(300L));
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals(300L, response.getBody().get(0).getBusinessId());
    }

    @Test
    void trafficViolationDetailsShouldSanitizePaymentSensitiveFields() {
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseTypeDictService offenseTypeDictService = Mockito.mock(OffenseTypeDictService.class);

        TrafficViolationController controller = new TrafficViolationController(
                offenseRecordService,
                fineRecordService,
                paymentRecordService,
                deductionRecordService,
                appealRecordService,
                offenseTypeDictService);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(88L);
        when(offenseRecordService.findById(88L)).thenReturn(offense);

        FineRecord fine = new FineRecord();
        fine.setFineId(188L);
        when(fineRecordService.findByOffenseId(88L, 1, 50)).thenReturn(List.of(fine));
        when(deductionRecordService.findByOffenseId(88L, 1, 50)).thenReturn(List.of());
        when(appealRecordService.findByOffenseId(88L, 1, 20)).thenReturn(List.of());

        PaymentRecord payment = new PaymentRecord();
        payment.setPaymentId(288L);
        payment.setFineId(188L);
        payment.setPayerIdCard("110101199001010088");
        payment.setPayerContact("13812345678");
        payment.setBankAccount("6222021234567890");
        payment.setReceiptUrl("https://example.com/receipt/288");
        when(paymentRecordService.findByFineId(188L, 1, 20)).thenReturn(List.of(payment));

        ResponseEntity<Map<String, Object>> response = controller.violationDetails(88L);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        @SuppressWarnings("unchecked")
        List<PaymentRecord> payments = (List<PaymentRecord>) response.getBody().get("payments");
        assertEquals(1, payments.size());
        assertNotEquals("110101199001010088", payments.get(0).getPayerIdCard());
        assertNotEquals("13812345678", payments.get(0).getPayerContact());
        assertNotEquals("6222021234567890", payments.get(0).getBankAccount());
        assertNull(payments.get(0).getReceiptUrl());
    }

    @Test
    void trafficViolationDashboardSummaryShouldReturnRealAggregatedMetrics() {
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseTypeDictService offenseTypeDictService = Mockito.mock(OffenseTypeDictService.class);

        TrafficViolationController controller = new TrafficViolationController(
                offenseRecordService,
                fineRecordService,
                paymentRecordService,
                deductionRecordService,
                appealRecordService,
                offenseTypeDictService);

        LocalDate today = LocalDate.now();
        OffenseRecord firstOffense = new OffenseRecord();
        firstOffense.setOffenseId(1L);
        firstOffense.setOffenseCode("SPD001");
        firstOffense.setOffenseTime(today.minusDays(1).atTime(10, 0));
        firstOffense.setFineAmount(BigDecimal.valueOf(200));
        firstOffense.setDeductedPoints(3);

        OffenseRecord secondOffense = new OffenseRecord();
        secondOffense.setOffenseId(2L);
        secondOffense.setOffenseCode("RED001");
        secondOffense.setOffenseTime(today.minusDays(1).atTime(14, 0));
        secondOffense.setFineAmount(BigDecimal.valueOf(100));
        secondOffense.setDeductedPoints(2);

        when(offenseRecordService.listOffenses(1, 200)).thenReturn(List.of(firstOffense, secondOffense));
        when(offenseRecordService.listOffenses(2, 200)).thenReturn(List.of());

        AppealRecord appeal = new AppealRecord();
        appeal.setAppealId(11L);
        appeal.setOffenseId(1L);
        appeal.setAppealReason("Insufficient evidence");
        when(appealRecordService.findByOffenseIds(List.of(1L, 2L), 1, 200)).thenReturn(List.of(appeal));
        when(appealRecordService.findByOffenseIds(List.of(1L, 2L), 2, 200)).thenReturn(List.of());

        FineRecord fine = new FineRecord();
        fine.setFineId(21L);
        fine.setOffenseId(1L);
        fine.setPaymentStatus("Paid");
        when(fineRecordService.listFines(1, 200)).thenReturn(List.of(fine));
        when(fineRecordService.listFines(2, 200)).thenReturn(List.of());

        OffenseTypeDict speeding = new OffenseTypeDict();
        speeding.setOffenseCode("SPD001");
        speeding.setOffenseName("Speeding");
        OffenseTypeDict redLight = new OffenseTypeDict();
        redLight.setOffenseCode("RED001");
        redLight.setOffenseName("Red-light running");
        when(offenseTypeDictService.findAll(1, 200)).thenReturn(List.of(speeding, redLight));
        when(offenseTypeDictService.findAll(2, 200)).thenReturn(List.of());

        ResponseEntity<Map<String, Object>> response = controller.dashboardSummary();

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());

        @SuppressWarnings("unchecked")
        Map<String, Number> violationTypes =
                (Map<String, Number>) response.getBody().get("violationTypes");
        assertEquals(1L, violationTypes.get("Speeding").longValue());
        assertEquals(1L, violationTypes.get("Red-light running").longValue());

        @SuppressWarnings("unchecked")
        Map<String, Number> appealReasons =
                (Map<String, Number>) response.getBody().get("appealReasons");
        assertEquals(1L, appealReasons.get("Insufficient evidence").longValue());

        @SuppressWarnings("unchecked")
        Map<String, Number> paymentStatus =
                (Map<String, Number>) response.getBody().get("paymentStatus");
        assertEquals(1L, paymentStatus.get("Paid").longValue());

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> timeSeries =
                (List<Map<String, Object>>) response.getBody().get("timeSeries");
        assertEquals(7, timeSeries.size());
        Map<String, Object> yesterdayPoint = timeSeries.stream()
                .filter(point -> LocalDateTime.parse(point.get("time").toString()).toLocalDate()
                        .equals(today.minusDays(1)))
                .findFirst()
                .orElseThrow();
        assertEquals(300.0, ((Number) yesterdayPoint.get("value1")).doubleValue());
        assertEquals(5, ((Number) yesterdayPoint.get("value2")).intValue());
        verify(offenseRecordService, never()).findAll();
        verify(fineRecordService, never()).findAll();
        verify(offenseTypeDictService, never()).findAll();
        verify(appealRecordService, never()).findByOffenseIds(List.of(1L, 2L));
    }

    @Test
    void vehicleSearchByTypeShouldUsePagedServiceSearch() {
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        DriverVehicleService driverVehicleService = Mockito.mock(DriverVehicleService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        VehicleInformationController controller = new VehicleInformationController(
                vehicleInformationService,
                driverVehicleService,
                currentUserTrafficSupportService);

        VehicleInformation vehicle = new VehicleInformation();
        vehicle.setVehicleId(701L);
        vehicle.setVehicleType("SUV");
        when(vehicleInformationService.searchByVehicleType("SUV", 2, 25)).thenReturn(List.of(vehicle));

        ResponseEntity<List<VehicleInformation>> response = controller.searchByType("SUV", 2, 25);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals(701L, response.getBody().get(0).getVehicleId());
        verify(vehicleInformationService).searchByVehicleType("SUV", 2, 25);
        verify(vehicleInformationService, never()).getVehicleInformationByType(any());
    }

    @Test
    void listCurrentUserVehiclesShouldUsePagedCurrentUserServiceSearch() {
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        DriverVehicleService driverVehicleService = Mockito.mock(DriverVehicleService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        VehicleInformationController controller = new VehicleInformationController(
                vehicleInformationService,
                driverVehicleService,
                currentUserTrafficSupportService);

        VehicleInformation vehicle = new VehicleInformation();
        vehicle.setVehicleId(702L);
        when(currentUserTrafficSupportService.listCurrentUserVehicles(3, 40)).thenReturn(List.of(vehicle));

        ResponseEntity<List<VehicleInformation>> response = controller.listCurrentUserVehicles(3, 40);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals(702L, response.getBody().get(0).getVehicleId());
        verify(currentUserTrafficSupportService).listCurrentUserVehicles(3, 40);
    }

    @Test
    void offenseDetailsViewShouldSanitizePaymentSensitiveFields() {
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);

        OffenseDetailsController controller = new OffenseDetailsController(
                offenseRecordService,
                fineRecordService,
                paymentRecordService,
                deductionRecordService,
                appealRecordService);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(89L);
        when(offenseRecordService.findById(89L)).thenReturn(offense);

        FineRecord fine = new FineRecord();
        fine.setFineId(189L);
        when(fineRecordService.findByOffenseId(89L, 1, 20)).thenReturn(List.of(fine));
        when(deductionRecordService.findByOffenseId(89L, 1, 20)).thenReturn(List.of());
        when(appealRecordService.findByOffenseId(89L, 1, 20)).thenReturn(List.of());

        PaymentRecord payment = new PaymentRecord();
        payment.setPaymentId(289L);
        payment.setFineId(189L);
        payment.setPayerIdCard("110101199001010089");
        payment.setPayerContact("13912345678");
        payment.setBankAccount("622202999988887777");
        payment.setReceiptUrl("https://example.com/receipt/289");
        when(paymentRecordService.findByFineId(189L, 1, 10)).thenReturn(List.of(payment));

        ResponseEntity<Map<String, Object>> response = controller.getDetails(89L);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        @SuppressWarnings("unchecked")
        List<PaymentRecord> payments = (List<PaymentRecord>) response.getBody().get("payments");
        assertEquals(1, payments.size());
        assertNotEquals("110101199001010089", payments.get(0).getPayerIdCard());
        assertNotEquals("13912345678", payments.get(0).getPayerContact());
        assertNotEquals("622202999988887777", payments.get(0).getBankAccount());
        assertNull(payments.get(0).getReceiptUrl());
    }

    @Test
    void listCurrentUserProgressShouldIncludeDeductionHistoryByDriverContext() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(101L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber()).thenReturn("110101199001010101");
        when(sysRequestHistoryService.findByUserId(101L, 1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserVehicleIds()).thenReturn(List.of());
        when(paymentRecordService.findIdsByPayerIdCardAndFineIds(eq("110101199001010101"), any())).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of(400L));

        SysRequestHistory deductionHistory = new SysRequestHistory();
        deductionHistory.setId(3L);
        deductionHistory.setBusinessType("DEDUCTION_CREATE");
        deductionHistory.setBusinessId(400L);
        deductionHistory.setUpdatedAt(java.time.LocalDateTime.now());

        ArgumentCaptor<Iterable<Long>> businessIdsCaptor = iterableLongCaptor();
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200)))
                .thenReturn(List.of(deductionHistory));

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        verify(sysRequestHistoryService).findByBusinessIds(businessIdsCaptor.capture(), eq(1), eq(200));
        LinkedHashSet<Long> businessIds = new LinkedHashSet<>();
        businessIdsCaptor.getValue().forEach(businessIds::add);
        assertTrue(businessIds.contains(400L));
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals(400L, response.getBody().get(0).getBusinessId());
    }

    @Test
    void listCurrentUserProgressShouldIncludeRefundAuditByFineContextEvenWithoutBusinessId() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(103L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber()).thenReturn("110101199001010103");
        when(sysRequestHistoryService.findByUserId(103L, 1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserVehicleIds()).thenReturn(List.of());
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200))).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(List.of(201L));
        when(paymentRecordService.findIdsByPayerIdCardAndFineIds(eq("110101199001010103"), any())).thenReturn(List.of());

        SysRequestHistory refundAudit = new SysRequestHistory();
        refundAudit.setId(6L);
        refundAudit.setBusinessType("PARTIAL_REFUND_FAILED");
        refundAudit.setBusinessId(null);
        refundAudit.setUpdatedAt(java.time.LocalDateTime.now());
        when(sysRequestHistoryService.findRefundAudits(null, 201L, null, 1, 100))
                .thenReturn(List.of(refundAudit));

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        verify(sysRequestHistoryService).findRefundAudits(null, 201L, null, 1, 100);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals(6L, response.getBody().get(0).getId());
        assertEquals("PARTIAL_REFUND_FAILED", response.getBody().get(0).getBusinessType());
    }

    @Test
    void listCurrentUserProgressShouldExcludeOverlappingBusinessIdsFromOtherTypes() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(102L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber()).thenReturn("110101199001010102");
        when(sysRequestHistoryService.findByUserId(102L, 1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserVehicleIds()).thenReturn(List.of());
        when(paymentRecordService.findByFineId(500L, 1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(List.of(500L));
        when(paymentRecordService.findIdsByPayerIdCardAndFineIds(eq("110101199001010102"), any())).thenReturn(List.of());
        when(sysRequestHistoryService.findRefundAudits(null, 500L, null, 1, 100)).thenReturn(List.of());

        SysRequestHistory fineHistory = new SysRequestHistory();
        fineHistory.setId(4L);
        fineHistory.setBusinessType("FINE_CREATE");
        fineHistory.setBusinessId(500L);
        fineHistory.setUpdatedAt(java.time.LocalDateTime.now());

        SysRequestHistory leakedOffenseHistory = new SysRequestHistory();
        leakedOffenseHistory.setId(5L);
        leakedOffenseHistory.setBusinessType("OFFENSE_CREATE");
        leakedOffenseHistory.setBusinessId(500L);
        leakedOffenseHistory.setUpdatedAt(java.time.LocalDateTime.now().minusMinutes(1));

        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200)))
                .thenReturn(List.of(fineHistory, leakedOffenseHistory));

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals(4L, response.getBody().get(0).getId());
        assertEquals("FINE_CREATE", response.getBody().get(0).getBusinessType());
    }

    @Test
    void listCurrentUserProgressShouldExcludePaymentHistoryFromOtherPayersOnSameFine() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(104L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber()).thenReturn("110101199001010104");
        when(sysRequestHistoryService.findByUserId(104L, 1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserVehicleIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(List.of(202L));
        when(paymentRecordService.findIdsByPayerIdCardAndFineIds(eq("110101199001010104"), any()))
                .thenReturn(List.of());

        SysRequestHistory leakedPaymentHistory = new SysRequestHistory();
        leakedPaymentHistory.setId(7L);
        leakedPaymentHistory.setBusinessType("PAYMENT_CREATE");
        leakedPaymentHistory.setBusinessId(302L);
        leakedPaymentHistory.setUpdatedAt(java.time.LocalDateTime.now());
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200)))
                .thenReturn(List.of(leakedPaymentHistory));
        when(sysRequestHistoryService.findRefundAudits(null, 202L, null, 1, 100)).thenReturn(List.of());

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertTrue(response.getBody().isEmpty());
    }

    @Test
    void syncPointsFromDeductionRecordsShouldRefreshDriverSummary() {
        TransactionSynchronizationManager.initSynchronization();

        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(50L);
        when(driverInformationMapper.selectById(50L)).thenReturn(driver);

        when(deductionRecordMapper.selectObjs(any())).thenReturn(java.util.Arrays.asList(5, 0, null));

        service.syncPointsFromDeductionRecords(50L);

        ArgumentCaptor<DriverInformation> captor = ArgumentCaptor.forClass(DriverInformation.class);
        verify(driverInformationMapper).updateById(captor.capture());
        assertEquals(5, captor.getValue().getTotalDeductedPoints());
        assertEquals(7, captor.getValue().getCurrentPoints());
    }

    @Test
    void createDriverShouldResetDerivedPointSummary() {
        TransactionSynchronizationManager.initSynchronization();

        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        DriverInformation request = new DriverInformation();
        request.setDriverId(51L);
        request.setIdCardNumber("110101199001010051");
        request.setDriverLicenseNumber("DL-000051");
        request.setCurrentPoints(1);
        request.setTotalDeductedPoints(11);

        service.createDriver(request);

        ArgumentCaptor<DriverInformation> captor = ArgumentCaptor.forClass(DriverInformation.class);
        verify(driverInformationMapper).insert(captor.capture());
        assertEquals(0, captor.getValue().getTotalDeductedPoints());
        assertEquals(12, captor.getValue().getCurrentPoints());
    }

    @Test
    void updateDriverShouldRecomputeDerivedPointSummary() {
        TransactionSynchronizationManager.initSynchronization();

        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        DriverInformation existing = new DriverInformation();
        existing.setDriverId(52L);
        existing.setIdCardNumber("110101199001010052");
        existing.setDriverLicenseNumber("DL-000052");
        when(driverInformationMapper.selectById(52L)).thenReturn(existing);
        when(driverInformationMapper.updateById(any(DriverInformation.class))).thenReturn(1);

        when(deductionRecordMapper.selectObjs(any())).thenReturn(java.util.Arrays.asList(5, 0));

        DriverInformation request = new DriverInformation();
        request.setDriverId(52L);
        request.setIdCardNumber("110101199001010052");
        request.setDriverLicenseNumber("DL-000052");
        request.setCurrentPoints(2);
        request.setTotalDeductedPoints(99);

        service.updateDriver(request);

        ArgumentCaptor<DriverInformation> captor = ArgumentCaptor.forClass(DriverInformation.class);
        verify(driverInformationMapper).updateById(captor.capture());
        assertEquals(5, captor.getValue().getTotalDeductedPoints());
        assertEquals(7, captor.getValue().getCurrentPoints());
    }

    @Test
    void checkAndInsertDriverIdempotencyShouldPopulateRequestHistoryMetadata() {
        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/drivers");
        request.addHeader("X-Real-IP", "198.51.100.61");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        DriverInformation driver = new DriverInformation();
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        driver.setDriverLicenseNumber("DL-000033");

        service.checkAndInsertIdempotency("driver-key", driver, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/drivers", history.getRequestUrl());
        assertEquals("DRIVER_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals("198.51.100.61", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("name=Carol Driver"));
        assertTrue(history.getRequestParams().contains("driverLicenseNumber=DL-000033"));
    }

    @Test
    void searchDriverByIdCardShouldUseExactMatchWithoutFuzzyFallback() {
        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        when(searchRepository.searchByIdCardNumber("110101199001010033", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByIdCardNumber("110101199001010033", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<DriverInformation>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(driverInformationMapper).selectPage(any(), wrapperCaptor.capture());
        verify(searchRepository, never()).searchByIdCardNumberFuzzy(any(), any());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchDriverByLicenseShouldUseExactMatchWithoutFuzzyFallback() {
        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        when(searchRepository.searchByDriverLicenseNumber("DL-000033", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByDriverLicenseNumber("DL-000033", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<DriverInformation>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(driverInformationMapper).selectPage(any(), wrapperCaptor.capture());
        verify(searchRepository, never()).searchByDriverLicenseNumberFuzzy(any(), any());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchDriversShouldCapCandidateFetchSizeForDeepPages() {
        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        when(searchRepository.searchByContactNumber("alice", org.springframework.data.domain.PageRequest.of(0, 500)))
                .thenReturn(null);
        when(searchRepository.searchByIdCardNumber("alice", org.springframework.data.domain.PageRequest.of(0, 500)))
                .thenReturn(null);
        when(searchRepository.searchByDriverLicenseNumber("alice", org.springframework.data.domain.PageRequest.of(0, 500)))
                .thenReturn(null);
        when(searchRepository.searchByNamePrefix("alice", org.springframework.data.domain.PageRequest.of(0, 500)))
                .thenReturn(null);
        when(searchRepository.searchByNameFuzzy("alice", org.springframework.data.domain.PageRequest.of(0, 500)))
                .thenReturn(null);

        when(driverInformationMapper.selectPage(any(), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<DriverInformation> page = invocation.getArgument(0);
            page.setRecords(List.of());
            return page;
        });

        service.searchDrivers("alice", 100, 20);

        verify(searchRepository).searchByContactNumber("alice", org.springframework.data.domain.PageRequest.of(0, 500));
        verify(searchRepository).searchByIdCardNumber("alice", org.springframework.data.domain.PageRequest.of(0, 500));
        verify(searchRepository).searchByDriverLicenseNumber("alice", org.springframework.data.domain.PageRequest.of(0, 500));
        verify(searchRepository).searchByNamePrefix("alice", org.springframework.data.domain.PageRequest.of(0, 500));
    }

    @Test
    void loginLogCrudShouldRejectManualMutation() {
        AuditLoginLogMapper auditLoginLogMapper = Mockito.mock(AuditLoginLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditLoginLogSearchRepository searchRepository = Mockito.mock(AuditLoginLogSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AuditLoginLogService service = new AuditLoginLogService(
                auditLoginLogMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        AuditLoginLog request = new AuditLoginLog();
        request.setLogId(601L);

        assertThrows(IllegalStateException.class, () -> service.createAuditLoginLog(request));
        assertThrows(IllegalStateException.class, () -> service.updateAuditLoginLog(request));
        assertThrows(IllegalStateException.class, () -> service.deleteAuditLoginLog(601L));
        verify(auditLoginLogMapper, never()).insert(any(AuditLoginLog.class));
        verify(auditLoginLogMapper, never()).updateById(any(AuditLoginLog.class));
        verify(auditLoginLogMapper, never()).deleteById(any());
    }

    @Test
    void loginLogSystemManagedCreateAndUpdateShouldPersist() {
        TransactionSynchronizationManager.initSynchronization();

        AuditLoginLogMapper auditLoginLogMapper = Mockito.mock(AuditLoginLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditLoginLogSearchRepository searchRepository = Mockito.mock(AuditLoginLogSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AuditLoginLogService service = new AuditLoginLogService(
                auditLoginLogMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        AuditLoginLog createRequest = new AuditLoginLog();
        createRequest.setUsername("alice");

        service.createAuditLoginLogSystemManaged(createRequest);
        verify(auditLoginLogMapper).insert(any(AuditLoginLog.class));

        AuditLoginLog updateRequest = new AuditLoginLog();
        updateRequest.setLogId(602L);
        updateRequest.setUsername("alice");
        when(auditLoginLogMapper.updateById(any(AuditLoginLog.class))).thenReturn(1);

        service.updateAuditLoginLogSystemManaged(updateRequest);
        verify(auditLoginLogMapper).updateById(any(AuditLoginLog.class));
    }

    @Test
    void checkAndInsertAuditLoginLogIdempotencyShouldPopulateHistoryWithoutPrematureSuccess() {
        AuditLoginLogMapper auditLoginLogMapper = Mockito.mock(AuditLoginLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditLoginLogSearchRepository searchRepository = Mockito.mock(AuditLoginLogSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AuditLoginLogService service = new AuditLoginLogService(
                auditLoginLogMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        AuditLoginLog request = new AuditLoginLog();
        request.setUsername("alice");
        request.setLoginIp("203.0.113.21");
        request.setLoginResult("SUCCESS");
        request.setDeviceType("WEB");

        service.checkAndInsertIdempotency("login-key", request, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        verify(requestHistoryMapper, never()).updateById(any(SysRequestHistory.class));
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/audit/login-logs", history.getRequestUrl());
        assertEquals("AUDIT_LOGIN_LOG_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertTrue(history.getRequestParams().contains("username=alice"));
        assertTrue(history.getRequestParams().contains("loginIp=203.0.113.21"));
    }

    @Test
    void searchLoginLogByIpShouldUseExactMatchInDatabaseFallback() {
        AuditLoginLogMapper auditLoginLogMapper = Mockito.mock(AuditLoginLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditLoginLogSearchRepository searchRepository = Mockito.mock(AuditLoginLogSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AuditLoginLogService service = new AuditLoginLogService(
                auditLoginLogMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        when(searchRepository.searchByLoginIp("203.0.113.21", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByLoginIp("203.0.113.21", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<AuditLoginLog>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(auditLoginLogMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchLoginLogByResultShouldUseExactQueryInDatabaseFallback() {
        AuditLoginLogMapper auditLoginLogMapper = Mockito.mock(AuditLoginLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditLoginLogSearchRepository searchRepository = Mockito.mock(AuditLoginLogSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AuditLoginLogService service = new AuditLoginLogService(
                auditLoginLogMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        when(searchRepository.searchByLoginResult("SUCCESS", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByLoginResult("SUCCESS", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<AuditLoginLog>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(auditLoginLogMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void checkAndInsertSysUserIdempotencyShouldPopulateHistoryWithoutPrematureSuccess() {
        SysUserMapper sysUserMapper = Mockito.mock(SysUserMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysUserSearchRepository searchRepository = Mockito.mock(SysUserSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PasswordEncoder passwordEncoder = Mockito.mock(PasswordEncoder.class);
        CacheManager cacheManager = Mockito.mock(CacheManager.class);

        SysUserService service = new SysUserService(
                sysUserMapper,
                requestHistoryMapper,
                searchRepository,
                passwordEncoder,
                cacheManager);

        SysUser request = new SysUser();
        request.setUsername("alice");
        request.setRealName("Alice Admin");
        request.setDepartment("Operations");
        request.setEmployeeNumber("EMP-1");
        request.setStatus("Active");

        service.checkAndInsertIdempotency("user-key", request, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        verify(requestHistoryMapper, never()).updateById(any(SysRequestHistory.class));
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/sys/users", history.getRequestUrl());
        assertEquals("SYS_USER_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertTrue(history.getRequestParams().contains("username=alice"));
        assertTrue(history.getRequestParams().contains("department=Operations"));
    }

    @Test
    void markHistoryFailureForSysUserShouldAppendFailureReason() {
        SysUserMapper sysUserMapper = Mockito.mock(SysUserMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysUserSearchRepository searchRepository = Mockito.mock(SysUserSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PasswordEncoder passwordEncoder = Mockito.mock(PasswordEncoder.class);
        CacheManager cacheManager = Mockito.mock(CacheManager.class);

        SysUserService service = new SysUserService(
                sysUserMapper,
                requestHistoryMapper,
                searchRepository,
                passwordEncoder,
                cacheManager);

        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey("user-key");
        history.setRequestParams("username=alice,status=Active");
        when(requestHistoryMapper.selectByIdempotencyKey("user-key")).thenReturn(history);

        service.markHistoryFailure("user-key", "duplicate email");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).updateById(captor.capture());
        SysRequestHistory updated = captor.getValue();
        assertEquals("FAILED", updated.getBusinessStatus());
        assertTrue(updated.getRequestParams().contains("username=alice"));
        assertTrue(updated.getRequestParams().contains("failure=duplicate email"));
    }

    @Test
    void searchSysUserByIdCardShouldUseExactMatchInDatabaseFallback() {
        SysUserMapper sysUserMapper = Mockito.mock(SysUserMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysUserSearchRepository searchRepository = Mockito.mock(SysUserSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PasswordEncoder passwordEncoder = Mockito.mock(PasswordEncoder.class);
        CacheManager cacheManager = Mockito.mock(CacheManager.class);

        SysUserService service = new SysUserService(
                sysUserMapper,
                requestHistoryMapper,
                searchRepository,
                passwordEncoder,
                cacheManager);

        when(searchRepository.searchByIdCardNumber("110101199001010011", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByIdCardNumber("110101199001010011", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<SysUser>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(sysUserMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchSysUserByContactShouldUsePrefixMatchInDatabaseFallback() {
        SysUserMapper sysUserMapper = Mockito.mock(SysUserMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysUserSearchRepository searchRepository = Mockito.mock(SysUserSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PasswordEncoder passwordEncoder = Mockito.mock(PasswordEncoder.class);
        CacheManager cacheManager = Mockito.mock(CacheManager.class);

        SysUserService service = new SysUserService(
                sysUserMapper,
                requestHistoryMapper,
                searchRepository,
                passwordEncoder,
                cacheManager);

        when(searchRepository.searchByContactNumber("13800138000", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByContactNumber("13800138000", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<SysUser>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(sysUserMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertTrue(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void searchSysUserByEmployeeNumberShouldUseExactMatchInDatabaseFallback() {
        SysUserMapper sysUserMapper = Mockito.mock(SysUserMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysUserSearchRepository searchRepository = Mockito.mock(SysUserSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PasswordEncoder passwordEncoder = Mockito.mock(PasswordEncoder.class);
        CacheManager cacheManager = Mockito.mock(CacheManager.class);

        SysUserService service = new SysUserService(
                sysUserMapper,
                requestHistoryMapper,
                searchRepository,
                passwordEncoder,
                cacheManager);

        when(searchRepository.searchByEmployeeNumber("EMP-001", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByEmployeeNumber("EMP-001", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<SysUser>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(sysUserMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void beginPasswordChangeShouldReturnAlreadySucceededForMatchingFingerprint() {
        SysUserMapper sysUserMapper = Mockito.mock(SysUserMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysUserSearchRepository searchRepository = Mockito.mock(SysUserSearchRepository.class);
        PasswordEncoder passwordEncoder = Mockito.mock(PasswordEncoder.class);
        CacheManager cacheManager = Mockito.mock(CacheManager.class);

        SysUserService service = new SysUserService(
                sysUserMapper,
                requestHistoryMapper,
                searchRepository,
                passwordEncoder,
                cacheManager);

        SysRequestHistory history = new SysRequestHistory();
        history.setIdempotencyKey("pwd-key");
        history.setBusinessType("SYS_USER_PASSWORD_UPDATE");
        history.setBusinessStatus("SUCCESS");
        history.setUserId(88L);
        history.setBusinessId(88L);
        history.setRequestParams("userId=88,operation=PASSWORD_CHANGE,fingerprint=abc123");
        when(requestHistoryMapper.selectByIdempotencyKey("pwd-key")).thenReturn(history);

        SysUserService.PasswordChangeIdempotencyStatus status =
                service.beginPasswordChange("pwd-key", 88L, "abc123");

        assertEquals(SysUserService.PasswordChangeIdempotencyStatus.ALREADY_SUCCEEDED, status);
        verify(requestHistoryMapper, never()).insert(any(SysRequestHistory.class));
        verify(requestHistoryMapper, never()).updateById(any(SysRequestHistory.class));
    }

    @Test
    void operationLogCrudShouldRejectManualMutation() {
        AuditOperationLogMapper auditOperationLogMapper = Mockito.mock(AuditOperationLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditOperationLogSearchRepository searchRepository = Mockito.mock(AuditOperationLogSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AuditOperationLogService service = new AuditOperationLogService(
                auditOperationLogMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        AuditOperationLog request = new AuditOperationLog();
        request.setLogId(701L);

        assertThrows(IllegalStateException.class, () -> service.createAuditOperationLog(request));
        assertThrows(IllegalStateException.class, () -> service.updateAuditOperationLog(request));
        assertThrows(IllegalStateException.class, () -> service.deleteAuditOperationLog(701L));
        verify(auditOperationLogMapper, never()).insert(any(AuditOperationLog.class));
        verify(auditOperationLogMapper, never()).updateById(any(AuditOperationLog.class));
        verify(auditOperationLogMapper, never()).deleteById(any());
    }

    @Test
    void operationLogSystemManagedCreateAndUpdateShouldPersist() {
        TransactionSynchronizationManager.initSynchronization();

        AuditOperationLogMapper auditOperationLogMapper = Mockito.mock(AuditOperationLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditOperationLogSearchRepository searchRepository = Mockito.mock(AuditOperationLogSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AuditOperationLogService service = new AuditOperationLogService(
                auditOperationLogMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        AuditOperationLog createRequest = new AuditOperationLog();
        createRequest.setOperationContent("system event");

        service.createAuditOperationLogSystemManaged(createRequest);
        verify(auditOperationLogMapper).insert(any(AuditOperationLog.class));

        AuditOperationLog updateRequest = new AuditOperationLog();
        updateRequest.setLogId(702L);
        updateRequest.setOperationContent("system event updated");
        when(auditOperationLogMapper.updateById(any(AuditOperationLog.class))).thenReturn(1);

        service.updateAuditOperationLogSystemManaged(updateRequest);
        verify(auditOperationLogMapper).updateById(any(AuditOperationLog.class));
    }

    @Test
    void updateFineSystemManagedShouldPersistManagedSummary() {
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        FineRecordSearchRepository searchRepository = Mockito.mock(FineRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        FineRecordService service = new FineRecordService(
                fineRecordMapper,
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        when(offenseRecordService.existsById(70L)).thenReturn(true);

        FineRecord existing = new FineRecord();
        existing.setFineId(60L);
        existing.setOffenseId(70L);
        existing.setFineAmount(BigDecimal.valueOf(100));
        existing.setLateFee(BigDecimal.ZERO);
        existing.setTotalAmount(BigDecimal.valueOf(100));
        existing.setPaidAmount(BigDecimal.valueOf(30));
        existing.setUnpaidAmount(BigDecimal.valueOf(70));
        existing.setPaymentStatus(PaymentState.PARTIAL.getCode());
        when(fineRecordMapper.selectById(60L)).thenReturn(existing);
        when(fineRecordMapper.selectCount(any())).thenReturn(0L);
        when(fineRecordMapper.updateById(any(FineRecord.class))).thenReturn(1);

        FineRecord request = new FineRecord();
        request.setFineId(60L);
        request.setOffenseId(70L);
        request.setFineAmount(BigDecimal.valueOf(120));
        request.setLateFee(BigDecimal.TEN);
        request.setPaidAmount(BigDecimal.valueOf(30));
        request.setUnpaidAmount(BigDecimal.valueOf(100));
        request.setPaymentStatus(PaymentState.PARTIAL.getCode());

        service.updateFineRecordSystemManaged(request);

        ArgumentCaptor<FineRecord> captor = ArgumentCaptor.forClass(FineRecord.class);
        verify(fineRecordMapper).updateById(captor.capture());
        verify(offenseRecordService).existsById(70L);
        verify(offenseRecordService, never()).findById(any());
        assertEquals(BigDecimal.valueOf(130), captor.getValue().getTotalAmount());
        assertEquals(BigDecimal.valueOf(30), captor.getValue().getPaidAmount());
        assertEquals(BigDecimal.valueOf(100), captor.getValue().getUnpaidAmount());
        assertEquals(PaymentState.PARTIAL.getCode(), captor.getValue().getPaymentStatus());
    }

    @Test
    void updateFineShouldRejectManualMutation() {
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        FineRecordSearchRepository searchRepository = Mockito.mock(FineRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        FineRecordService service = new FineRecordService(
                fineRecordMapper,
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        FineRecord request = new FineRecord();
        request.setFineId(60L);

        assertThrows(IllegalStateException.class, () -> service.updateFineRecord(request));
        verify(fineRecordMapper, never()).updateById(any(FineRecord.class));
    }

    @Test
    void deleteFineShouldRejectManualDeletion() {
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        FineRecordSearchRepository searchRepository = Mockito.mock(FineRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        FineRecordService service = new FineRecordService(
                fineRecordMapper,
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        assertThrows(IllegalStateException.class, () -> service.deleteFineRecord(60L));
        verify(fineRecordMapper, never()).deleteById(any());
    }

    @Test
    void createFineShouldRejectDuplicateOffenseBinding() {
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        FineRecordSearchRepository searchRepository = Mockito.mock(FineRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        FineRecordService service = new FineRecordService(
                fineRecordMapper,
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        when(offenseRecordService.existsById(80L)).thenReturn(true);

        FineRecord duplicate = new FineRecord();
        duplicate.setFineId(801L);
        duplicate.setOffenseId(80L);
        when(fineRecordMapper.selectCount(any())).thenReturn(1L);

        FineRecord request = new FineRecord();
        request.setOffenseId(80L);
        request.setFineAmount(BigDecimal.valueOf(200));

        assertThrows(IllegalStateException.class, () -> service.createFineRecord(request));
        verify(offenseRecordService).existsById(80L);
        verify(offenseRecordService, never()).findById(any());
        verify(fineRecordMapper, never()).insert(any(FineRecord.class));
    }

    @Test
    void createFineShouldRejectMissingOffenseViaExistenceCheck() {
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        FineRecordSearchRepository searchRepository = Mockito.mock(FineRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        FineRecordService service = new FineRecordService(
                fineRecordMapper,
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        when(offenseRecordService.existsById(81L)).thenReturn(false);

        FineRecord request = new FineRecord();
        request.setOffenseId(81L);
        request.setFineAmount(BigDecimal.valueOf(200));

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () -> service.createFineRecord(request));

        assertEquals("Offense record does not exist", ex.getMessage());
        verify(offenseRecordService).existsById(81L);
        verify(offenseRecordService, never()).findById(any());
        verify(fineRecordMapper, never()).insert(any(FineRecord.class));
    }

    @Test
    void checkAndInsertFineIdempotencyShouldPopulateRequestHistoryMetadata() {
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        FineRecordSearchRepository searchRepository = Mockito.mock(FineRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        FineRecordService service = new FineRecordService(
                fineRecordMapper,
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("police", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(66L);
        when(sysUserService.findByUsername("police")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Real-IP", "198.51.100.12");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        FineRecord fineRecord = new FineRecord();
        fineRecord.setOffenseId(80L);
        fineRecord.setFineAmount(BigDecimal.valueOf(200));
        fineRecord.setLateFee(BigDecimal.TEN);
        fineRecord.setHandler("Officer Li");

        service.checkAndInsertIdempotency("fine-key", fineRecord, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/fines", history.getRequestUrl());
        assertEquals("FINE_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals(66L, history.getUserId());
        assertEquals("198.51.100.12", history.getRequestIp());
        assertNotNull(history.getRequestParams());
        assertTrue(history.getRequestParams().contains("offenseId=80"));
        assertTrue(history.getRequestParams().contains("fineAmount=200"));
    }

    @Test
    void updateDeductionSystemManagedShouldSyncDriverPoints() {
        TransactionSynchronizationManager.initSynchronization();

        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DeductionRecordSearchRepository searchRepository = Mockito.mock(DeductionRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, DeductionRecord> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DeductionRecordService service = new DeductionRecordService(
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                driverInformationService,
                sysUserService,
                kafkaTemplate);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(90L);
        offense.setDriverId(91L);
        when(offenseRecordService.findById(90L)).thenReturn(offense);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(91L);
        when(driverInformationService.getDriverById(91L)).thenReturn(driver);

        DeductionRecord existing = new DeductionRecord();
        existing.setDeductionId(902L);
        existing.setOffenseId(90L);
        existing.setDriverId(91L);
        existing.setDeductedPoints(3);
        when(deductionRecordMapper.selectById(902L)).thenReturn(existing);
        when(deductionRecordMapper.selectCount(any())).thenReturn(0L);
        when(deductionRecordMapper.updateById(any(DeductionRecord.class))).thenReturn(1);

        DeductionRecord request = new DeductionRecord();
        request.setDeductionId(902L);
        request.setOffenseId(90L);
        request.setDriverId(91L);
        request.setDeductedPoints(2);
        request.setStatus("Effective");

        service.updateDeductionRecordSystemManaged(request);

        verify(deductionRecordMapper).updateById(any(DeductionRecord.class));
        verify(driverInformationService).syncPointsFromDeductionRecords(91L);
    }

    @Test
    void updateDeductionShouldRejectManualMutation() {
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DeductionRecordSearchRepository searchRepository = Mockito.mock(DeductionRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, DeductionRecord> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DeductionRecordService service = new DeductionRecordService(
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                driverInformationService,
                sysUserService,
                kafkaTemplate);

        DeductionRecord request = new DeductionRecord();
        request.setDeductionId(902L);

        assertThrows(IllegalStateException.class, () -> service.updateDeductionRecord(request));
        verify(deductionRecordMapper, never()).updateById(any(DeductionRecord.class));
    }

    @Test
    void deleteDeductionShouldRejectManualDeletion() {
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DeductionRecordSearchRepository searchRepository = Mockito.mock(DeductionRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, DeductionRecord> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DeductionRecordService service = new DeductionRecordService(
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                driverInformationService,
                sysUserService,
                kafkaTemplate);

        assertThrows(IllegalStateException.class, () -> service.deleteDeductionRecord(902L));
        verify(deductionRecordMapper, never()).deleteById(any());
    }

    @Test
    void createDeductionShouldRejectDuplicateOffenseBinding() {
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DeductionRecordSearchRepository searchRepository = Mockito.mock(DeductionRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, DeductionRecord> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DeductionRecordService service = new DeductionRecordService(
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                driverInformationService,
                sysUserService,
                kafkaTemplate);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(90L);
        offense.setDriverId(91L);
        when(offenseRecordService.findById(90L)).thenReturn(offense);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(91L);
        when(driverInformationService.getDriverById(91L)).thenReturn(driver);

        when(deductionRecordMapper.selectCount(any())).thenReturn(1L);

        DeductionRecord request = new DeductionRecord();
        request.setOffenseId(90L);
        request.setDriverId(91L);
        request.setDeductedPoints(3);

        assertThrows(IllegalStateException.class, () -> service.createDeductionRecord(request));
        verify(deductionRecordMapper, never()).insert(any(DeductionRecord.class));
    }

    @Test
    void checkAndInsertDeductionIdempotencyShouldPopulateRequestHistoryMetadata() {
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DeductionRecordSearchRepository searchRepository = Mockito.mock(DeductionRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, DeductionRecord> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DeductionRecordService service = new DeductionRecordService(
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                driverInformationService,
                sysUserService,
                kafkaTemplate);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("police", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(44L);
        when(sysUserService.findByUsername("police")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/deductions");
        request.addHeader("X-Real-IP", "198.51.100.44");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        DeductionRecord deductionRecord = new DeductionRecord();
        deductionRecord.setOffenseId(90L);
        deductionRecord.setDriverId(91L);
        deductionRecord.setDeductedPoints(6);

        service.checkAndInsertIdempotency("deduction-key", deductionRecord, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/deductions", history.getRequestUrl());
        assertEquals("DEDUCTION_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals(44L, history.getUserId());
        assertEquals("198.51.100.44", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("offenseId=90"));
        assertTrue(history.getRequestParams().contains("driverId=91"));
    }

    @Test
    void checkAndInsertVehicleIdempotencyShouldPopulateRequestHistoryMetadata() {
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        VehicleInformationSearchRepository searchRepository = Mockito.mock(VehicleInformationSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, VehicleInformation> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        VehicleInformationService service = new VehicleInformationService(
                vehicleInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/vehicles");
        request.addHeader("X-Real-IP", "198.51.100.77");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        VehicleInformation vehicle = new VehicleInformation();
        vehicle.setLicensePlate("浙A12345");
        vehicle.setVehicleType("Sedan");
        vehicle.setOwnerName("Carol Driver");
        vehicle.setOwnerIdCard("110101199001010033");
        vehicle.setStatus("Active");

        service.checkAndInsertIdempotency("vehicle-key", vehicle, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        verify(requestHistoryMapper, never()).updateById(any(SysRequestHistory.class));
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/vehicles", history.getRequestUrl());
        assertEquals("VEHICLE_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals("198.51.100.77", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("licensePlate=浙A12345"));
        assertTrue(history.getRequestParams().contains("ownerIdCard=110101199001010033"));
    }

    @Test
    void searchVehicleByOwnerIdCardShouldUseExactMatchInDatabaseFallback() {
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        VehicleInformationSearchRepository searchRepository = Mockito.mock(VehicleInformationSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, VehicleInformation> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        VehicleInformationService service = new VehicleInformationService(
                vehicleInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository);

        when(searchRepository.searchByOwnerIdCard("110101199001010033", org.springframework.data.domain.PageRequest.of(0, 20)))
                .thenReturn(null);

        service.searchByOwnerIdCard("110101199001010033", 1, 20);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<QueryWrapper<VehicleInformation>> wrapperCaptor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(vehicleInformationMapper).selectPage(any(), wrapperCaptor.capture());
        String sqlSegment = wrapperCaptor.getValue().getSqlSegment();
        assertFalse(sqlSegment.toUpperCase().contains("LIKE"));
    }

    @Test
    void getVehicleInformationByOwnerNameShouldUsePagedDatabaseLoad() {
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        VehicleInformationSearchRepository searchRepository = Mockito.mock(VehicleInformationSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, VehicleInformation> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        VehicleInformationService service = new VehicleInformationService(
                vehicleInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository);

        VehicleInformation first = new VehicleInformation();
        first.setVehicleId(1L);
        VehicleInformation second = new VehicleInformation();
        second.setVehicleId(2L);
        when(vehicleInformationMapper.selectPage(any(), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<VehicleInformation> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second) : List.of());
            return page;
        });

        List<VehicleInformation> result = service.getVehicleInformationByOwnerName("Carol Driver");

        assertEquals(2, result.size());
        verify(vehicleInformationMapper, never()).selectList(any());
        verify(vehicleInformationMapper).selectPage(any(), any());
        verify(searchRepository).saveAll(any());
    }

    @Test
    void getVehicleInformationByIdCardNumberShouldUsePagedDatabaseLoad() {
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        VehicleInformationSearchRepository searchRepository = Mockito.mock(VehicleInformationSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, VehicleInformation> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        VehicleInformationService service = new VehicleInformationService(
                vehicleInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository);

        VehicleInformation first = new VehicleInformation();
        first.setVehicleId(3L);
        when(vehicleInformationMapper.selectPage(any(), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<VehicleInformation> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first) : List.of());
            return page;
        });

        List<VehicleInformation> result = service.getVehicleInformationByIdCardNumber("110101199001010033");

        assertEquals(1, result.size());
        verify(vehicleInformationMapper, never()).selectList(any());
        verify(vehicleInformationMapper).selectPage(any(), any());
        verify(searchRepository).saveAll(any());
    }

    @Test
    void saveCurrentDriverShouldApplyDraftFieldsAndSyncUserIdentity() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("alice", "n/a", Collections.emptyList()));

        com.tutict.finalassignmentbackend.entity.SysUser user =
                new com.tutict.finalassignmentbackend.entity.SysUser();
        user.setUserId(100L);
        user.setUsername("alice");
        user.setRealName("Old Name");
        user.setIdCardNumber("110101199001010011");
        user.setContactNumber("13800000000");
        user.setEmail("old@example.com");
        when(sysUserService.findByUsername("alice")).thenReturn(user);
        when(sysUserService.findByExactEmail("new@example.com")).thenReturn(null);
        when(sysUserService.findByExactIdCardNumber("110101199001010022")).thenReturn(null);
        when(sysUserService.updateSysUser(any())).thenAnswer(invocation -> invocation.getArgument(0));

        DriverInformation existingDriver = new DriverInformation();
        existingDriver.setDriverId(100L);
        existingDriver.setName("Old Driver");
        existingDriver.setIdCardNumber("110101199001010011");
        existingDriver.setContactNumber("13800000000");
        existingDriver.setDriverLicenseNumber("123456789012");
        existingDriver.setEmail("old@example.com");
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(existingDriver);
        when(driverInformationService.findByExactIdCardNumber("110101199001010022")).thenReturn(null);
        when(driverInformationService.findByExactDriverLicenseNumber("987654321098")).thenReturn(null);
        when(driverInformationService.updateDriver(any())).thenAnswer(invocation -> invocation.getArgument(0));

        DriverInformation draft = new DriverInformation();
        draft.setName("New Driver");
        draft.setIdCardNumber("110101199001010022");
        draft.setContactNumber("13900000000");
        draft.setDriverLicenseNumber("987654321098");
        draft.setEmail("new@example.com");
        draft.setAddress("New Address");

        DriverInformation updated = service.saveCurrentDriver(draft);

        assertEquals("New Driver", updated.getName());
        assertEquals("110101199001010022", updated.getIdCardNumber());
        assertEquals("13900000000", updated.getContactNumber());
        assertEquals("987654321098", updated.getDriverLicenseNumber());
        assertEquals("new@example.com", updated.getEmail());
        assertEquals("New Address", updated.getAddress());

        ArgumentCaptor<com.tutict.finalassignmentbackend.entity.SysUser> userCaptor =
                ArgumentCaptor.forClass(com.tutict.finalassignmentbackend.entity.SysUser.class);
        verify(sysUserService).updateSysUser(userCaptor.capture());
        assertEquals("110101199001010022", userCaptor.getValue().getIdCardNumber());
        assertEquals("13900000000", userCaptor.getValue().getContactNumber());
        verify(vehicleInformationService).reassignOwnerIdCard(
                "110101199001010011",
                "110101199001010022",
                "New Driver",
                "13900000000");
    }

    @Test
    void requestHistoryCrudShouldRejectManualMutation() {
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysRequestHistorySearchRepository searchRepository = Mockito.mock(SysRequestHistorySearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        SysRequestHistoryService service = new SysRequestHistoryService(
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        SysRequestHistory record = new SysRequestHistory();
        record.setId(501L);

        assertThrows(IllegalStateException.class, () -> service.createSysRequestHistory(record));
        assertThrows(IllegalStateException.class, () -> service.updateSysRequestHistory(record));
        assertThrows(IllegalStateException.class, () -> service.deleteSysRequestHistory(501L));
        verify(requestHistoryMapper, never()).insert(any(SysRequestHistory.class));
        verify(requestHistoryMapper, never()).updateById(any(SysRequestHistory.class));
        verify(requestHistoryMapper, never()).deleteById(any());
    }

    @Test
    void createCurrentUserVehicleShouldBindOwnerToCurrentUserScope() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        com.tutict.finalassignmentbackend.entity.SysUser user =
                new com.tutict.finalassignmentbackend.entity.SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        user.setRealName("Carol Driver");
        user.setIdCardNumber("110101199001010033");
        user.setContactNumber("13700000000");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        driver.setContactNumber("13700000000");
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);
        when(vehicleInformationService.createVehicleInformation(any()))
                .thenAnswer(invocation -> invocation.getArgument(0));

        VehicleInformation draft = new VehicleInformation();
        draft.setLicensePlate("沪A12345");
        draft.setVehicleType("Sedan");

        VehicleInformation created = service.createVehicleForCurrentUser(draft);

        assertEquals("110101199001010033", created.getOwnerIdCard());
        assertEquals("Carol Driver", created.getOwnerName());
        assertEquals("13700000000", created.getOwnerContact());
    }

    @Test
    void updateCurrentUserVehicleShouldIgnoreDraftOwnerIdentity() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        user.setRealName("Carol Driver");
        user.setIdCardNumber("110101199001010033");
        user.setContactNumber("13700000000");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        driver.setContactNumber("13700000000");
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        VehicleInformation existingVehicle = new VehicleInformation();
        existingVehicle.setVehicleId(300L);
        existingVehicle.setOwnerIdCard("110101199001010033");
        existingVehicle.setOwnerName("Old Stored Name");
        existingVehicle.setOwnerContact("13600000000");
        when(vehicleInformationService.getVehicleInformationById(300L)).thenReturn(existingVehicle);
        when(vehicleInformationService.updateVehicleInformation(any()))
                .thenAnswer(invocation -> invocation.getArgument(0));

        VehicleInformation draft = new VehicleInformation();
        draft.setLicensePlate("浙A12345");
        draft.setVehicleType("Sedan");
        draft.setOwnerIdCard("110101199001010033");
        draft.setOwnerName("Forged Name");
        draft.setOwnerContact("13999999999");

        VehicleInformation updated = service.updateVehicleForCurrentUser(300L, draft);

        assertEquals("110101199001010033", updated.getOwnerIdCard());
        assertEquals("Carol Driver", updated.getOwnerName());
        assertEquals("13700000000", updated.getOwnerContact());
    }

    @Test
    void createCurrentUserAppealShouldOverrideAppellantIdentityWithCurrentUserScope() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        user.setRealName("Carol Driver");
        user.setIdCardNumber("110101199001010033");
        user.setContactNumber("13700000000");
        user.setEmail("carol@example.com");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        driver.setContactNumber("13700000000");
        driver.setEmail("driver@example.com");
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(500L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(500L)).thenReturn(offense);
        when(appealRecordService.createAppeal(any())).thenAnswer(invocation -> invocation.getArgument(0));

        AppealRecord draft = new AppealRecord();
        draft.setOffenseId(500L);
        draft.setAppellantName("Forged Name");
        draft.setAppellantIdCard("110101199001010099");
        draft.setAppellantContact("13999999999");
        draft.setAppellantEmail("forged@example.com");

        AppealRecord created = service.createAppealForCurrentUser(draft);

        assertEquals("Carol Driver", created.getAppellantName());
        assertEquals("110101199001010033", created.getAppellantIdCard());
        assertEquals("13700000000", created.getAppellantContact());
        assertEquals("driver@example.com", created.getAppellantEmail());
    }

    @Test
    void createCurrentUserAppealShouldRejectIncompleteCurrentUserProfile() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        user.setRealName("Carol Driver");
        user.setIdCardNumber("110101199001010033");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(500L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(500L)).thenReturn(offense);

        AppealRecord draft = new AppealRecord();
        draft.setOffenseId(500L);

        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> service.createAppealForCurrentUser(draft));

        assertEquals("Complete your personal profile before submitting an appeal", ex.getMessage());
        verify(appealRecordService, never()).createAppeal(any());
    }

    @Test
    void currentUserShouldResubmitOwnRejectedAppeal() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(501L);
        existing.setOffenseId(500L);
        existing.setAcceptanceStatus(AppealAcceptanceState.REJECTED.getCode());
        when(appealRecordService.getAppealById(501L)).thenReturn(existing);
        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(500L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(500L)).thenReturn(offense);

        AppealRecord updated = new AppealRecord();
        updated.setAppealId(501L);
        updated.setOffenseId(500L);
        updated.setAcceptanceStatus(AppealAcceptanceState.PENDING.getCode());
        when(stateMachineService.processAppealAcceptanceState(
                501L,
                AppealAcceptanceState.REJECTED,
                AppealAcceptanceEvent.RESUBMIT)).thenReturn(AppealAcceptanceState.PENDING);
        when(appealRecordService.updateAcceptanceStatus(501L, AppealAcceptanceState.PENDING)).thenReturn(updated);

        AppealRecord result = service.triggerCurrentUserAppealAcceptanceEvent(501L, AppealAcceptanceEvent.RESUBMIT);

        assertEquals(AppealAcceptanceState.PENDING.getCode(), result.getAcceptanceStatus());
        verify(offenseRecordService).findById(500L);
        verify(offenseRecordService, never()).findIdsByDriverIds(any());
        verify(appealRecordService).updateAcceptanceStatus(501L, AppealAcceptanceState.PENDING);
    }

    @Test
    void currentUserAppealAcceptanceEventShouldRejectManagerOnlyTransitions() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        assertThrows(IllegalArgumentException.class,
                () -> service.triggerCurrentUserAppealAcceptanceEvent(501L, AppealAcceptanceEvent.ACCEPT));
        verify(stateMachineService, never()).processAppealAcceptanceState(any(), any(), any());
    }

    @Test
    void currentUserAppealAcceptanceEventShouldPersistSupplementFieldsBeforeCompleting() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(501L);
        existing.setOffenseId(500L);
        existing.setAcceptanceStatus(AppealAcceptanceState.NEED_SUPPLEMENT.getCode());
        when(appealRecordService.getAppealById(501L)).thenReturn(existing);
        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(500L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(500L)).thenReturn(offense);

        AppealRecord supplementDraft = new AppealRecord();
        supplementDraft.setAppealReason("Updated supplement reason");
        supplementDraft.setEvidenceDescription("Uploaded additional explanation");
        supplementDraft.setEvidenceUrls("[\"supplement-1\"]");

        AppealRecord updatedSupplement = new AppealRecord();
        updatedSupplement.setAppealId(501L);
        updatedSupplement.setOffenseId(500L);
        updatedSupplement.setAcceptanceStatus(AppealAcceptanceState.NEED_SUPPLEMENT.getCode());
        updatedSupplement.setAppealReason("Updated supplement reason");
        when(appealRecordService.updateSupplementFieldsSystemManaged(501L, supplementDraft))
                .thenReturn(updatedSupplement);
        when(stateMachineService.processAppealAcceptanceState(
                501L,
                AppealAcceptanceState.NEED_SUPPLEMENT,
                AppealAcceptanceEvent.SUPPLEMENT_COMPLETE)).thenReturn(AppealAcceptanceState.PENDING);

        AppealRecord finalRecord = new AppealRecord();
        finalRecord.setAppealId(501L);
        finalRecord.setAcceptanceStatus(AppealAcceptanceState.PENDING.getCode());
        when(appealRecordService.updateAcceptanceStatus(501L, AppealAcceptanceState.PENDING)).thenReturn(finalRecord);

        AppealRecord result = service.triggerCurrentUserAppealAcceptanceEvent(
                501L,
                AppealAcceptanceEvent.SUPPLEMENT_COMPLETE,
                supplementDraft);

        assertEquals(AppealAcceptanceState.PENDING.getCode(), result.getAcceptanceStatus());
        verify(offenseRecordService).findById(500L);
        verify(offenseRecordService, never()).findIdsByDriverIds(any());
        verify(appealRecordService).updateSupplementFieldsSystemManaged(501L, supplementDraft);
        verify(appealRecordService).updateAcceptanceStatus(501L, AppealAcceptanceState.PENDING);
    }

    @Test
    void currentUserAppealAcceptanceEventShouldRejectAppealOutsideUserActionStates() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(501L);
        existing.setOffenseId(500L);
        existing.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        when(appealRecordService.getAppealById(501L)).thenReturn(existing);
        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(500L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(500L)).thenReturn(offense);

        assertThrows(IllegalStateException.class,
                () -> service.triggerCurrentUserAppealAcceptanceEvent(
                        501L,
                        AppealAcceptanceEvent.SUPPLEMENT_COMPLETE,
                        new AppealRecord()));
        verify(offenseRecordService).findById(500L);
        verify(offenseRecordService, never()).findIdsByDriverIds(any());
        verify(appealRecordService, never()).updateSupplementFieldsSystemManaged(any(), any());
        verify(stateMachineService, never()).processAppealAcceptanceState(any(), any(), any());
    }

    @Test
    void createCurrentUserPaymentShouldPopulatePayerFieldsWithinCurrentUserScope() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        user.setRealName("Carol Driver");
        user.setIdCardNumber("110101199001010033");
        user.setContactNumber("13700000000");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        driver.setContactNumber("13700000000");
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(701L);
        fineRecord.setOffenseId(702L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(120));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(120));
        when(fineRecordService.findById(701L)).thenReturn(fineRecord);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(702L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(702L)).thenReturn(offense);

        when(paymentRecordService.createPaymentRecord(any(PaymentRecord.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        PaymentRecord draft = new PaymentRecord();
        draft.setFineId(701L);
        draft.setPaymentAmount(BigDecimal.valueOf(120));

        PaymentRecord created = service.createPaymentForCurrentUser(draft);

        assertEquals("Carol Driver", created.getPayerName());
        assertEquals("110101199001010033", created.getPayerIdCard());
        assertEquals("13700000000", created.getPayerContact());
        assertEquals("WeChat", created.getPaymentMethod());
        assertEquals("USER_SELF_SERVICE", created.getPaymentChannel());
        verify(fineRecordService, Mockito.times(1)).findById(701L);
        verify(offenseRecordService, Mockito.times(1)).findById(702L);
    }

    @Test
    void listCurrentUserPaymentsByFineIdShouldOnlyReturnCurrentUserPayments() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        user.setIdCardNumber("110101199001010033");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        driver.setIdCardNumber("110101199001010033");
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(701L);
        fineRecord.setOffenseId(702L);
        when(fineRecordService.findById(701L)).thenReturn(fineRecord);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(702L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(702L)).thenReturn(offense);

        PaymentRecord ownPayment = new PaymentRecord();
        ownPayment.setPaymentId(801L);
        ownPayment.setFineId(701L);
        ownPayment.setPayerIdCard("110101199001010033");

        when(paymentRecordService.findByFineIdAndPayerIdCard(701L, "110101199001010033", 1, 20))
                .thenReturn(List.of(ownPayment));

        List<PaymentRecord> result = service.listCurrentUserPaymentsByFineId(701L, 1, 20);

        assertEquals(1, result.size());
        assertEquals(801L, result.get(0).getPaymentId());
    }

    @Test
    void triggerCurrentUserAppealProcessEventShouldWithdrawOwnedAppeal() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("carol", "n/a", Collections.emptyList()));

        SysUser user = new SysUser();
        user.setUserId(200L);
        user.setUsername("carol");
        when(sysUserService.findByUsername("carol")).thenReturn(user);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(200L);
        when(driverInformationService.findLinkedDriverForUser(any())).thenReturn(driver);

        AppealRecord appeal = new AppealRecord();
        appeal.setAppealId(501L);
        appeal.setOffenseId(702L);
        appeal.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
        when(appealRecordService.getAppealById(501L)).thenReturn(appeal);
        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(702L);
        offense.setDriverId(200L);
        when(offenseRecordService.findById(702L)).thenReturn(offense);
        when(stateMachineService.processAppealState(
                501L,
                AppealProcessState.UNPROCESSED,
                AppealProcessEvent.WITHDRAW)).thenReturn(AppealProcessState.WITHDRAWN);

        AppealRecord updated = new AppealRecord();
        updated.setAppealId(501L);
        updated.setProcessStatus(AppealProcessState.WITHDRAWN.getCode());
        when(appealRecordService.updateProcessStatus(501L, AppealProcessState.WITHDRAWN)).thenReturn(updated);

        AppealRecord result = service.triggerCurrentUserAppealProcessEvent(501L, AppealProcessEvent.WITHDRAW);

        assertEquals(AppealProcessState.WITHDRAWN.getCode(), result.getProcessStatus());
        verify(offenseRecordService).findById(702L);
        verify(offenseRecordService, never()).findIdsByDriverIds(any());
        verify(appealRecordService).updateProcessStatus(501L, AppealProcessState.WITHDRAWN);
    }

    @Test
    void createCurrentUserAppealShouldMarkHistoryFailureForRejectedCurrentUserRequest() {
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        AppealReviewService appealReviewService = Mockito.mock(AppealReviewService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        AppealManagementController controller = new AppealManagementController(
                appealRecordService,
                appealReviewService,
                currentUserTrafficSupportService);

        AppealManagementController.CurrentUserAppealCreateRequest request =
                new AppealManagementController.CurrentUserAppealCreateRequest();
        request.setOffenseId(500L);
        request.setAppealReason("Need review");

        when(appealRecordService.shouldSkipProcessing("appeal-key")).thenReturn(false);
        Mockito.doNothing().when(appealRecordService)
                .checkAndInsertIdempotency(eq("appeal-key"), any(AppealRecord.class), eq("create"));
        when(currentUserTrafficSupportService.createAppealForCurrentUser(any(AppealRecord.class)))
                .thenThrow(new IllegalStateException("Offense does not belong to current user"));

        ResponseEntity<AppealRecord> response = controller.createCurrentUserAppeal(request, "appeal-key");

        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        verify(appealRecordService).markHistoryFailure("appeal-key", "Offense does not belong to current user");
    }

    @Test
    void confirmCurrentUserPaymentShouldMarkHistoryFailureForRejectedCurrentUserRequest() {
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        PaymentRecordController controller = new PaymentRecordController(
                paymentRecordService,
                currentUserTrafficSupportService);

        PaymentRecordController.CurrentUserPaymentConfirmationRequest request =
                new PaymentRecordController.CurrentUserPaymentConfirmationRequest();
        request.setTransactionId("WX-20260410-0003");

        when(paymentRecordService.shouldSkipProcessing("payment-confirm-key")).thenReturn(false);
        Mockito.doNothing().when(paymentRecordService)
                .checkAndInsertIdempotency(any(), any(PaymentRecord.class), eq("confirm"));
        when(currentUserTrafficSupportService.confirmCurrentUserPayment(eq(902L), any(PaymentRecord.class)))
                .thenThrow(new IllegalStateException("Pending self-service payment order has expired"));

        ResponseEntity<PaymentRecord> response =
                controller.confirmCurrentUserPayment(902L, request, "payment-confirm-key");

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        verify(paymentRecordService).markHistoryFailure(
                "payment-confirm-key",
                "Pending self-service payment order has expired");
    }

    @Test
    void reviewPaymentShouldMarkHistoryFailureForRejectedFinanceReviewRequest() {
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        PaymentRecordController controller = new PaymentRecordController(
                paymentRecordService,
                currentUserTrafficSupportService);

        PaymentRecordController.PaymentFinanceReviewRequest request =
                new PaymentRecordController.PaymentFinanceReviewRequest();
        request.setReviewResult("NEED_PROOF");
        request.setReviewOpinion("Please upload receipt");

        when(paymentRecordService.shouldSkipProcessing("payment-review-key")).thenReturn(false);
        Mockito.doNothing().when(paymentRecordService)
                .checkAndInsertIdempotency(any(), any(PaymentRecord.class), eq("review"));
        when(paymentRecordService.recordFinanceReview(902L, "NEED_PROOF", "Please upload receipt"))
                .thenThrow(new IllegalStateException("Only confirmed self-service payment records can be reviewed"));

        IllegalStateException ex = assertThrows(
                IllegalStateException.class,
                () -> controller.reviewPayment(902L, request, "payment-review-key"));

        assertEquals("Only confirmed self-service payment records can be reviewed", ex.getMessage());
        verify(paymentRecordService).markHistoryFailure(
                "payment-review-key",
                "Only confirmed self-service payment records can be reviewed");
    }

    @Test
    void updateCurrentUserPaymentProofShouldMarkHistoryFailureForRejectedProofUpdate() {
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        PaymentRecordController controller = new PaymentRecordController(
                paymentRecordService,
                currentUserTrafficSupportService);

        PaymentRecordController.CurrentUserPaymentProofRequest request =
                new PaymentRecordController.CurrentUserPaymentProofRequest();
        request.setReceiptUrl("https://example.com/proof/new-902");

        when(paymentRecordService.shouldSkipProcessing("payment-proof-key")).thenReturn(false);
        Mockito.doNothing().when(paymentRecordService)
                .checkAndInsertIdempotency(any(), any(PaymentRecord.class), eq("proof"));
        when(currentUserTrafficSupportService.updateCurrentUserPaymentProof(eq(902L), any(PaymentRecord.class)))
                .thenThrow(new IllegalStateException("Only confirmed self-service payment records can update proof"));

        ResponseEntity<PaymentRecord> response =
                controller.updateCurrentUserPaymentProof(902L, request, "payment-proof-key");

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        verify(paymentRecordService).markHistoryFailure(
                "payment-proof-key",
                "Only confirmed self-service payment records can update proof");
    }

    @Test
    void currentUserAppealAcceptanceEndpointShouldReturnConflictForInvalidSelfServiceTransition() {
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        AppealReviewService appealReviewService = Mockito.mock(AppealReviewService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        AppealManagementController controller = new AppealManagementController(
                appealRecordService,
                appealReviewService,
                currentUserTrafficSupportService);

        when(currentUserTrafficSupportService.triggerCurrentUserAppealAcceptanceEvent(
                501L,
                AppealAcceptanceEvent.RESUBMIT,
                null)).thenThrow(new IllegalStateException("Appeal acceptance state does not allow this event"));

        ResponseEntity<AppealRecord> response = controller.triggerCurrentUserAppealAcceptanceEvent(
                501L,
                AppealAcceptanceEvent.RESUBMIT,
                null);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
    }

    @Test
    void currentUserAppealProcessEndpointShouldReturnConflictForInvalidSelfServiceTransition() {
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        AppealReviewService appealReviewService = Mockito.mock(AppealReviewService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        AppealManagementController controller = new AppealManagementController(
                appealRecordService,
                appealReviewService,
                currentUserTrafficSupportService);

        when(currentUserTrafficSupportService.triggerCurrentUserAppealProcessEvent(
                501L,
                AppealProcessEvent.WITHDRAW)).thenThrow(new IllegalStateException("Appeal process state does not allow this event"));

        ResponseEntity<AppealRecord> response = controller.triggerCurrentUserAppealProcessEvent(
                501L,
                AppealProcessEvent.WITHDRAW);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
    }

    @Test
    void currentUserAppealAcceptanceEndpointShouldForwardSupplementPayload() {
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        AppealReviewService appealReviewService = Mockito.mock(AppealReviewService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);

        AppealManagementController controller = new AppealManagementController(
                appealRecordService,
                appealReviewService,
                currentUserTrafficSupportService);

        AppealManagementController.CurrentUserAppealSubmissionRequest request =
                new AppealManagementController.CurrentUserAppealSubmissionRequest();
        request.setAppealReason("Need to add more detail");
        request.setEvidenceDescription("Uploaded dashboard screenshots");
        request.setEvidenceUrls("[\"https://example.com/evidence.png\"]");

        AppealRecord updated = new AppealRecord();
        updated.setAppealId(501L);
        updated.setAcceptanceStatus(AppealAcceptanceState.PENDING.getCode());
        when(currentUserTrafficSupportService.triggerCurrentUserAppealAcceptanceEvent(
                eq(501L),
                eq(AppealAcceptanceEvent.SUPPLEMENT_COMPLETE),
                any(AppealRecord.class))).thenReturn(updated);

        ResponseEntity<AppealRecord> response = controller.triggerCurrentUserAppealAcceptanceEvent(
                501L,
                AppealAcceptanceEvent.SUPPLEMENT_COMPLETE,
                request);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        ArgumentCaptor<AppealRecord> captor = ArgumentCaptor.forClass(AppealRecord.class);
        verify(currentUserTrafficSupportService).triggerCurrentUserAppealAcceptanceEvent(
                eq(501L),
                eq(AppealAcceptanceEvent.SUPPLEMENT_COMPLETE),
                captor.capture());
        assertEquals("Need to add more detail", captor.getValue().getAppealReason());
        assertEquals("Uploaded dashboard screenshots", captor.getValue().getEvidenceDescription());
        assertEquals("[\"https://example.com/evidence.png\"]", captor.getValue().getEvidenceUrls());
    }

    @Test
    void createDeductionShouldDeriveDriverIdFromOffenseWhenMissing() {
        TransactionSynchronizationManager.initSynchronization();

        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DeductionRecordSearchRepository searchRepository = Mockito.mock(DeductionRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, DeductionRecord> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DeductionRecordService service = new DeductionRecordService(
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                offenseRecordService,
                driverInformationService,
                sysUserService,
                kafkaTemplate);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(600L);
        offense.setDriverId(601L);
        when(offenseRecordService.findById(600L)).thenReturn(offense);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(601L);
        when(driverInformationService.getDriverById(601L)).thenReturn(driver);

        DeductionRecord draft = new DeductionRecord();
        draft.setOffenseId(600L);
        draft.setDeductedPoints(3);

        service.createDeductionRecord(draft);

        ArgumentCaptor<DeductionRecord> captor = ArgumentCaptor.forClass(DeductionRecord.class);
        verify(deductionRecordMapper).insert(captor.capture());
        assertEquals(601L, captor.getValue().getDriverId());
    }

    @Test
    void updateReviewSystemManagedShouldRejectChangesAfterAppealFinalized() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(300L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        appealRecord.setProcessStatus(AppealProcessState.APPROVED.getCode());
        when(appealRecordService.getAppealById(300L)).thenReturn(appealRecord);

        AppealReview existing = new AppealReview();
        existing.setReviewId(301L);
        existing.setAppealId(300L);
        existing.setReviewLevel("Initial");
        existing.setReviewResult("Approved");
        when(appealReviewMapper.selectById(301L)).thenReturn(existing);
        when(appealReviewMapper.selectCount(any())).thenReturn(0L);

        AppealReview incoming = new AppealReview();
        incoming.setReviewId(301L);
        incoming.setAppealId(300L);
        incoming.setReviewLevel("Initial");
        incoming.setReviewResult("Rejected");

        assertThrows(IllegalStateException.class, () -> service.updateReviewSystemManaged(incoming));
        verify(appealReviewMapper, never()).updateById(any(AppealReview.class));
    }

    @Test
    void updateReviewShouldRejectManualMutation() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        AppealReview request = new AppealReview();
        request.setReviewId(301L);

        assertThrows(IllegalStateException.class, () -> service.updateReview(request));
        verify(appealReviewMapper, never()).updateById(any(AppealReview.class));
    }

    @Test
    void deleteReviewShouldRejectManualDeletion() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        assertThrows(IllegalStateException.class, () -> service.deleteReview(301L));
        verify(appealReviewMapper, never()).deleteById(any());
    }

    @Test
    void checkAndInsertAppealReviewIdempotencyShouldPopulateRequestHistoryMetadata() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("reviewer", "n/a", Collections.emptyList()));
        SysUser user = new SysUser();
        user.setUserId(99L);
        when(sysUserService.findByUsername("reviewer")).thenReturn(user);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/appeals/310/reviews");
        request.addHeader("X-Forwarded-For", "203.0.113.99");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        AppealReview review = new AppealReview();
        review.setAppealId(310L);
        review.setReviewLevel("Final");
        review.setReviewResult("Approved");
        review.setSuggestedAction("Cancel_Offense");

        service.checkAndInsertIdempotency("review-key", review, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/appeals/310/reviews", history.getRequestUrl());
        assertEquals("APPEAL_REVIEW_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals(99L, history.getUserId());
        assertEquals("203.0.113.99", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("appealId=310"));
        assertTrue(history.getRequestParams().contains("reviewLevel=Final"));
    }

    @Test
    void deleteOffenseShouldRejectWhenDeductionRecordsExist() {
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        FineRecordMapper fineRecordMapper = Mockito.mock(FineRecordMapper.class);
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        OffenseInformationSearchRepository searchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        OffenseRecordService service = new OffenseRecordService(
                offenseRecordMapper,
                fineRecordMapper,
                appealRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                searchRepository,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        when(fineRecordMapper.selectCount(any())).thenReturn(0L);
        when(deductionRecordMapper.selectCount(any())).thenReturn(1L);

        assertThrows(IllegalStateException.class, () -> service.deleteOffenseRecord(10L));
        verify(offenseRecordMapper, never()).deleteById(any());
    }

    @Test
    void createReviewShouldRejectDuplicateReviewLevelForAppeal() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(310L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        appealRecord.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        when(appealRecordService.getAppealById(310L)).thenReturn(appealRecord);

        when(appealReviewMapper.selectCount(any())).thenReturn(1L);

        AppealReview request = new AppealReview();
        request.setAppealId(310L);
        request.setReviewLevel("Final");
        request.setReviewResult("Approved");

        assertThrows(IllegalStateException.class, () -> service.createReview(request));
        verify(appealReviewMapper, never()).insert(any(AppealReview.class));
    }

    @Test
    void createReviewShouldOverrideClientControlledAuditFields() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("reviewer-a", "n/a", Collections.emptyList()));

        SysUser reviewer = new SysUser();
        reviewer.setUsername("reviewer-a");
        reviewer.setDepartment("Appeals");
        when(sysUserService.findByUsername("reviewer-a")).thenReturn(reviewer);

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(81L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        appealRecord.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        when(appealRecordService.getAppealById(81L)).thenReturn(appealRecord);
        when(appealReviewMapper.selectCount(any())).thenReturn(0L);
        when(appealReviewMapper.insert(any(AppealReview.class))).thenReturn(1);

        LocalDateTime spoofedTime = LocalDateTime.of(2000, 1, 1, 0, 0);

        AppealReview request = new AppealReview();
        request.setReviewId(999L);
        request.setAppealId(81L);
        request.setReviewLevel("Primary");
        request.setReviewResult("Approved");
        request.setTenantId("fake-tenant");
        request.setOrganizationCode("fake-org");
        request.setRegionCode("fake-region");
        request.setDepartmentCode("fake-dept");
        request.setReviewer("fake-reviewer");
        request.setReviewerDept("fake-reviewer-dept");
        request.setReviewTime(spoofedTime);
        request.setCreatedAt(spoofedTime);
        request.setUpdatedAt(spoofedTime);
        request.setDeletedAt(spoofedTime);

        service.createReview(request);

        ArgumentCaptor<AppealReview> captor = ArgumentCaptor.forClass(AppealReview.class);
        verify(appealReviewMapper).insert(captor.capture());
        AppealReview saved = captor.getValue();
        assertNull(saved.getReviewId());
        assertNull(saved.getTenantId());
        assertNull(saved.getOrganizationCode());
        assertNull(saved.getRegionCode());
        assertNull(saved.getDepartmentCode());
        assertEquals("reviewer-a", saved.getReviewer());
        assertEquals("Appeals", saved.getReviewerDept());
        assertNotNull(saved.getReviewTime());
        assertNotEquals(spoofedTime, saved.getReviewTime());
        assertNull(saved.getCreatedAt());
        assertNull(saved.getUpdatedAt());
        assertNull(saved.getDeletedAt());
    }

    @Test
    void finalApprovedReviewShouldPersistProcessResultFromReviewOpinion() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(309L);
        appealRecord.setOffenseId(409L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        appealRecord.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        when(appealRecordService.getAppealById(309L)).thenReturn(appealRecord);
        when(appealReviewMapper.selectCount(any())).thenReturn(0L);
        when(appealReviewMapper.insert(any(AppealReview.class))).thenReturn(1);

        AppealReview review = new AppealReview();
        review.setAppealId(309L);
        review.setReviewLevel("Final");
        review.setReviewResult("Approved");
        review.setReviewOpinion("Evidence verified and appeal approved");

        service.createReview(review);

        verify(appealRecordService).updateProcessStatus(
                309L,
                AppealProcessState.APPROVED,
                "Evidence verified and appeal approved");
    }

    @Test
    void finalApprovedReviewShouldSyncOffensePenaltySummaryAfterFineReduction() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(310L);
        appealRecord.setOffenseId(410L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        appealRecord.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        when(appealRecordService.getAppealById(310L)).thenReturn(appealRecord);

        AppealRecord approvedAppeal = new AppealRecord();
        approvedAppeal.setAppealId(310L);
        approvedAppeal.setOffenseId(410L);
        approvedAppeal.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        approvedAppeal.setProcessStatus(AppealProcessState.APPROVED.getCode());
        when(appealRecordService.updateProcessStatus(310L, AppealProcessState.APPROVED, "Approved"))
                .thenReturn(approvedAppeal);

        when(appealReviewMapper.selectCount(any())).thenReturn(0L);
        when(appealReviewMapper.insert(any(AppealReview.class))).thenReturn(1);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(510L);
        fineRecord.setFineAmount(BigDecimal.valueOf(200));
        fineRecord.setLateFee(BigDecimal.ZERO);
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        when(fineRecordService.findByOffenseId(410L, 1, 200)).thenReturn(List.of(fineRecord));

        AppealReview review = new AppealReview();
        review.setAppealId(310L);
        review.setReviewLevel("Final");
        review.setReviewResult("Approved");
        review.setSuggestedAction("Reduce_Fine");
        review.setSuggestedFineAmount(BigDecimal.valueOf(80));

        service.createReview(review);

        verify(offenseRecordService).updatePenaltySummary(410L, BigDecimal.valueOf(80), null, null);
        verify(fineRecordService).updateFineRecordSystemManaged(any(FineRecord.class));
    }

    @Test
    void updateAcceptanceStatusShouldReturnOffenseToProcessedWhenAppealRejected() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(320L);
        existing.setOffenseId(420L);
        existing.setAcceptanceStatus(AppealAcceptanceState.PENDING.getCode());
        existing.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        existing.setProcessResult("Old result");
        existing.setProcessHandler("reviewer-a");
        existing.setProcessTime(LocalDateTime.now().minusDays(1));
        when(appealRecordMapper.selectById(320L)).thenReturn(existing);
        when(appealRecordMapper.updateById(any(AppealRecord.class))).thenReturn(1);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(420L);
        offense.setProcessStatus(OffenseProcessState.APPEALING.getCode());
        when(offenseRecordService.findById(420L)).thenReturn(offense);
        when(stateMachineService.canTransitionOffenseState(
                OffenseProcessState.APPEALING,
                OffenseProcessEvent.WITHDRAW_APPEAL)).thenReturn(true);
        when(stateMachineService.processOffenseState(
                420L,
                OffenseProcessState.APPEALING,
                OffenseProcessEvent.WITHDRAW_APPEAL)).thenReturn(OffenseProcessState.PROCESSED);

        service.updateAcceptanceStatus(320L, AppealAcceptanceState.REJECTED, "Missing supporting evidence");

        ArgumentCaptor<AppealRecord> captor = ArgumentCaptor.forClass(AppealRecord.class);
        verify(appealRecordMapper).updateById(captor.capture());
        assertEquals(AppealAcceptanceState.REJECTED.getCode(), captor.getValue().getAcceptanceStatus());
        assertEquals(AppealProcessState.UNPROCESSED.getCode(), captor.getValue().getProcessStatus());
        assertNull(captor.getValue().getProcessResult());
        assertNull(captor.getValue().getProcessHandler());
        assertNull(captor.getValue().getProcessTime());
        assertEquals("Missing supporting evidence", captor.getValue().getRejectionReason());
        verify(offenseRecordService).updateProcessStatus(420L, OffenseProcessState.PROCESSED);
    }

    @Test
    void updateAcceptanceStatusShouldRestoreAppealingWhenRejectedAppealIsResubmitted() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(321L);
        existing.setOffenseId(421L);
        existing.setAcceptanceStatus(AppealAcceptanceState.REJECTED.getCode());
        existing.setRejectionReason("Please provide a clearer explanation");
        existing.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
        when(appealRecordMapper.selectById(321L)).thenReturn(existing);
        when(appealRecordMapper.updateById(any(AppealRecord.class))).thenReturn(1);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(421L);
        offense.setProcessStatus(OffenseProcessState.PROCESSED.getCode());
        when(offenseRecordService.findById(421L)).thenReturn(offense);
        when(stateMachineService.canTransitionOffenseState(
                OffenseProcessState.PROCESSED,
                OffenseProcessEvent.SUBMIT_APPEAL)).thenReturn(true);
        when(stateMachineService.processOffenseState(
                421L,
                OffenseProcessState.PROCESSED,
                OffenseProcessEvent.SUBMIT_APPEAL)).thenReturn(OffenseProcessState.APPEALING);

        service.updateAcceptanceStatus(321L, AppealAcceptanceState.PENDING);

        ArgumentCaptor<AppealRecord> captor = ArgumentCaptor.forClass(AppealRecord.class);
        verify(appealRecordMapper).updateById(captor.capture());
        assertEquals(AppealAcceptanceState.PENDING.getCode(), captor.getValue().getAcceptanceStatus());
        assertNull(captor.getValue().getAcceptanceTime());
        assertNull(captor.getValue().getAcceptanceHandler());
        assertNull(captor.getValue().getRejectionReason());
        assertEquals(AppealProcessState.UNPROCESSED.getCode(), captor.getValue().getProcessStatus());
        verify(offenseRecordService).updateProcessStatus(421L, OffenseProcessState.APPEALING);
    }

    @Test
    void updateAcceptanceStatusShouldKeepSupplementReasonWhenRequestingMaterials() {
        AppealRecordMapper appealRecordMapper = Mockito.mock(AppealRecordMapper.class);
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        AppealRecordSearchRepository searchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        AppealRecordService service = new AppealRecordService(
                appealRecordMapper,
                appealReviewMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                offenseRecordService,
                sysUserService,
                stateMachineService,
                new ObjectMapper());

        AppealRecord existing = new AppealRecord();
        existing.setAppealId(322L);
        existing.setOffenseId(422L);
        existing.setAcceptanceStatus(AppealAcceptanceState.PENDING.getCode());
        existing.setProcessStatus(AppealProcessState.UNPROCESSED.getCode());
        when(appealRecordMapper.selectById(322L)).thenReturn(existing);
        when(appealRecordMapper.updateById(any(AppealRecord.class))).thenReturn(1);

        OffenseRecord offense = new OffenseRecord();
        offense.setOffenseId(422L);
        offense.setProcessStatus(OffenseProcessState.APPEALING.getCode());
        when(offenseRecordService.findById(422L)).thenReturn(offense);

        service.updateAcceptanceStatus(322L,
                AppealAcceptanceState.NEED_SUPPLEMENT,
                "Please upload clearer evidence");

        ArgumentCaptor<AppealRecord> captor = ArgumentCaptor.forClass(AppealRecord.class);
        verify(appealRecordMapper).updateById(captor.capture());
        assertEquals(AppealAcceptanceState.NEED_SUPPLEMENT.getCode(), captor.getValue().getAcceptanceStatus());
        assertEquals("Please upload clearer evidence", captor.getValue().getRejectionReason());
    }

    @Test
    void createReviewShouldRejectFineIncreaseSuggestion() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(311L);
        appealRecord.setOffenseId(411L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        appealRecord.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        when(appealRecordService.getAppealById(311L)).thenReturn(appealRecord);
        when(appealReviewMapper.selectCount(any())).thenReturn(0L);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(511L);
        fineRecord.setFineAmount(BigDecimal.valueOf(120));
        when(fineRecordService.findByOffenseId(411L, 1, 200)).thenReturn(List.of(fineRecord));

        AppealReview review = new AppealReview();
        review.setAppealId(311L);
        review.setReviewLevel("Final");
        review.setReviewResult("Approved");
        review.setSuggestedAction("Reduce_Fine");
        review.setSuggestedFineAmount(BigDecimal.valueOf(150));

        assertThrows(IllegalArgumentException.class, () -> service.createReview(review));
        verify(appealReviewMapper, never()).insert(any(AppealReview.class));
        verify(offenseRecordService, never()).updatePenaltySummary(any(), any(), any(), any());
    }

    @Test
    void createReviewShouldRejectPointIncreaseSuggestion() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository searchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                requestHistoryMapper,
                searchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper());

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(312L);
        appealRecord.setOffenseId(412L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.ACCEPTED.getCode());
        appealRecord.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        when(appealRecordService.getAppealById(312L)).thenReturn(appealRecord);
        when(appealReviewMapper.selectCount(any())).thenReturn(0L);

        DeductionRecord deductionRecord = new DeductionRecord();
        deductionRecord.setDeductionId(612L);
        deductionRecord.setDeductedPoints(3);
        when(deductionRecordService.findByOffenseId(412L, 1, 200)).thenReturn(List.of(deductionRecord));

        AppealReview review = new AppealReview();
        review.setAppealId(312L);
        review.setReviewLevel("Final");
        review.setReviewResult("Approved");
        review.setSuggestedAction("Reduce_Points");
        review.setSuggestedPoints(5);

        assertThrows(IllegalArgumentException.class, () -> service.createReview(review));
        verify(appealReviewMapper, never()).insert(any(AppealReview.class));
        verify(offenseRecordService, never()).updatePenaltySummary(any(), any(), any(), any());
    }

    @Test
    void saveCurrentDriverShouldRejectDuplicateDraftIdCardBeforeSyncingUserProfile() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("alice", "n/a", Collections.emptyList()));

        SysUser currentUser = new SysUser();
        currentUser.setUserId(700L);
        currentUser.setUsername("alice");
        currentUser.setRealName("Alice Driver");
        currentUser.setIdCardNumber("110101199001010011");
        currentUser.setContactNumber("13800138000");
        currentUser.setEmail("alice@example.com");
        when(sysUserService.findByUsername("alice")).thenReturn(currentUser);

        DriverInformation existingDriver = new DriverInformation();
        existingDriver.setDriverId(701L);
        existingDriver.setName("Alice Driver");
        existingDriver.setIdCardNumber("110101199001010011");
        existingDriver.setDriverLicenseNumber("123456789012");
        existingDriver.setContactNumber("13800138000");
        existingDriver.setEmail("alice@example.com");
        when(driverInformationService.findLinkedDriverForUser(currentUser)).thenReturn(existingDriver);

        SysUser otherUser = new SysUser();
        otherUser.setUserId(999L);
        otherUser.setIdCardNumber("110101199001010099");
        when(sysUserService.findByExactIdCardNumber("110101199001010099")).thenReturn(otherUser);

        DriverInformation draft = new DriverInformation();
        draft.setIdCardNumber("110101199001010099");

        assertThrows(IllegalArgumentException.class, () -> service.saveCurrentDriver(draft));
        verify(sysUserService, never()).updateSysUser(any(SysUser.class));
        verify(driverInformationService, never()).updateDriver(any(DriverInformation.class));
        verify(driverInformationService, never()).createDriver(any(DriverInformation.class));
        verify(vehicleInformationService, never()).reassignOwnerIdCard(any(), any(), any(), any());
    }

    @Test
    void createBindingShouldDemoteExistingVehiclePrimary() {
        TransactionSynchronizationManager.initSynchronization();

        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DriverVehicleSearchRepository searchRepository = Mockito.mock(DriverVehicleSearchRepository.class);
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DriverVehicleService service = new DriverVehicleService(
                driverVehicleMapper,
                driverInformationMapper,
                requestHistoryMapper,
                searchRepository,
                vehicleInformationMapper,
                kafkaTemplate,
                new ObjectMapper());

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(400L);
        when(driverInformationMapper.selectById(400L)).thenReturn(driver);

        VehicleInformation vehicle = new VehicleInformation();
        vehicle.setVehicleId(401L);
        when(vehicleInformationMapper.selectById(401L)).thenReturn(vehicle);

        DriverVehicle existingVehiclePrimary = new DriverVehicle();
        existingVehiclePrimary.setId(402L);
        existingVehiclePrimary.setDriverId(499L);
        existingVehiclePrimary.setVehicleId(401L);
        existingVehiclePrimary.setIsPrimary(true);

        when(driverVehicleMapper.selectList(any()))
                .thenReturn(List.of())
                .thenReturn(List.of())
                .thenReturn(List.of(existingVehiclePrimary));
        when(driverVehicleMapper.insert(any(DriverVehicle.class))).thenReturn(1);

        DriverVehicle request = new DriverVehicle();
        request.setDriverId(400L);
        request.setVehicleId(401L);
        request.setIsPrimary(true);

        service.createBinding(request);

        ArgumentCaptor<DriverVehicle> captor = ArgumentCaptor.forClass(DriverVehicle.class);
        verify(driverVehicleMapper).updateById(captor.capture());
        assertEquals(false, captor.getValue().getIsPrimary());
        verify(driverVehicleMapper).insert(any(DriverVehicle.class));
    }

    @Test
    void checkAndInsertDriverVehicleIdempotencyShouldPopulateRequestHistoryMetadata() {
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DriverVehicleSearchRepository searchRepository = Mockito.mock(DriverVehicleSearchRepository.class);
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DriverVehicleService service = new DriverVehicleService(
                driverVehicleMapper,
                driverInformationMapper,
                requestHistoryMapper,
                searchRepository,
                vehicleInformationMapper,
                kafkaTemplate,
                new ObjectMapper());

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/vehicles/401/drivers");
        request.addHeader("X-Forwarded-For", "203.0.113.41");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));

        DriverVehicle binding = new DriverVehicle();
        binding.setDriverId(400L);
        binding.setVehicleId(401L);
        binding.setRelationship("OWNER");
        binding.setIsPrimary(true);

        service.checkAndInsertIdempotency("binding-key", binding, "create");

        ArgumentCaptor<SysRequestHistory> captor = ArgumentCaptor.forClass(SysRequestHistory.class);
        verify(requestHistoryMapper).insert(captor.capture());
        SysRequestHistory history = captor.getValue();
        assertEquals("POST", history.getRequestMethod());
        assertEquals("/api/vehicles/401/drivers", history.getRequestUrl());
        assertEquals("DRIVER_VEHICLE_CREATE", history.getBusinessType());
        assertEquals("PROCESSING", history.getBusinessStatus());
        assertEquals("203.0.113.41", history.getRequestIp());
        assertTrue(history.getRequestParams().contains("driverId=400"));
        assertTrue(history.getRequestParams().contains("vehicleId=401"));
    }

    @Test
    void updateUserRoleBindingShouldRejectManualMutation() {
        SysUserRoleMapper sysUserRoleMapper = Mockito.mock(SysUserRoleMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysUserRoleSearchRepository searchRepository = Mockito.mock(SysUserRoleSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        SysUserRoleService service = new SysUserRoleService(
                sysUserRoleMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        SysUserRole request = new SysUserRole();
        request.setId(801L);
        request.setUserId(10L);
        request.setRoleId(20);

        assertThrows(IllegalStateException.class, () -> service.updateRelation(request));
        verify(sysUserRoleMapper, never()).updateById(any(SysUserRole.class));
    }

    @Test
    void updateRolePermissionBindingShouldRejectManualMutation() {
        SysRolePermissionMapper sysRolePermissionMapper = Mockito.mock(SysRolePermissionMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysRolePermissionSearchRepository searchRepository = Mockito.mock(SysRolePermissionSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        SysRolePermissionService service = new SysRolePermissionService(
                sysRolePermissionMapper,
                requestHistoryMapper,
                searchRepository,
                kafkaTemplate,
                new ObjectMapper());

        SysRolePermission request = new SysRolePermission();
        request.setId(901L);
        request.setRoleId(20);
        request.setPermissionId(30);

        assertThrows(IllegalStateException.class, () -> service.updateRelation(request));
        verify(sysRolePermissionMapper, never()).updateById(any(SysRolePermission.class));
    }

    @Test
    void registerUserShouldMarkHistorySuccessAfterRoleAssignment() {
        TokenProvider tokenProvider = Mockito.mock(TokenProvider.class);
        AuditLoginLogService auditLoginLogService = Mockito.mock(AuditLoginLogService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        SysRoleService sysRoleService = Mockito.mock(SysRoleService.class);
        SysUserRoleService sysUserRoleService = Mockito.mock(SysUserRoleService.class);

        AuthWsService service = new AuthWsService(
                tokenProvider,
                auditLoginLogService,
                sysUserService,
                sysRoleService,
                sysUserRoleService);

        AuthWsService.RegisterRequest request = new AuthWsService.RegisterRequest();
        request.setUsername("new-user");
        request.setPassword("secret");
        request.setIdempotencyKey("register-key");

        when(sysUserService.isUsernameExists("new-user")).thenReturn(false);
        when(sysUserService.shouldSkipProcessing("register-key")).thenReturn(false);

        SysUser savedUser = new SysUser();
        savedUser.setUserId(88L);
        savedUser.setUsername("new-user");
        when(sysUserService.findByUsername("new-user")).thenReturn(savedUser);

        SysRole role = new SysRole();
        role.setRoleId(9);
        role.setRoleCode("USER");
        when(sysRoleService.findByRoleCode("USER")).thenReturn(role);

        assertEquals("CREATED", service.registerUser(request));

        verify(sysUserService).checkAndInsertIdempotency(eq("register-key"), any(SysUser.class), eq("create"));
        verify(sysUserService).createSysUser(any(SysUser.class));
        verify(sysUserRoleService).createRelation(any(SysUserRole.class));
        verify(sysUserService).markHistorySuccess("register-key", 88L);
        verify(sysUserService, never()).markHistoryFailure(any(), any());

        var inOrder = Mockito.inOrder(sysUserService, sysUserRoleService);
        inOrder.verify(sysUserService).createSysUser(any(SysUser.class));
        inOrder.verify(sysUserRoleService).createRelation(any(SysUserRole.class));
        inOrder.verify(sysUserService).markHistorySuccess("register-key", 88L);
    }

    @Test
    void registerUserShouldAcknowledgeCompletedIdempotentReplayBeforeUsernameConflict() {
        TokenProvider tokenProvider = Mockito.mock(TokenProvider.class);
        AuditLoginLogService auditLoginLogService = Mockito.mock(AuditLoginLogService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        SysRoleService sysRoleService = Mockito.mock(SysRoleService.class);
        SysUserRoleService sysUserRoleService = Mockito.mock(SysUserRoleService.class);

        AuthWsService service = new AuthWsService(
                tokenProvider,
                auditLoginLogService,
                sysUserService,
                sysRoleService,
                sysUserRoleService);

        AuthWsService.RegisterRequest request = new AuthWsService.RegisterRequest();
        request.setUsername("new-user");
        request.setPassword("secret");
        request.setIdempotencyKey("register-key");

        when(sysUserService.shouldSkipProcessing("register-key")).thenReturn(true);

        assertEquals("CREATED", service.registerUser(request));

        verify(sysUserService, never()).isUsernameExists(any());
        verify(sysUserService, never()).checkAndInsertIdempotency(any(), any(SysUser.class), any());
        verify(sysUserService, never()).createSysUser(any(SysUser.class));
        verify(sysUserRoleService, never()).createRelation(any(SysUserRole.class));
    }

    @Test
    void countByReviewLevelShouldFallBackToDatabaseWhenSearchIndexIsEmpty() {
        AppealReviewMapper appealReviewMapper = Mockito.mock(AppealReviewMapper.class);
        SysRequestHistoryMapper sysRequestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AppealReviewSearchRepository appealReviewSearchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        ObjectMapper objectMapper = new ObjectMapper();

        AppealReviewService service = new AppealReviewService(
                appealReviewMapper,
                sysRequestHistoryMapper,
                appealReviewSearchRepository,
                appealRecordService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                paymentRecordService,
                sysUserService,
                kafkaTemplate,
                objectMapper);

        @SuppressWarnings("unchecked")
        SearchHits<com.tutict.finalassignmentbackend.entity.elastic.AppealReviewDocument> emptyHits =
                Mockito.mock(SearchHits.class);
        when(emptyHits.getTotalHits()).thenReturn(0L);
        when(appealReviewSearchRepository.findByReviewLevel(eq("Final"), any()))
                .thenReturn(emptyHits);
        when(appealReviewMapper.selectCount(any(QueryWrapper.class))).thenReturn(3L);

        assertEquals(3L, service.countByReviewLevel("Final"));

        verify(appealReviewMapper).selectCount(any(QueryWrapper.class));
    }

    @Test
    void refreshTokenShouldReturnRefreshedAuthenticationPayload() {
        TokenProvider tokenProvider = Mockito.mock(TokenProvider.class);
        AuditLoginLogService auditLoginLogService = Mockito.mock(AuditLoginLogService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        SysRoleService sysRoleService = Mockito.mock(SysRoleService.class);
        SysUserRoleService sysUserRoleService = Mockito.mock(SysUserRoleService.class);

        AuthWsService service = new AuthWsService(
                tokenProvider,
                auditLoginLogService,
                sysUserService,
                sysRoleService,
                sysUserRoleService);

        SysUser user = new SysUser();
        user.setUserId(42L);
        user.setUsername("tester");
        user.setRealName("Tester");

        SysUserRole relation = new SysUserRole();
        relation.setRoleId(7);

        SysRole role = new SysRole();
        role.setRoleId(7);
        role.setRoleCode("USER");
        role.setRoleName("USER");
        role.setRoleType(RoleType.CUSTOM.getCode());
        role.setDataScope(DataScope.SELF.getCode());

        when(tokenProvider.validateToken("refresh-token")).thenReturn(true);
        when(tokenProvider.isRefreshToken("refresh-token")).thenReturn(true);
        when(tokenProvider.getUsernameFromToken("refresh-token")).thenReturn("tester");
        when(sysUserService.findByUsername("tester")).thenReturn(user);
        when(sysUserRoleService.findByUserId(42L, 1, 100)).thenReturn(List.of(relation));
        when(sysRoleService.findById(7)).thenReturn(role);
        when(tokenProvider.validateRoleClaims("USER", RoleType.CUSTOM.getCode(), DataScope.SELF.getCode()))
                .thenReturn(true);
        when(tokenProvider.createEnhancedToken("tester", "USER", RoleType.CUSTOM.getCode(), DataScope.SELF.getCode()))
                .thenReturn("new-jwt");
        when(tokenProvider.createRefreshToken("tester")).thenReturn("new-refresh");
        when(tokenProvider.hasSystemRole("new-jwt")).thenReturn(false);
        when(tokenProvider.hasBusinessRole("new-jwt")).thenReturn(false);
        when(tokenProvider.hasDataScopePermission("new-jwt", DataScope.DEPARTMENT)).thenReturn(false);

        Map<String, Object> payload = service.refreshToken("refresh-token");

        assertEquals("new-jwt", payload.get("jwtToken"));
        assertEquals("new-refresh", payload.get("refreshToken"));
        assertEquals(List.of("USER"), payload.get("roleCodes"));
        assertEquals(DataScope.SELF.getCode(), payload.get("dataScope"));
    }

    @Test
    void refreshTokenShouldRejectAccessTokens() {
        TokenProvider tokenProvider = Mockito.mock(TokenProvider.class);
        AuditLoginLogService auditLoginLogService = Mockito.mock(AuditLoginLogService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        SysRoleService sysRoleService = Mockito.mock(SysRoleService.class);
        SysUserRoleService sysUserRoleService = Mockito.mock(SysUserRoleService.class);

        AuthWsService service = new AuthWsService(
                tokenProvider,
                auditLoginLogService,
                sysUserService,
                sysRoleService,
                sysUserRoleService);

        when(tokenProvider.validateToken("access-token")).thenReturn(true);
        when(tokenProvider.isRefreshToken("access-token")).thenReturn(false);

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> service.refreshToken("access-token"));

        assertEquals("Unsupported token type for refresh.", ex.getMessage());
        verify(sysUserService, never()).findByUsername(any());
    }

    @Test
    void workflowControllerShouldRejectDirectAppealFinalDecisionEvents() {
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);

        WorkflowController controller = new WorkflowController(
                stateMachineService,
                offenseRecordService,
                paymentRecordService,
                appealRecordService);

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(12L);
        appealRecord.setProcessStatus(AppealProcessState.UNDER_REVIEW.getCode());
        when(appealRecordService.getAppealById(12L)).thenReturn(appealRecord);

        ResponseEntity<AppealRecord> response =
                controller.triggerAppealEvent(12L, AppealProcessEvent.APPROVE);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals(appealRecord, response.getBody());
        verify(stateMachineService, never()).processAppealState(any(), any(), any());
        verify(appealRecordService, never()).updateProcessStatus(any(), any());
    }

    @Test
    void workflowControllerShouldRejectDerivedOffenseAppealEvents() {
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);

        WorkflowController controller = new WorkflowController(
                stateMachineService,
                offenseRecordService,
                paymentRecordService,
                appealRecordService);

        OffenseRecord offenseRecord = new OffenseRecord();
        offenseRecord.setOffenseId(21L);
        offenseRecord.setProcessStatus(OffenseProcessState.PROCESSED.getCode());
        when(offenseRecordService.findById(21L)).thenReturn(offenseRecord);

        ResponseEntity<OffenseRecord> response =
                controller.triggerOffenseEvent(21L, OffenseProcessEvent.SUBMIT_APPEAL);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals(offenseRecord, response.getBody());
        verify(stateMachineService, never()).processOffenseState(any(), any(), any());
        verify(offenseRecordService, never()).updateProcessStatus(any(), any());
    }

    @Test
    void workflowControllerShouldRejectDirectPaymentWaiveEvent() {
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);

        WorkflowController controller = new WorkflowController(
                stateMachineService,
                offenseRecordService,
                paymentRecordService,
                appealRecordService);

        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setPaymentId(31L);
        paymentRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(paymentRecordService.findById(31L)).thenReturn(paymentRecord);

        ResponseEntity<PaymentRecord> response =
                controller.triggerPaymentEvent(31L, PaymentEvent.WAIVE_FINE);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals(paymentRecord, response.getBody());
        verify(stateMachineService, never()).processPaymentState(any(), any(), any());
        verify(paymentRecordService, never()).transitionPaymentStatus(any(), any());
        verify(paymentRecordService, never()).updatePaymentStatus(any(), any());
    }

    @Test
    void workflowControllerShouldRejectSelfServiceAppealAcceptanceEvents() {
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);

        WorkflowController controller = new WorkflowController(
                stateMachineService,
                offenseRecordService,
                paymentRecordService,
                appealRecordService);

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(41L);
        appealRecord.setAcceptanceStatus(AppealAcceptanceState.NEED_SUPPLEMENT.getCode());
        when(appealRecordService.getAppealById(41L)).thenReturn(appealRecord);

        ResponseEntity<AppealRecord> response =
                controller.triggerAppealAcceptanceEvent(41L, AppealAcceptanceEvent.SUPPLEMENT_COMPLETE, null);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals(appealRecord, response.getBody());
        verify(stateMachineService, never()).processAppealAcceptanceState(any(), any(), any());
        verify(appealRecordService, never()).updateAcceptanceStatus(any(), any());
    }

    @Test
    void workflowControllerShouldUsePaymentTransitionServiceForAllowedEvents() {
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);

        WorkflowController controller = new WorkflowController(
                stateMachineService,
                offenseRecordService,
                paymentRecordService,
                appealRecordService);

        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setPaymentId(32L);
        paymentRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(paymentRecordService.findById(32L)).thenReturn(paymentRecord);
        when(stateMachineService.processPaymentState(32L, PaymentState.UNPAID, PaymentEvent.COMPLETE_PAYMENT))
                .thenReturn(PaymentState.PAID);

        PaymentRecord updatedRecord = new PaymentRecord();
        updatedRecord.setPaymentId(32L);
        updatedRecord.setPaymentStatus(PaymentState.PAID.getCode());
        when(paymentRecordService.updatePaymentStatus(32L, PaymentState.PAID)).thenReturn(updatedRecord);

        ResponseEntity<PaymentRecord> response =
                controller.triggerPaymentEvent(32L, PaymentEvent.COMPLETE_PAYMENT);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(updatedRecord, response.getBody());
        verify(paymentRecordService).updatePaymentStatus(32L, PaymentState.PAID);
        verify(paymentRecordService, never()).transitionPaymentStatus(any(), any());
    }

    @Test
    void listCurrentUserProgressShouldNotRequireIdCardForBaseHistory() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber())
                .thenThrow(new IllegalStateException("Current user profile has no ID card number"));
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of());

        SysRequestHistory history = new SysRequestHistory();
        history.setId(501L);
        when(sysRequestHistoryService.findByUserId(42L, 1, 100)).thenReturn(List.of(history));
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200))).thenReturn(List.of());

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(List.of(history), response.getBody());
        verify(paymentRecordService, never()).findIdsByPayerIdCardAndFineIds(any(), any());
        verify(currentUserTrafficSupportService, never()).listCurrentUserVehicleIds();
    }

    @Test
    void listCurrentUserProgressShouldIncludeAppealReviewHistoriesLinkedByAppealId() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber())
                .thenThrow(new IllegalStateException("Current user profile has no ID card number"));

        AppealRecord appealRecord = new AppealRecord();
        appealRecord.setAppealId(501L);
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of(appealRecord));
        when(currentUserTrafficSupportService.listCurrentUserAppeals(2, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of());

        when(sysRequestHistoryService.findByUserId(42L, 1, 100)).thenReturn(List.of());
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200))).thenReturn(List.of());

        SysRequestHistory reviewHistory = new SysRequestHistory();
        reviewHistory.setId(9001L);
        reviewHistory.setBusinessType("APPEAL_REVIEW_CREATE");
        reviewHistory.setBusinessId(7001L);
        reviewHistory.setRequestUrl("/api/appeals/501/reviews");
        reviewHistory.setRequestParams("appealId=501,reviewLevel=FIRST");
        reviewHistory.setUpdatedAt(LocalDateTime.of(2026, 1, 6, 10, 0));
        when(sysRequestHistoryService.searchByRequestUrlPrefix("/api/appeals/501/reviews", 1, 200))
                .thenReturn(List.of(reviewHistory));
        when(sysRequestHistoryService.searchByRequestUrlPrefix("/api/appeals/501/reviews", 2, 200))
                .thenReturn(List.of());

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(1, response.getBody().size());
        assertEquals(9001L, response.getBody().get(0).getId());
    }

    @Test
    void listCurrentUserProgressShouldFilterByAppealId() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);

        AppealRecord firstAppeal = new AppealRecord();
        firstAppeal.setAppealId(501L);
        AppealRecord secondAppeal = new AppealRecord();
        secondAppeal.setAppealId(502L);
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of(firstAppeal, secondAppeal));
        when(currentUserTrafficSupportService.listCurrentUserAppeals(2, 100)).thenReturn(List.of());

        SysRequestHistory targetAppealHistory = new SysRequestHistory();
        targetAppealHistory.setId(9101L);
        targetAppealHistory.setBusinessType("APPEAL_CREATE");
        targetAppealHistory.setBusinessId(501L);
        targetAppealHistory.setUpdatedAt(LocalDateTime.of(2026, 1, 7, 10, 0));

        SysRequestHistory otherAppealHistory = new SysRequestHistory();
        otherAppealHistory.setId(9102L);
        otherAppealHistory.setBusinessType("APPEAL_CREATE");
        otherAppealHistory.setBusinessId(502L);
        otherAppealHistory.setUpdatedAt(LocalDateTime.of(2026, 1, 8, 10, 0));

        when(sysRequestHistoryService.findByUserId(42L, 1, 100))
                .thenReturn(List.of(targetAppealHistory, otherAppealHistory));
        when(sysRequestHistoryService.findByUserId(42L, 2, 100)).thenReturn(List.of());

        SysRequestHistory managerHistory = new SysRequestHistory();
        managerHistory.setId(9103L);
        managerHistory.setBusinessType("APPEAL_ACCEPTANCE_TRANSITION");
        managerHistory.setBusinessId(501L);
        managerHistory.setUpdatedAt(LocalDateTime.of(2026, 1, 9, 10, 0));
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200))).thenReturn(List.of(managerHistory));

        SysRequestHistory reviewHistory = new SysRequestHistory();
        reviewHistory.setId(9104L);
        reviewHistory.setBusinessType("APPEAL_REVIEW_CREATE");
        reviewHistory.setBusinessId(7001L);
        reviewHistory.setRequestUrl("/api/appeals/501/reviews");
        reviewHistory.setRequestParams("appealId=501");
        reviewHistory.setUpdatedAt(LocalDateTime.of(2026, 1, 10, 10, 0));
        when(sysRequestHistoryService.searchByRequestUrlPrefix("/api/appeals/501/reviews", 1, 200))
                .thenReturn(List.of(reviewHistory));
        when(sysRequestHistoryService.searchByRequestUrlPrefix("/api/appeals/501/reviews", 2, 200))
                .thenReturn(List.of());

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, 501L);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(List.of(reviewHistory, managerHistory, targetAppealHistory), response.getBody());
        verify(currentUserTrafficSupportService, never()).getCurrentUserIdCardNumber();
        verify(currentUserTrafficSupportService, never()).listCurrentUserFineIds();
        verify(currentUserTrafficSupportService, never()).listCurrentUserOffenseIds();
        verify(currentUserTrafficSupportService, never()).listCurrentUserDeductionIds();
        verify(currentUserTrafficSupportService, never()).listCurrentUserVehicleIds();
        verify(paymentRecordService, never()).findIdsByPayerIdCardAndFineIds(any(), any());
    }

    @Test
    void listCurrentUserProgressShouldRejectAppealIdOutsideCurrentUserScope() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, 999L);

        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        verify(sysRequestHistoryService, never()).findByUserId(any(), anyInt(), anyInt());
        verify(sysRequestHistoryService, never()).findByBusinessIds(any(), anyInt(), anyInt());
        verify(sysRequestHistoryService, never()).searchByRequestUrlPrefix(any(), anyInt(), anyInt());
    }

    @Test
    void listCurrentUserProgressShouldReturnConflictWhenProfileHasNoIdCardNumber() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber())
                .thenThrow(new IllegalStateException("Current user profile has no ID card number"));
        when(currentUserTrafficSupportService.listCurrentUserFineIds())
                .thenThrow(new IllegalStateException("Current user profile has no ID card number"));

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
    }

    @Test
    void createPaymentRecordShouldMarkPartialWhenPaymentDoesNotClearFine() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(100));
        fineRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);
        when(paymentRecordMapper.insert(any(PaymentRecord.class))).thenReturn(1);
        when(paymentRecordMapper.selectList(any())).thenAnswer(invocation -> {
            PaymentRecord stored = new PaymentRecord();
            stored.setPaymentId(902L);
            stored.setFineId(901L);
            stored.setPaymentAmount(BigDecimal.valueOf(30));
            stored.setPaymentStatus(PaymentState.PARTIAL.getCode());
            stored.setRefundAmount(BigDecimal.ZERO);
            return List.of(stored);
        });
        when(fineRecordService.updateFineRecordSystemManaged(any(FineRecord.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        PaymentRecord draft = new PaymentRecord();
        draft.setFineId(901L);
        draft.setPaymentAmount(BigDecimal.valueOf(30));
        draft.setPayerName("Carol Driver");
        draft.setPayerIdCard("110101199001010033");

        PaymentRecord created = service.createPaymentRecord(draft);

        assertEquals(PaymentState.PARTIAL.getCode(), created.getPaymentStatus());
        ArgumentCaptor<FineRecord> fineCaptor = ArgumentCaptor.forClass(FineRecord.class);
        verify(fineRecordService).updateFineRecordSystemManaged(fineCaptor.capture());
        assertEquals(PaymentState.PARTIAL.getCode(), fineCaptor.getValue().getPaymentStatus());
        assertEquals(BigDecimal.valueOf(30), fineCaptor.getValue().getPaidAmount());
        assertEquals(BigDecimal.valueOf(70), fineCaptor.getValue().getUnpaidAmount());
    }

    @Test
    void createPaymentRecordShouldKeepSelfServiceAppPaymentUnpaidUntilConfirmed() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(100));
        fineRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);
        when(paymentRecordMapper.insert(any(PaymentRecord.class))).thenReturn(1);
        when(paymentRecordMapper.selectList(any())).thenAnswer(invocation -> {
            PaymentRecord stored = new PaymentRecord();
            stored.setPaymentId(902L);
            stored.setFineId(901L);
            stored.setPaymentAmount(BigDecimal.valueOf(30));
            stored.setPaymentStatus(PaymentState.UNPAID.getCode());
            stored.setPaymentChannel("APP");
            stored.setRefundAmount(BigDecimal.ZERO);
            return List.of(stored);
        });
        when(fineRecordService.updateFineRecordSystemManaged(any(FineRecord.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        PaymentRecord draft = new PaymentRecord();
        draft.setFineId(901L);
        draft.setPaymentAmount(BigDecimal.valueOf(30));
        draft.setPayerName("Carol Driver");
        draft.setPayerIdCard("110101199001010033");
        draft.setPaymentChannel("APP");
        draft.setRemarks("Current user self-service payment");

        PaymentRecord created = service.createPaymentRecord(draft);

        assertEquals(PaymentState.UNPAID.getCode(), created.getPaymentStatus());
        assertNull(created.getTransactionId());
        assertNull(created.getReceiptNumber());
        ArgumentCaptor<FineRecord> fineCaptor = ArgumentCaptor.forClass(FineRecord.class);
        verify(fineRecordService).updateFineRecordSystemManaged(fineCaptor.capture());
        assertEquals(PaymentState.UNPAID.getCode(), fineCaptor.getValue().getPaymentStatus());
        assertEquals(BigDecimal.ZERO, fineCaptor.getValue().getPaidAmount());
        assertEquals(BigDecimal.valueOf(100), fineCaptor.getValue().getUnpaidAmount());
    }

    @Test
    void updateSelfServicePaymentConfirmationDetailsShouldRequireTransactionId() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        assertThrows(IllegalArgumentException.class,
                () -> service.updateSelfServicePaymentConfirmationDetails(902L, "   ", null));
        verify(paymentRecordMapper, never()).selectById(any());
    }

    @Test
    void updateSelfServicePaymentConfirmationDetailsShouldPersistTransactionIdAndReceiptUrl() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord existing = new PaymentRecord();
        existing.setPaymentId(902L);
        existing.setFineId(901L);
        existing.setPaymentChannel("APP");
        existing.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(paymentRecordMapper.selectById(902L)).thenReturn(existing);
        when(paymentRecordMapper.update(any(PaymentRecord.class), any(UpdateWrapper.class))).thenReturn(1);

        PaymentRecord updated = service.updateSelfServicePaymentConfirmationDetails(
                902L,
                "WX-20260410-0001",
                "https://example.com/proof/902");

        assertEquals("WX-20260410-0001", updated.getTransactionId());
        assertEquals("https://example.com/proof/902", updated.getReceiptUrl());
        assertNotNull(updated.getReceiptNumber());
        verify(paymentRecordMapper).update(any(PaymentRecord.class), any(UpdateWrapper.class));
    }

    @Test
    void confirmSelfServicePaymentShouldPersistConfirmationAndFinalStatusInSinglePaymentLoad() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord existing = new PaymentRecord();
        existing.setPaymentId(902L);
        existing.setFineId(901L);
        existing.setPaymentAmount(BigDecimal.valueOf(100));
        existing.setRefundAmount(BigDecimal.ZERO);
        existing.setPaymentChannel("APP");
        existing.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(paymentRecordMapper.selectById(902L)).thenReturn(existing);
        when(paymentRecordMapper.selectCount(any(QueryWrapper.class))).thenReturn(0L);
        when(paymentRecordMapper.update(any(PaymentRecord.class), any(UpdateWrapper.class))).thenReturn(1);
        when(paymentRecordMapper.selectList(any(QueryWrapper.class))).thenReturn(List.of(existing));

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);

        when(stateMachineService.canTransitionPaymentState(any(), any())).thenReturn(true);
        when(stateMachineService.processPaymentState(902L, PaymentState.UNPAID, PaymentEvent.COMPLETE_PAYMENT))
                .thenReturn(PaymentState.PAID);

        PaymentRecord updated = service.confirmSelfServicePayment(
                902L,
                "WX-20260410-0001",
                "https://example.com/proof/902",
                PaymentState.PAID);

        assertEquals(PaymentState.PAID.getCode(), updated.getPaymentStatus());
        assertEquals("WX-20260410-0001", updated.getTransactionId());
        assertEquals("https://example.com/proof/902", updated.getReceiptUrl());
        verify(paymentRecordMapper, Mockito.times(1)).selectById(902L);
        verify(paymentRecordMapper, Mockito.times(1)).update(any(PaymentRecord.class), any(UpdateWrapper.class));
        verify(fineRecordService, Mockito.times(1)).findById(901L);
        verify(fineRecordService).updateFineRecordSystemManaged(any(FineRecord.class));
    }

    @Test
    void recordFinanceReviewShouldAppendStructuredAuditRemark() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("finance", "n/a", Collections.emptyList()));

        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setPaymentId(902L);
        paymentRecord.setFineId(901L);
        paymentRecord.setPaymentChannel("APP");
        paymentRecord.setPaymentStatus(PaymentState.PAID.getCode());
        paymentRecord.setRemarks("Current user self-service payment");
        when(paymentRecordMapper.selectById(902L)).thenReturn(paymentRecord);

        PaymentRecord reviewed = service.recordFinanceReview(902L, "need_proof", "Please upload receipt\nsoon");

        assertEquals(902L, reviewed.getPaymentId());
        assertTrue(reviewed.getRemarks().contains("[FINANCE_REVIEW]|NEED_PROOF|finance|"));
        assertTrue(reviewed.getRemarks().contains("Please upload receipt soon"));
        assertEquals("finance", reviewed.getUpdatedBy());
        verify(paymentRecordMapper).updateById(paymentRecord);
    }

    @Test
    void updateSelfServicePaymentReceiptProofShouldPersistUpdatedReceiptUrl() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));

        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setPaymentId(902L);
        paymentRecord.setFineId(901L);
        paymentRecord.setPaymentChannel("APP");
        paymentRecord.setPaymentStatus(PaymentState.PAID.getCode());
        paymentRecord.setReceiptUrl("https://example.com/proof/old-902");
        when(paymentRecordMapper.selectById(902L)).thenReturn(paymentRecord);

        PaymentRecord updated = service.updateSelfServicePaymentReceiptProof(
                902L,
                "https://example.com/proof/new-902");

        assertEquals("https://example.com/proof/new-902", updated.getReceiptUrl());
        assertTrue(updated.getRemarks().contains("[USER_PROOF_UPLOAD]|"));
        assertEquals("driver", updated.getUpdatedBy());
        verify(paymentRecordMapper).updateById(paymentRecord);
    }

    @Test
    void updateSelfServicePaymentConfirmationDetailsShouldRejectDuplicateTransactionId() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord existing = new PaymentRecord();
        existing.setPaymentId(902L);
        existing.setFineId(901L);
        existing.setPaymentChannel("APP");
        existing.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(paymentRecordMapper.selectById(902L)).thenReturn(existing);
        when(paymentRecordMapper.selectCount(any())).thenReturn(1L);

        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> service.updateSelfServicePaymentConfirmationDetails(
                        902L,
                        "WX-20260410-0001",
                        "https://example.com/proof/902"));

        assertEquals("Transaction ID is already used by another payment record", ex.getMessage());
        verify(paymentRecordMapper, never()).update(any(PaymentRecord.class), any(UpdateWrapper.class));
    }

    @Test
    void createPaymentRecordShouldRejectDuplicatePendingSelfServiceForSameFineAndPayer() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(100));
        fineRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);
        when(paymentRecordMapper.selectCount(any(QueryWrapper.class))).thenReturn(1L);

        PaymentRecord draft = new PaymentRecord();
        draft.setFineId(901L);
        draft.setPaymentAmount(BigDecimal.valueOf(30));
        draft.setPayerName("Carol Driver");
        draft.setPayerIdCard("110101199001010033");
        draft.setPaymentChannel("APP");

        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> service.createPaymentRecord(draft));

        assertEquals("A pending self-service payment order already exists for this fine and payer", ex.getMessage());
        verify(paymentRecordMapper, never()).insert(any(PaymentRecord.class));
    }

    @Test
    void updateSelfServicePaymentConfirmationDetailsShouldRejectWhenTransactionAlreadySetDifferently() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord existing = new PaymentRecord();
        existing.setPaymentId(902L);
        existing.setFineId(901L);
        existing.setPaymentChannel("APP");
        existing.setPaymentStatus(PaymentState.UNPAID.getCode());
        existing.setTransactionId("WX-20260410-0001");
        when(paymentRecordMapper.selectById(902L)).thenReturn(existing);
        when(paymentRecordMapper.selectCount(any(QueryWrapper.class))).thenReturn(0L);

        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> service.updateSelfServicePaymentConfirmationDetails(
                        902L,
                        "WX-20260410-0002",
                        "https://example.com/proof/902"));

        assertEquals("Transaction ID has already been set for this payment record", ex.getMessage());
        verify(paymentRecordMapper, never()).update(any(PaymentRecord.class), any(UpdateWrapper.class));
    }

    @Test
    void waiveAndRefundPaymentsByFineIdShouldProcessAllDatabaseBatches() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(501));
        fineRecord.setPaidAmount(BigDecimal.valueOf(501));
        fineRecord.setUnpaidAmount(BigDecimal.ZERO);
        fineRecord.setPaymentStatus(PaymentState.PAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);
        when(fineRecordService.updateFineRecordSystemManaged(any(FineRecord.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
        when(paymentRecordMapper.updateById(any(PaymentRecord.class))).thenReturn(1);

        java.util.List<PaymentRecord> firstBatch = new java.util.ArrayList<>();
        for (long paymentId = 1L; paymentId <= 500L; paymentId++) {
            firstBatch.add(buildPaidPaymentRecord(paymentId, 901L, BigDecimal.ONE));
        }
        PaymentRecord secondBatchRecord = buildPaidPaymentRecord(501L, 901L, BigDecimal.ONE);

        when(paymentRecordMapper.selectPage(any(Page.class), any(QueryWrapper.class))).thenAnswer(invocation -> {
            Page<PaymentRecord> page = invocation.getArgument(0);
            if (page.getCurrent() == 1L) {
                page.setRecords(firstBatch);
            } else if (page.getCurrent() == 2L) {
                page.setRecords(List.of(secondBatchRecord));
            } else {
                page.setRecords(List.of());
            }
            return page;
        });
        when(paymentRecordMapper.selectList(any(QueryWrapper.class))).thenAnswer(invocation -> {
            java.util.List<PaymentRecord> summaryRecords = new java.util.ArrayList<>(firstBatch);
            summaryRecords.add(secondBatchRecord);
            return summaryRecords;
        });

        service.waiveAndRefundPaymentsByFineId(901L, "Batch waive");

        verify(paymentRecordMapper, Mockito.times(2)).selectPage(any(Page.class), any(QueryWrapper.class));
        verify(paymentRecordMapper, Mockito.times(501)).updateById(any(PaymentRecord.class));
        verify(searchRepository, Mockito.never()).findByFineId(eq(901L), any());
        assertEquals(PaymentState.WAIVED.getCode(), firstBatch.get(0).getPaymentStatus());
        assertEquals(BigDecimal.ONE, firstBatch.get(0).getRefundAmount());
        assertEquals(PaymentState.WAIVED.getCode(), secondBatchRecord.getPaymentStatus());
        assertEquals(BigDecimal.ONE, secondBatchRecord.getRefundAmount());

        ArgumentCaptor<FineRecord> fineCaptor = ArgumentCaptor.forClass(FineRecord.class);
        verify(fineRecordService).updateFineRecordSystemManaged(fineCaptor.capture());
        assertEquals(PaymentState.WAIVED.getCode(), fineCaptor.getValue().getPaymentStatus());
        assertEquals(BigDecimal.ZERO, fineCaptor.getValue().getPaidAmount());
        assertEquals(BigDecimal.ZERO, fineCaptor.getValue().getUnpaidAmount());
    }

    @Test
    void createPaymentForCurrentUserShouldRejectWhenPendingSelfServicePaymentExists() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        currentUser.setUsername("driver");
        currentUser.setRealName("Carol Driver");
        currentUser.setIdCardNumber("110101199001010033");
        currentUser.setContactNumber("13800000000");
        when(sysUserService.findByUsername("driver")).thenReturn(currentUser);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(101L);
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        driver.setContactNumber("13800000000");
        when(driverInformationService.findLinkedDriverForUser(currentUser)).thenReturn(driver);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setOffenseId(701L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(100));
        fineRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);

        OffenseRecord offenseRecord = new OffenseRecord();
        offenseRecord.setOffenseId(701L);
        offenseRecord.setDriverId(101L);
        when(offenseRecordService.findById(701L)).thenReturn(offenseRecord);

        PaymentRecord pendingRecord = new PaymentRecord();
        pendingRecord.setPaymentId(902L);
        pendingRecord.setFineId(901L);
        pendingRecord.setPayerIdCard("110101199001010033");
        pendingRecord.setPaymentChannel("APP");
        pendingRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(paymentRecordService.findByFineIdAndPayerIdCard(901L, "110101199001010033", 1, 200))
                .thenReturn(List.of(pendingRecord));

        PaymentRecord draft = new PaymentRecord();
        draft.setFineId(901L);
        draft.setPaymentAmount(BigDecimal.valueOf(100));

        assertThrows(IllegalStateException.class, () -> service.createPaymentForCurrentUser(draft));
        verify(paymentRecordService, never()).createPaymentRecord(any(PaymentRecord.class));
    }

    @Test
    void createPaymentForCurrentUserShouldIgnoreExpiredPendingSelfServicePayment() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        currentUser.setUsername("driver");
        currentUser.setRealName("Carol Driver");
        currentUser.setIdCardNumber("110101199001010033");
        currentUser.setContactNumber("13800000000");
        when(sysUserService.findByUsername("driver")).thenReturn(currentUser);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(101L);
        driver.setName("Carol Driver");
        driver.setIdCardNumber("110101199001010033");
        driver.setContactNumber("13800000000");
        when(driverInformationService.findLinkedDriverForUser(currentUser)).thenReturn(driver);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setOffenseId(701L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(100));
        fineRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);

        OffenseRecord offenseRecord = new OffenseRecord();
        offenseRecord.setOffenseId(701L);
        offenseRecord.setDriverId(101L);
        when(offenseRecordService.findById(701L)).thenReturn(offenseRecord);

        PaymentRecord expiredPendingRecord = new PaymentRecord();
        expiredPendingRecord.setPaymentId(902L);
        expiredPendingRecord.setFineId(901L);
        expiredPendingRecord.setPayerIdCard("110101199001010033");
        expiredPendingRecord.setPaymentChannel("APP");
        expiredPendingRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        expiredPendingRecord.setCreatedAt(LocalDateTime.now().minusMinutes(20));
        when(paymentRecordService.findByFineIdAndPayerIdCard(901L, "110101199001010033", 1, 200))
                .thenReturn(List.of(expiredPendingRecord));

        PaymentRecord draft = new PaymentRecord();
        draft.setFineId(901L);
        draft.setPaymentAmount(BigDecimal.valueOf(100));

        PaymentRecord created = new PaymentRecord();
        created.setPaymentId(903L);
        when(paymentRecordService.createPaymentRecord(any(PaymentRecord.class))).thenReturn(created);

        PaymentRecord saved = service.createPaymentForCurrentUser(draft);

        assertEquals(903L, saved.getPaymentId());
        verify(paymentRecordService).createPaymentRecord(any(PaymentRecord.class));
    }

    @Test
    void confirmCurrentUserPaymentShouldTransitionPendingSelfServicePaymentToPaidWhenAmountClearsRemaining() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        currentUser.setUsername("driver");
        currentUser.setRealName("Carol Driver");
        currentUser.setIdCardNumber("110101199001010033");
        when(sysUserService.findByUsername("driver")).thenReturn(currentUser);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(101L);
        driver.setIdCardNumber("110101199001010033");
        when(driverInformationService.findLinkedDriverForUser(currentUser)).thenReturn(driver);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setOffenseId(701L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(100));
        fineRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);

        OffenseRecord offenseRecord = new OffenseRecord();
        offenseRecord.setOffenseId(701L);
        offenseRecord.setDriverId(101L);
        when(offenseRecordService.findById(701L)).thenReturn(offenseRecord);

        PaymentRecord pendingRecord = new PaymentRecord();
        pendingRecord.setPaymentId(902L);
        pendingRecord.setFineId(901L);
        pendingRecord.setPaymentAmount(BigDecimal.valueOf(100));
        pendingRecord.setPayerIdCard("110101199001010033");
        pendingRecord.setPaymentChannel("APP");
        pendingRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(paymentRecordService.findById(902L)).thenReturn(pendingRecord);

        PaymentRecord confirmedRecord = new PaymentRecord();
        confirmedRecord.setPaymentId(902L);
        confirmedRecord.setPaymentStatus(PaymentState.PAID.getCode());
        when(paymentRecordService.confirmSelfServicePayment(
                902L,
                "WX-20260410-0001",
                "https://example.com/proof/902",
                PaymentState.PAID)).thenReturn(confirmedRecord);

        PaymentRecord confirmationDraft = new PaymentRecord();
        confirmationDraft.setTransactionId("WX-20260410-0001");
        confirmationDraft.setReceiptUrl("https://example.com/proof/902");

        PaymentRecord confirmed = service.confirmCurrentUserPayment(902L, confirmationDraft);

        assertEquals(PaymentState.PAID.getCode(), confirmed.getPaymentStatus());
        verify(fineRecordService, Mockito.times(1)).findById(901L);
        verify(paymentRecordService).confirmSelfServicePayment(
                902L,
                "WX-20260410-0001",
                "https://example.com/proof/902",
                PaymentState.PAID);
    }

    @Test
    void confirmCurrentUserPaymentShouldRejectExpiredPendingSelfServicePayment() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        currentUser.setUsername("driver");
        currentUser.setRealName("Carol Driver");
        currentUser.setIdCardNumber("110101199001010033");
        when(sysUserService.findByUsername("driver")).thenReturn(currentUser);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(101L);
        driver.setIdCardNumber("110101199001010033");
        when(driverInformationService.findLinkedDriverForUser(currentUser)).thenReturn(driver);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setOffenseId(701L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.ZERO);
        fineRecord.setUnpaidAmount(BigDecimal.valueOf(100));
        fineRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);

        OffenseRecord offenseRecord = new OffenseRecord();
        offenseRecord.setOffenseId(701L);
        offenseRecord.setDriverId(101L);
        when(offenseRecordService.findById(701L)).thenReturn(offenseRecord);

        PaymentRecord expiredPendingRecord = new PaymentRecord();
        expiredPendingRecord.setPaymentId(902L);
        expiredPendingRecord.setFineId(901L);
        expiredPendingRecord.setPaymentAmount(BigDecimal.valueOf(100));
        expiredPendingRecord.setPayerIdCard("110101199001010033");
        expiredPendingRecord.setPaymentChannel("APP");
        expiredPendingRecord.setPaymentStatus(PaymentState.UNPAID.getCode());
        expiredPendingRecord.setCreatedAt(LocalDateTime.now().minusMinutes(20));
        when(paymentRecordService.findById(902L)).thenReturn(expiredPendingRecord);

        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> service.confirmCurrentUserPayment(902L, new PaymentRecord()));

        assertEquals("Pending self-service payment order has expired", ex.getMessage());
        verify(paymentRecordService, never()).confirmSelfServicePayment(any(), any(), any(), any());
    }

    @Test
    void updateCurrentUserPaymentProofShouldReuseOwnedFineValidationLoad() {
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        DriverInformationService driverInformationService = Mockito.mock(DriverInformationService.class);
        OffenseRecordService offenseRecordService = Mockito.mock(OffenseRecordService.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        DeductionRecordService deductionRecordService = Mockito.mock(DeductionRecordService.class);
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        CurrentUserTrafficSupportService service = new CurrentUserTrafficSupportService(
                sysUserService,
                driverInformationService,
                offenseRecordService,
                fineRecordService,
                deductionRecordService,
                vehicleInformationService,
                appealRecordService,
                paymentRecordService,
                stateMachineService);

        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("driver", "n/a", Collections.emptyList()));

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        currentUser.setUsername("driver");
        currentUser.setIdCardNumber("110101199001010033");
        when(sysUserService.findByUsername("driver")).thenReturn(currentUser);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(101L);
        driver.setIdCardNumber("110101199001010033");
        when(driverInformationService.findLinkedDriverForUser(currentUser)).thenReturn(driver);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setOffenseId(701L);
        fineRecord.setPaymentStatus(PaymentState.PARTIAL.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);

        OffenseRecord offenseRecord = new OffenseRecord();
        offenseRecord.setOffenseId(701L);
        offenseRecord.setDriverId(101L);
        when(offenseRecordService.findById(701L)).thenReturn(offenseRecord);

        PaymentRecord pendingRecord = new PaymentRecord();
        pendingRecord.setPaymentId(902L);
        pendingRecord.setFineId(901L);
        pendingRecord.setPayerIdCard("110101199001010033");
        pendingRecord.setPaymentChannel("APP");
        pendingRecord.setPaymentStatus(PaymentState.PAID.getCode());
        when(paymentRecordService.findById(902L)).thenReturn(pendingRecord);

        PaymentRecord updatedRecord = new PaymentRecord();
        updatedRecord.setPaymentId(902L);
        updatedRecord.setReceiptUrl("https://example.com/proof/new-902");
        when(paymentRecordService.updateSelfServicePaymentReceiptProof(pendingRecord, "https://example.com/proof/new-902"))
                .thenReturn(updatedRecord);

        PaymentRecord proofDraft = new PaymentRecord();
        proofDraft.setReceiptUrl("https://example.com/proof/new-902");

        PaymentRecord updated = service.updateCurrentUserPaymentProof(902L, proofDraft);

        assertEquals("https://example.com/proof/new-902", updated.getReceiptUrl());
        verify(fineRecordService, Mockito.times(1)).findById(901L);
        verify(paymentRecordService).updateSelfServicePaymentReceiptProof(
                pendingRecord,
                "https://example.com/proof/new-902");
    }

    @Test
    void listCurrentUserProgressShouldAggregateAcrossMultiplePages() {
        SysRequestHistoryService sysRequestHistoryService = Mockito.mock(SysRequestHistoryService.class);
        CurrentUserTrafficSupportService currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);

        ProgressItemController controller = new ProgressItemController(
                sysRequestHistoryService,
                currentUserTrafficSupportService,
                paymentRecordService);

        SysUser currentUser = new SysUser();
        currentUser.setUserId(42L);
        when(currentUserTrafficSupportService.requireCurrentUser()).thenReturn(currentUser);
        when(currentUserTrafficSupportService.getCurrentUserIdCardNumber()).thenReturn("110101199001010033");

        SysRequestHistory historyPageOne = new SysRequestHistory();
        historyPageOne.setId(1001L);
        historyPageOne.setUpdatedAt(LocalDateTime.of(2026, 1, 2, 10, 0));
        SysRequestHistory historyPageTwo = new SysRequestHistory();
        historyPageTwo.setId(1002L);
        historyPageTwo.setUpdatedAt(LocalDateTime.of(2026, 1, 3, 10, 0));
        List<SysRequestHistory> firstUserHistoryPage = new java.util.ArrayList<>();
        firstUserHistoryPage.add(historyPageOne);
        for (int index = 0; index < 99; index++) {
            SysRequestHistory fillerHistory = new SysRequestHistory();
            fillerHistory.setId(1100L + index);
            firstUserHistoryPage.add(fillerHistory);
        }
        when(sysRequestHistoryService.findByUserId(42L, 1, 100)).thenReturn(firstUserHistoryPage);
        when(sysRequestHistoryService.findByUserId(42L, 2, 100)).thenReturn(List.of());

        when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 100)).thenReturn(List.of());
        List<Long> fineIds = new java.util.ArrayList<>();
        fineIds.add(2001L);
        for (int index = 0; index < 99; index++) {
            fineIds.add(3000L + index);
        }
        fineIds.add(2002L);
        when(currentUserTrafficSupportService.listCurrentUserFineIds()).thenReturn(fineIds);
        when(currentUserTrafficSupportService.listCurrentUserOffenseIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserDeductionIds()).thenReturn(List.of());
        when(currentUserTrafficSupportService.listCurrentUserVehicleIds()).thenReturn(List.of());
        when(paymentRecordService.findIdsByPayerIdCardAndFineIds(eq("110101199001010033"), any())).thenReturn(List.of());

        SysRequestHistory relatedHistoryPageOne = new SysRequestHistory();
        relatedHistoryPageOne.setId(1003L);
        relatedHistoryPageOne.setBusinessType("FINE_CREATE");
        relatedHistoryPageOne.setBusinessId(2001L);
        relatedHistoryPageOne.setUpdatedAt(LocalDateTime.of(2026, 1, 4, 10, 0));
        SysRequestHistory relatedHistoryPageTwo = new SysRequestHistory();
        relatedHistoryPageTwo.setId(1004L);
        relatedHistoryPageTwo.setBusinessType("FINE_CREATE");
        relatedHistoryPageTwo.setBusinessId(2002L);
        relatedHistoryPageTwo.setUpdatedAt(LocalDateTime.of(2026, 1, 5, 10, 0));
        when(sysRequestHistoryService.findRefundAudits(null, 2001L, null, 1, 100)).thenReturn(List.of());
        when(sysRequestHistoryService.findRefundAudits(null, 2002L, null, 1, 100)).thenReturn(List.of());
        List<SysRequestHistory> firstBusinessHistoryPage = new java.util.ArrayList<>();
        firstBusinessHistoryPage.add(relatedHistoryPageOne);
        for (int index = 0; index < 199; index++) {
            SysRequestHistory fillerHistory = new SysRequestHistory();
            fillerHistory.setId(4000L + index);
            fillerHistory.setBusinessType("IGNORED");
            fillerHistory.setBusinessId(9000L + index);
            firstBusinessHistoryPage.add(fillerHistory);
        }
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(1), eq(200)))
                .thenReturn(firstBusinessHistoryPage);
        when(sysRequestHistoryService.findByBusinessIds(any(), eq(2), eq(200))).thenReturn(List.of(relatedHistoryPageTwo));

        ResponseEntity<List<SysRequestHistory>> response = controller.listCurrentUserProgress(1, 20, null);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(20, response.getBody().size());
        assertTrue(response.getBody().stream().anyMatch(history -> Objects.equals(history.getId(), 1004L)));
        assertTrue(response.getBody().stream().anyMatch(history -> Objects.equals(history.getId(), 1003L)));
        verify(sysRequestHistoryService).findByBusinessIds(any(), eq(1), eq(200));
        verify(sysRequestHistoryService).findByBusinessIds(any(), eq(2), eq(200));
    }

    @Test
    void financeReadEndpointsShouldRemainAvailableForFineManagementAndViolationReview() throws Exception {
        assertRolesContain(
                DriverInformationController.class.getMethod("searchByName", String.class, int.class, int.class),
                "FINANCE");
        assertRolesContain(
                OffenseInformationController.class.getMethod("byDriver", Long.class, int.class, int.class),
                "FINANCE");
        assertRolesContain(
                OffenseInformationController.class.getMethod("byVehicle", Long.class, int.class, int.class),
                "FINANCE");
        assertRolesContain(
                VehicleInformationController.class.getMethod("searchByLicense", String.class),
                "FINANCE");
        assertRolesContain(
                VehicleInformationController.class.getMethod("globalPlateSuggestions", String.class, int.class),
                "FINANCE");
        assertRolesContain(TrafficViolationController.class, "FINANCE");
        assertRolesContain(TrafficViolationController.class, "APPEAL_REVIEWER");
        assertRolesContain(OffenseDetailsController.class, "FINANCE");
        assertRolesContain(OffenseDetailsController.class, "APPEAL_REVIEWER");
    }

    @Test
    void currentUserSelfServiceEndpointsShouldRemainUserOnly() throws Exception {
        assertRolesExactly(
                PaymentRecordController.class.getMethod(
                        "createCurrentUserPayment",
                        PaymentRecordController.CurrentUserPaymentCreateRequest.class,
                        String.class),
                "USER");
        assertRolesExactly(
                PaymentRecordController.class.getMethod("listCurrentUserPayments", int.class, int.class, Long.class),
                "USER");
        assertRolesExactly(
                PaymentRecordController.class.getMethod(
                        "confirmCurrentUserPayment",
                        Long.class,
                        PaymentRecordController.CurrentUserPaymentConfirmationRequest.class,
                        String.class),
                "USER");
        assertRolesExactly(
                PaymentRecordController.class.getMethod(
                        "updateCurrentUserPaymentProof",
                        Long.class,
                        PaymentRecordController.CurrentUserPaymentProofRequest.class,
                        String.class),
                "USER");
        assertRolesExactly(
                AppealManagementController.class.getMethod("listCurrentUserAppeals", int.class, int.class),
                "USER");
        assertRolesExactly(
                AppealManagementController.class.getMethod(
                        "createCurrentUserAppeal",
                        AppealManagementController.CurrentUserAppealCreateRequest.class,
                        String.class),
                "USER");
        assertRolesExactly(
                AppealManagementController.class.getMethod(
                        "triggerCurrentUserAppealAcceptanceEvent",
                        Long.class,
                        AppealAcceptanceEvent.class,
                        AppealManagementController.CurrentUserAppealSubmissionRequest.class),
                "USER");
        assertRolesExactly(
                AppealManagementController.class.getMethod(
                        "triggerCurrentUserAppealProcessEvent",
                        Long.class,
                        AppealProcessEvent.class),
                "USER");
        assertRolesExactly(
                ProgressItemController.class.getMethod("listCurrentUserProgress", int.class, int.class, Long.class),
                "USER");
    }

    @Test
    void paymentFinanceReviewEndpointShouldRemainFinanceVisible() throws Exception {
        assertRolesContain(PaymentRecordController.class, "FINANCE");
        assertRolesContain(PaymentRecordController.class, "ADMIN");
        assertRolesContain(PaymentRecordController.class, "SUPER_ADMIN");
    }

    @Test
    void transitionPaymentStatusShouldRejectManualWaiveTarget() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        PaymentRecord existing = new PaymentRecord();
        existing.setPaymentId(40L);
        when(paymentRecordMapper.selectById(40L)).thenReturn(existing);

        assertThrows(IllegalStateException.class, () -> service.transitionPaymentStatus(40L, PaymentState.WAIVED));
        verify(paymentRecordMapper).selectById(40L);
        verify(stateMachineService, never()).processPaymentState(any(), any(), any());
    }

    private void assertRolesContain(Method method, String expectedRole) {
        RolesAllowed rolesAllowed = method.getAnnotation(RolesAllowed.class);
        assertNotNull(rolesAllowed, "Missing @RolesAllowed on method: " + method);
        assertTrue(List.of(rolesAllowed.value()).contains(expectedRole),
                "Expected role " + expectedRole + " on method " + method);
    }

    private void assertRolesContain(Class<?> type, String expectedRole) {
        RolesAllowed rolesAllowed = type.getAnnotation(RolesAllowed.class);
        assertNotNull(rolesAllowed, "Missing @RolesAllowed on type: " + type.getName());
        assertTrue(List.of(rolesAllowed.value()).contains(expectedRole),
                "Expected role " + expectedRole + " on type " + type.getName());
    }

    private void assertRolesExactly(Method method, String... expectedRoles) {
        RolesAllowed rolesAllowed = method.getAnnotation(RolesAllowed.class);
        assertNotNull(rolesAllowed, "Missing @RolesAllowed on method: " + method);
        assertEquals(List.of(expectedRoles), List.of(rolesAllowed.value()),
                "Unexpected roles on method " + method);
    }

    private PaymentRecord buildFinanceReviewTaskRecord(Long paymentId,
                                                       String paymentChannel,
                                                       String paymentStatus,
                                                       String receiptUrl) {
        PaymentRecord record = new PaymentRecord();
        record.setPaymentId(paymentId);
        record.setPaymentChannel(paymentChannel);
        record.setPaymentStatus(paymentStatus);
        record.setReceiptUrl(receiptUrl);
        return record;
    }

    private PaymentRecord buildPaidPaymentRecord(Long paymentId, Long fineId, BigDecimal paymentAmount) {
        PaymentRecord record = new PaymentRecord();
        record.setPaymentId(paymentId);
        record.setFineId(fineId);
        record.setPaymentAmount(paymentAmount);
        record.setRefundAmount(BigDecimal.ZERO);
        record.setPaymentStatus(PaymentState.PAID.getCode());
        record.setPaymentTime(LocalDateTime.of(2026, 4, 12, 10, 0));
        return record;
    }

    @SuppressWarnings("unchecked")
    private ArgumentCaptor<Iterable<Long>> iterableLongCaptor() {
        return (ArgumentCaptor<Iterable<Long>>) (ArgumentCaptor<?>) ArgumentCaptor.forClass(Iterable.class);
    }
}
