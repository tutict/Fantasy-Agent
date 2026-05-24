package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.entity.AuditLoginLog;
import com.tutict.finalassignmentbackend.entity.AuditOperationLog;
import com.tutict.finalassignmentbackend.entity.AppealReview;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.DriverVehicle;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.OffenseTypeDict;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.entity.SysBackupRestore;
import com.tutict.finalassignmentbackend.entity.SysDict;
import com.tutict.finalassignmentbackend.entity.SysPermission;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysSettings;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.mapper.AppealRecordMapper;
import com.tutict.finalassignmentbackend.mapper.AppealReviewMapper;
import com.tutict.finalassignmentbackend.mapper.AuditLoginLogMapper;
import com.tutict.finalassignmentbackend.mapper.AuditOperationLogMapper;
import com.tutict.finalassignmentbackend.mapper.DeductionRecordMapper;
import com.tutict.finalassignmentbackend.mapper.DriverInformationMapper;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.FineRecordMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseTypeDictMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.PaymentRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysDictMapper;
import com.tutict.finalassignmentbackend.mapper.SysPermissionMapper;
import com.tutict.finalassignmentbackend.mapper.SysBackupRestoreMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.SysRoleMapper;
import com.tutict.finalassignmentbackend.mapper.SysSettingsMapper;
import com.tutict.finalassignmentbackend.mapper.SysUserMapper;
import com.tutict.finalassignmentbackend.mapper.VehicleInformationMapper;
import com.tutict.finalassignmentbackend.repository.AuditLoginLogSearchRepository;
import com.tutict.finalassignmentbackend.repository.AuditOperationLogSearchRepository;
import com.tutict.finalassignmentbackend.repository.AppealReviewSearchRepository;
import com.tutict.finalassignmentbackend.repository.DeductionRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.DriverInformationSearchRepository;
import com.tutict.finalassignmentbackend.repository.DriverVehicleSearchRepository;
import com.tutict.finalassignmentbackend.repository.FineRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.OffenseTypeDictSearchRepository;
import com.tutict.finalassignmentbackend.repository.OffenseInformationSearchRepository;
import com.tutict.finalassignmentbackend.repository.PaymentRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysBackupRestoreSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysDictSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysPermissionSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysRequestHistorySearchRepository;
import com.tutict.finalassignmentbackend.repository.SysRoleSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysSettingsSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysUserSearchRepository;
import com.tutict.finalassignmentbackend.repository.VehicleInformationSearchRepository;
import com.tutict.finalassignmentbackend.service.statemachine.StateMachineService;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.cache.CacheManager;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.PlatformTransactionManager;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class FindAllPaginationOptimizationTest {

    @Test
    void auditLoginLogFindAllShouldUsePagedFallback() {
        AuditLoginLogMapper mapper = Mockito.mock(AuditLoginLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditLoginLogSearchRepository repository = Mockito.mock(AuditLoginLogSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubAuditLoginLogPages(mapper);

        AuditLoginLogService service = new AuditLoginLogService(
                mapper,
                requestHistoryMapper,
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<AuditLoginLog> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void auditOperationLogFindAllShouldUsePagedFallback() {
        AuditOperationLogMapper mapper = Mockito.mock(AuditOperationLogMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        AuditOperationLogSearchRepository repository = Mockito.mock(AuditOperationLogSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubAuditOperationLogPages(mapper);

        AuditOperationLogService service = new AuditOperationLogService(
                mapper,
                requestHistoryMapper,
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<AuditOperationLog> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void offenseRecordFindAllShouldUsePagedFallback() {
        OffenseRecordMapper mapper = Mockito.mock(OffenseRecordMapper.class);
        OffenseInformationSearchRepository repository = Mockito.mock(OffenseInformationSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubOffenseRecordPages(mapper);

        OffenseRecordService service = new OffenseRecordService(
                mapper,
                Mockito.mock(FineRecordMapper.class),
                Mockito.mock(AppealRecordMapper.class),
                Mockito.mock(DeductionRecordMapper.class),
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(SysUserService.class),
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<OffenseRecord> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void paymentRecordFindAllShouldUsePagedFallback() {
        PaymentRecordMapper mapper = Mockito.mock(PaymentRecordMapper.class);
        PaymentRecordSearchRepository repository = Mockito.mock(PaymentRecordSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubPaymentRecordPages(mapper);

        PaymentRecordService service = new PaymentRecordService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(FineRecordService.class),
                Mockito.mock(SysUserService.class),
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper(),
                Mockito.mock(PlatformTransactionManager.class),
                Mockito.mock(StateMachineService.class)
        );

        List<PaymentRecord> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void driverInformationGetAllShouldUsePagedFallback() {
        DriverInformationMapper mapper = Mockito.mock(DriverInformationMapper.class);
        DriverInformationSearchRepository repository = Mockito.mock(DriverInformationSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubDriverInformationPages(mapper);

        DriverInformationService service = new DriverInformationService(
                mapper,
                Mockito.mock(DriverVehicleMapper.class),
                Mockito.mock(OffenseRecordMapper.class),
                Mockito.mock(DeductionRecordMapper.class),
                Mockito.mock(SysRequestHistoryMapper.class),
                Mockito.mock(KafkaTemplate.class),
                repository,
                new ObjectMapper()
        );

        List<DriverInformation> result = service.getAllDrivers();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void vehicleInformationGetAllShouldUsePagedFallback() {
        VehicleInformationMapper mapper = Mockito.mock(VehicleInformationMapper.class);
        VehicleInformationSearchRepository repository = Mockito.mock(VehicleInformationSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubVehicleInformationPages(mapper);

        VehicleInformationService service = new VehicleInformationService(
                mapper,
                Mockito.mock(DriverVehicleMapper.class),
                Mockito.mock(OffenseRecordMapper.class),
                Mockito.mock(SysRequestHistoryMapper.class),
                Mockito.mock(KafkaTemplate.class),
                repository
        );

        List<VehicleInformation> result = service.getAllVehicleInformation();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void sysRequestHistoryFindAllShouldUsePagedFallback() {
        SysRequestHistoryMapper mapper = Mockito.mock(SysRequestHistoryMapper.class);
        SysRequestHistorySearchRepository repository = Mockito.mock(SysRequestHistorySearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubSysRequestHistoryPages(mapper);

        SysRequestHistoryService service = new SysRequestHistoryService(
                mapper,
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<SysRequestHistory> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void offenseTypeDictFindAllShouldUsePagedFallback() {
        OffenseTypeDictMapper mapper = Mockito.mock(OffenseTypeDictMapper.class);
        OffenseTypeDictSearchRepository repository = Mockito.mock(OffenseTypeDictSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubOffenseTypeDictPages(mapper);

        OffenseTypeDictService service = new OffenseTypeDictService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<OffenseTypeDict> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void sysDictFindAllShouldUsePagedFallback() {
        SysDictMapper mapper = Mockito.mock(SysDictMapper.class);
        SysDictSearchRepository repository = Mockito.mock(SysDictSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubSysDictPages(mapper);

        SysDictService service = new SysDictService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<SysDict> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void sysPermissionFindAllShouldUsePagedFallback() {
        SysPermissionMapper mapper = Mockito.mock(SysPermissionMapper.class);
        SysPermissionSearchRepository repository = Mockito.mock(SysPermissionSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubSysPermissionPages(mapper);

        SysPermissionService service = new SysPermissionService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<SysPermission> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void sysRoleFindAllShouldUsePagedFallback() {
        SysRoleMapper mapper = Mockito.mock(SysRoleMapper.class);
        SysRoleSearchRepository repository = Mockito.mock(SysRoleSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubSysRolePages(mapper);

        SysRoleService service = new SysRoleService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<SysRole> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void sysSettingsFindAllShouldUsePagedFallback() {
        SysSettingsMapper mapper = Mockito.mock(SysSettingsMapper.class);
        SysSettingsSearchRepository repository = Mockito.mock(SysSettingsSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubSysSettingsPages(mapper);

        SysSettingsService service = new SysSettingsService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<SysSettings> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void sysUserFindAllShouldUsePagedFallback() {
        SysUserMapper mapper = Mockito.mock(SysUserMapper.class);
        SysUserSearchRepository repository = Mockito.mock(SysUserSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubSysUserPages(mapper);

        SysUserService service = new SysUserService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(PasswordEncoder.class),
                Mockito.mock(CacheManager.class)
        );

        List<SysUser> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void appealReviewFindAllShouldUsePagedFallback() {
        AppealReviewMapper mapper = Mockito.mock(AppealReviewMapper.class);
        AppealReviewSearchRepository repository = Mockito.mock(AppealReviewSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubAppealReviewPages(mapper);

        AppealReviewService service = new AppealReviewService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(AppealRecordService.class),
                Mockito.mock(OffenseRecordService.class),
                Mockito.mock(FineRecordService.class),
                Mockito.mock(DeductionRecordService.class),
                Mockito.mock(PaymentRecordService.class),
                Mockito.mock(SysUserService.class),
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<AppealReview> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void deductionRecordFindAllShouldUsePagedFallback() {
        DeductionRecordMapper mapper = Mockito.mock(DeductionRecordMapper.class);
        DeductionRecordSearchRepository repository = Mockito.mock(DeductionRecordSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubDeductionRecordPages(mapper);

        DeductionRecordService service = new DeductionRecordService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(OffenseRecordService.class),
                Mockito.mock(DriverInformationService.class),
                Mockito.mock(SysUserService.class),
                Mockito.mock(KafkaTemplate.class)
        );

        List<DeductionRecord> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void driverVehicleFindAllShouldUsePagedFallback() {
        DriverVehicleMapper mapper = Mockito.mock(DriverVehicleMapper.class);
        DriverVehicleSearchRepository repository = Mockito.mock(DriverVehicleSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubDriverVehiclePages(mapper);

        DriverVehicleService service = new DriverVehicleService(
                mapper,
                Mockito.mock(DriverInformationMapper.class),
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(VehicleInformationMapper.class),
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<DriverVehicle> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void fineRecordFindAllShouldUsePagedFallback() {
        FineRecordMapper mapper = Mockito.mock(FineRecordMapper.class);
        FineRecordSearchRepository repository = Mockito.mock(FineRecordSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubFineRecordPages(mapper);

        FineRecordService service = new FineRecordService(
                mapper,
                Mockito.mock(PaymentRecordMapper.class),
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(OffenseRecordService.class),
                Mockito.mock(SysUserService.class),
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<FineRecord> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    @Test
    void sysBackupRestoreFindAllShouldUsePagedFallback() {
        SysBackupRestoreMapper mapper = Mockito.mock(SysBackupRestoreMapper.class);
        SysBackupRestoreSearchRepository repository = Mockito.mock(SysBackupRestoreSearchRepository.class);
        when(repository.findAll()).thenReturn(List.of());
        stubSysBackupRestorePages(mapper);

        SysBackupRestoreService service = new SysBackupRestoreService(
                mapper,
                Mockito.mock(SysRequestHistoryMapper.class),
                repository,
                Mockito.mock(KafkaTemplate.class),
                new ObjectMapper()
        );

        List<SysBackupRestore> result = service.findAll();

        assertEquals(3, result.size());
        verify(mapper, times(1)).selectPage(any(Page.class), any());
        verify(mapper, never()).selectList(any());
        verify(repository, times(1)).saveAll(any());
    }

    private void stubAuditLoginLogPages(AuditLoginLogMapper mapper) {
        AuditLoginLog first = new AuditLoginLog();
        first.setLogId(1L);
        AuditLoginLog second = new AuditLoginLog();
        second.setLogId(2L);
        AuditLoginLog third = new AuditLoginLog();
        third.setLogId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<AuditLoginLog> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubAuditOperationLogPages(AuditOperationLogMapper mapper) {
        AuditOperationLog first = new AuditOperationLog();
        first.setLogId(1L);
        AuditOperationLog second = new AuditOperationLog();
        second.setLogId(2L);
        AuditOperationLog third = new AuditOperationLog();
        third.setLogId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<AuditOperationLog> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubOffenseRecordPages(OffenseRecordMapper mapper) {
        OffenseRecord first = new OffenseRecord();
        first.setOffenseId(1L);
        OffenseRecord second = new OffenseRecord();
        second.setOffenseId(2L);
        OffenseRecord third = new OffenseRecord();
        third.setOffenseId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<OffenseRecord> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubPaymentRecordPages(PaymentRecordMapper mapper) {
        PaymentRecord first = new PaymentRecord();
        first.setPaymentId(1L);
        PaymentRecord second = new PaymentRecord();
        second.setPaymentId(2L);
        PaymentRecord third = new PaymentRecord();
        third.setPaymentId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<PaymentRecord> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubDriverInformationPages(DriverInformationMapper mapper) {
        DriverInformation first = new DriverInformation();
        first.setDriverId(1L);
        DriverInformation second = new DriverInformation();
        second.setDriverId(2L);
        DriverInformation third = new DriverInformation();
        third.setDriverId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<DriverInformation> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubVehicleInformationPages(VehicleInformationMapper mapper) {
        VehicleInformation first = new VehicleInformation();
        first.setVehicleId(1L);
        VehicleInformation second = new VehicleInformation();
        second.setVehicleId(2L);
        VehicleInformation third = new VehicleInformation();
        third.setVehicleId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<VehicleInformation> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubSysRequestHistoryPages(SysRequestHistoryMapper mapper) {
        SysRequestHistory first = new SysRequestHistory();
        first.setId(1L);
        SysRequestHistory second = new SysRequestHistory();
        second.setId(2L);
        SysRequestHistory third = new SysRequestHistory();
        third.setId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<SysRequestHistory> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubOffenseTypeDictPages(OffenseTypeDictMapper mapper) {
        OffenseTypeDict first = new OffenseTypeDict();
        first.setTypeId(1);
        OffenseTypeDict second = new OffenseTypeDict();
        second.setTypeId(2);
        OffenseTypeDict third = new OffenseTypeDict();
        third.setTypeId(3);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<OffenseTypeDict> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubSysDictPages(SysDictMapper mapper) {
        SysDict first = new SysDict();
        first.setDictId(1);
        SysDict second = new SysDict();
        second.setDictId(2);
        SysDict third = new SysDict();
        third.setDictId(3);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<SysDict> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubSysPermissionPages(SysPermissionMapper mapper) {
        SysPermission first = new SysPermission();
        first.setPermissionId(1);
        SysPermission second = new SysPermission();
        second.setPermissionId(2);
        SysPermission third = new SysPermission();
        third.setPermissionId(3);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<SysPermission> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubSysRolePages(SysRoleMapper mapper) {
        SysRole first = new SysRole();
        first.setRoleId(1);
        SysRole second = new SysRole();
        second.setRoleId(2);
        SysRole third = new SysRole();
        third.setRoleId(3);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<SysRole> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubSysSettingsPages(SysSettingsMapper mapper) {
        SysSettings first = new SysSettings();
        first.setSettingId(1);
        SysSettings second = new SysSettings();
        second.setSettingId(2);
        SysSettings third = new SysSettings();
        third.setSettingId(3);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<SysSettings> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubSysUserPages(SysUserMapper mapper) {
        SysUser first = new SysUser();
        first.setUserId(1L);
        SysUser second = new SysUser();
        second.setUserId(2L);
        SysUser third = new SysUser();
        third.setUserId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<SysUser> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubAppealReviewPages(AppealReviewMapper mapper) {
        AppealReview first = new AppealReview();
        first.setReviewId(1L);
        AppealReview second = new AppealReview();
        second.setReviewId(2L);
        AppealReview third = new AppealReview();
        third.setReviewId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<AppealReview> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubDeductionRecordPages(DeductionRecordMapper mapper) {
        DeductionRecord first = new DeductionRecord();
        first.setDeductionId(1L);
        DeductionRecord second = new DeductionRecord();
        second.setDeductionId(2L);
        DeductionRecord third = new DeductionRecord();
        third.setDeductionId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<DeductionRecord> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubDriverVehiclePages(DriverVehicleMapper mapper) {
        DriverVehicle first = new DriverVehicle();
        first.setId(1L);
        DriverVehicle second = new DriverVehicle();
        second.setId(2L);
        DriverVehicle third = new DriverVehicle();
        third.setId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<DriverVehicle> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubFineRecordPages(FineRecordMapper mapper) {
        FineRecord first = new FineRecord();
        first.setFineId(1L);
        FineRecord second = new FineRecord();
        second.setFineId(2L);
        FineRecord third = new FineRecord();
        third.setFineId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<FineRecord> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }

    private void stubSysBackupRestorePages(SysBackupRestoreMapper mapper) {
        SysBackupRestore first = new SysBackupRestore();
        first.setBackupId(1L);
        SysBackupRestore second = new SysBackupRestore();
        second.setBackupId(2L);
        SysBackupRestore third = new SysBackupRestore();
        third.setBackupId(3L);
        when(mapper.selectPage(any(Page.class), any())).thenAnswer(invocation -> {
            @SuppressWarnings("unchecked")
            Page<SysBackupRestore> page = invocation.getArgument(0);
            page.setRecords(page.getCurrent() == 1L ? List.of(first, second, third) : List.of());
            return page;
        });
    }
}
