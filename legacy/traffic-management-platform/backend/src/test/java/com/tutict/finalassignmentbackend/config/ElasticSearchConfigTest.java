package com.tutict.finalassignmentbackend.config;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.entity.elastic.VehicleInformationDocument;
import com.tutict.finalassignmentbackend.mapper.AppealRecordMapper;
import com.tutict.finalassignmentbackend.mapper.AppealReviewMapper;
import com.tutict.finalassignmentbackend.mapper.AuditLoginLogMapper;
import com.tutict.finalassignmentbackend.mapper.AuditOperationLogMapper;
import com.tutict.finalassignmentbackend.mapper.DeductionRecordMapper;
import com.tutict.finalassignmentbackend.mapper.DriverInformationMapper;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.FineRecordMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseTypeDictMapper;
import com.tutict.finalassignmentbackend.mapper.PaymentRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysBackupRestoreMapper;
import com.tutict.finalassignmentbackend.mapper.SysDictMapper;
import com.tutict.finalassignmentbackend.mapper.SysPermissionMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.SysRoleMapper;
import com.tutict.finalassignmentbackend.mapper.SysRolePermissionMapper;
import com.tutict.finalassignmentbackend.mapper.SysSettingsMapper;
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
import com.tutict.finalassignmentbackend.repository.OffenseTypeDictSearchRepository;
import com.tutict.finalassignmentbackend.repository.PaymentRecordSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysBackupRestoreSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysDictSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysPermissionSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysRequestHistorySearchRepository;
import com.tutict.finalassignmentbackend.repository.SysRolePermissionSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysRoleSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysSettingsSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysUserRoleSearchRepository;
import com.tutict.finalassignmentbackend.repository.SysUserSearchRepository;
import com.tutict.finalassignmentbackend.repository.VehicleInformationSearchRepository;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;

import java.util.List;
import java.util.stream.StreamSupport;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class ElasticSearchConfigTest {

    @Test
    void shouldSkipStartupSyncWhenDisabled() {
        Fixture fixture = new Fixture();

        ElasticSearchConfig config = fixture.create(false, 2);

        config.syncDatabaseToElasticsearch();

        verifyNoInteractions(fixture.vehicleInformationMapper, fixture.vehicleInformationSearchRepository);
    }

    @Test
    void shouldSyncVehiclesInPagedBatchesWithoutSelectList() {
        Fixture fixture = new Fixture();
        VehicleInformation first = vehicle(1L, "A1001");
        VehicleInformation second = vehicle(2L, "A1002");
        VehicleInformation third = vehicle(3L, "A1003");

        when(fixture.vehicleInformationMapper.selectPage(any(Page.class), isNull()))
                .thenAnswer(invocation -> {
                    @SuppressWarnings("unchecked")
                    Page<VehicleInformation> page = invocation.getArgument(0);
                    long current = page.getCurrent();
                    if (current == 1L) {
                        page.setRecords(List.of(first, second));
                    } else if (current == 2L) {
                        page.setRecords(List.of(third));
                    } else {
                        page.setRecords(List.of());
                    }
                    return page;
                });

        ElasticSearchConfig config = fixture.create(true, 2);

        config.syncDatabaseToElasticsearch();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Iterable<VehicleInformationDocument>> captor = ArgumentCaptor.forClass(Iterable.class);
        verify(fixture.vehicleInformationSearchRepository, times(2)).saveAll(captor.capture());
        verify(fixture.vehicleInformationMapper, never()).selectList(any());
        verify(fixture.vehicleInformationMapper, times(2)).selectPage(any(Page.class), isNull());

        List<Integer> batchSizes = captor.getAllValues().stream()
                .map(batch -> (int) StreamSupport.stream(batch.spliterator(), false).count())
                .toList();

        assertEquals(List.of(2, 1), batchSizes);
    }

    private static VehicleInformation vehicle(long id, String plate) {
        VehicleInformation vehicle = new VehicleInformation();
        vehicle.setVehicleId(id);
        vehicle.setLicensePlate(plate);
        return vehicle;
    }

    private static <T, M extends BaseMapper<T>> M mockPagedMapper(Class<M> mapperType) {
        M mapper = Mockito.mock(mapperType);
        when(mapper.selectPage(any(Page.class), isNull()))
                .thenAnswer(invocation -> invocation.getArgument(0));
        return mapper;
    }

    private static final class Fixture {
        private final VehicleInformationMapper vehicleInformationMapper = mockPagedMapper(VehicleInformationMapper.class);
        private final DriverInformationMapper driverInformationMapper = mockPagedMapper(DriverInformationMapper.class);
        private final DriverVehicleMapper driverVehicleMapper = mockPagedMapper(DriverVehicleMapper.class);
        private final OffenseRecordMapper offenseRecordMapper = mockPagedMapper(OffenseRecordMapper.class);
        private final AppealRecordMapper appealRecordMapper = mockPagedMapper(AppealRecordMapper.class);
        private final AppealReviewMapper appealReviewMapper = mockPagedMapper(AppealReviewMapper.class);
        private final FineRecordMapper fineRecordMapper = mockPagedMapper(FineRecordMapper.class);
        private final DeductionRecordMapper deductionRecordMapper = mockPagedMapper(DeductionRecordMapper.class);
        private final PaymentRecordMapper paymentRecordMapper = mockPagedMapper(PaymentRecordMapper.class);
        private final OffenseTypeDictMapper offenseTypeDictMapper = mockPagedMapper(OffenseTypeDictMapper.class);
        private final SysUserMapper sysUserMapper = mockPagedMapper(SysUserMapper.class);
        private final SysRoleMapper sysRoleMapper = mockPagedMapper(SysRoleMapper.class);
        private final SysUserRoleMapper sysUserRoleMapper = mockPagedMapper(SysUserRoleMapper.class);
        private final SysPermissionMapper sysPermissionMapper = mockPagedMapper(SysPermissionMapper.class);
        private final SysDictMapper sysDictMapper = mockPagedMapper(SysDictMapper.class);
        private final SysSettingsMapper sysSettingsMapper = mockPagedMapper(SysSettingsMapper.class);
        private final SysBackupRestoreMapper sysBackupRestoreMapper = mockPagedMapper(SysBackupRestoreMapper.class);
        private final SysRequestHistoryMapper sysRequestHistoryMapper = mockPagedMapper(SysRequestHistoryMapper.class);
        private final SysRolePermissionMapper sysRolePermissionMapper = mockPagedMapper(SysRolePermissionMapper.class);
        private final AuditLoginLogMapper auditLoginLogMapper = mockPagedMapper(AuditLoginLogMapper.class);
        private final AuditOperationLogMapper auditOperationLogMapper = mockPagedMapper(AuditOperationLogMapper.class);

        private final VehicleInformationSearchRepository vehicleInformationSearchRepository = Mockito.mock(VehicleInformationSearchRepository.class);
        private final DriverInformationSearchRepository driverInformationSearchRepository = Mockito.mock(DriverInformationSearchRepository.class);
        private final DriverVehicleSearchRepository driverVehicleSearchRepository = Mockito.mock(DriverVehicleSearchRepository.class);
        private final OffenseInformationSearchRepository offenseInformationSearchRepository = Mockito.mock(OffenseInformationSearchRepository.class);
        private final AppealRecordSearchRepository appealRecordSearchRepository = Mockito.mock(AppealRecordSearchRepository.class);
        private final AppealReviewSearchRepository appealReviewSearchRepository = Mockito.mock(AppealReviewSearchRepository.class);
        private final FineRecordSearchRepository fineRecordSearchRepository = Mockito.mock(FineRecordSearchRepository.class);
        private final DeductionRecordSearchRepository deductionRecordSearchRepository = Mockito.mock(DeductionRecordSearchRepository.class);
        private final PaymentRecordSearchRepository paymentRecordSearchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        private final OffenseTypeDictSearchRepository offenseTypeDictSearchRepository = Mockito.mock(OffenseTypeDictSearchRepository.class);
        private final SysUserSearchRepository sysUserSearchRepository = Mockito.mock(SysUserSearchRepository.class);
        private final SysRoleSearchRepository sysRoleSearchRepository = Mockito.mock(SysRoleSearchRepository.class);
        private final SysUserRoleSearchRepository sysUserRoleSearchRepository = Mockito.mock(SysUserRoleSearchRepository.class);
        private final SysPermissionSearchRepository sysPermissionSearchRepository = Mockito.mock(SysPermissionSearchRepository.class);
        private final SysDictSearchRepository sysDictSearchRepository = Mockito.mock(SysDictSearchRepository.class);
        private final SysSettingsSearchRepository sysSettingsSearchRepository = Mockito.mock(SysSettingsSearchRepository.class);
        private final SysBackupRestoreSearchRepository sysBackupRestoreSearchRepository = Mockito.mock(SysBackupRestoreSearchRepository.class);
        private final SysRequestHistorySearchRepository sysRequestHistorySearchRepository = Mockito.mock(SysRequestHistorySearchRepository.class);
        private final SysRolePermissionSearchRepository sysRolePermissionSearchRepository = Mockito.mock(SysRolePermissionSearchRepository.class);
        private final AuditLoginLogSearchRepository auditLoginLogSearchRepository = Mockito.mock(AuditLoginLogSearchRepository.class);
        private final AuditOperationLogSearchRepository auditOperationLogSearchRepository = Mockito.mock(AuditOperationLogSearchRepository.class);

        private ElasticSearchConfig create(boolean syncOnStartup, int batchSize) {
            return new ElasticSearchConfig(
                    syncOnStartup,
                    batchSize,
                    vehicleInformationMapper,
                    driverInformationMapper,
                    driverVehicleMapper,
                    offenseRecordMapper,
                    appealRecordMapper,
                    appealReviewMapper,
                    fineRecordMapper,
                    deductionRecordMapper,
                    paymentRecordMapper,
                    offenseTypeDictMapper,
                    sysUserMapper,
                    sysRoleMapper,
                    sysUserRoleMapper,
                    sysPermissionMapper,
                    sysDictMapper,
                    sysSettingsMapper,
                    sysBackupRestoreMapper,
                    sysRequestHistoryMapper,
                    sysRolePermissionMapper,
                    auditLoginLogMapper,
                    auditOperationLogMapper,
                    vehicleInformationSearchRepository,
                    driverInformationSearchRepository,
                    driverVehicleSearchRepository,
                    offenseInformationSearchRepository,
                    appealRecordSearchRepository,
                    appealReviewSearchRepository,
                    fineRecordSearchRepository,
                    deductionRecordSearchRepository,
                    paymentRecordSearchRepository,
                    offenseTypeDictSearchRepository,
                    sysUserSearchRepository,
                    sysRoleSearchRepository,
                    sysUserRoleSearchRepository,
                    sysPermissionSearchRepository,
                    sysDictSearchRepository,
                    sysSettingsSearchRepository,
                    sysBackupRestoreSearchRepository,
                    sysRequestHistorySearchRepository,
                    sysRolePermissionSearchRepository,
                    auditLoginLogSearchRepository,
                    auditOperationLogSearchRepository
            );
        }
    }
}
