package com.tutict.finalassignmentbackend.config;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
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
import com.tutict.finalassignmentbackend.entity.SysBackupRestore;
import com.tutict.finalassignmentbackend.entity.SysDict;
import com.tutict.finalassignmentbackend.entity.SysPermission;
import com.tutict.finalassignmentbackend.entity.SysRequestHistory;
import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysRolePermission;
import com.tutict.finalassignmentbackend.entity.SysSettings;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.SysUserRole;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.entity.elastic.AppealRecordDocument;
import com.tutict.finalassignmentbackend.entity.elastic.AppealReviewDocument;
import com.tutict.finalassignmentbackend.entity.elastic.AuditLoginLogDocument;
import com.tutict.finalassignmentbackend.entity.elastic.AuditOperationLogDocument;
import com.tutict.finalassignmentbackend.entity.elastic.DeductionRecordDocument;
import com.tutict.finalassignmentbackend.entity.elastic.DriverInformationDocument;
import com.tutict.finalassignmentbackend.entity.elastic.DriverVehicleDocument;
import com.tutict.finalassignmentbackend.entity.elastic.FineRecordDocument;
import com.tutict.finalassignmentbackend.entity.elastic.OffenseRecordDocument;
import com.tutict.finalassignmentbackend.entity.elastic.OffenseTypeDictDocument;
import com.tutict.finalassignmentbackend.entity.elastic.PaymentRecordDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysBackupRestoreDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysDictDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysPermissionDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysRequestHistoryDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysRoleDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysRolePermissionDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysSettingsDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysUserDocument;
import com.tutict.finalassignmentbackend.entity.elastic.SysUserRoleDocument;
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
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.data.elasticsearch.repository.config.EnableElasticsearchRepositories;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import java.util.logging.Level;
import java.util.logging.Logger;

@Configuration
@ConditionalOnProperty(name = "spring.data.elasticsearch.repositories.enabled", havingValue = "true")
@EnableElasticsearchRepositories(basePackages = "com.tutict.finalassignmentbackend.repository")
public class ElasticSearchConfig {

    private static final Logger LOG = Logger.getLogger(ElasticSearchConfig.class.getName());

    private final boolean syncOnStartup;
    private final int syncBatchSize;
    private final VehicleInformationMapper vehicleInformationMapper;
    private final DriverInformationMapper driverInformationMapper;
    private final DriverVehicleMapper driverVehicleMapper;
    private final OffenseRecordMapper offenseRecordMapper;
    private final AppealRecordMapper appealRecordMapper;
    private final AppealReviewMapper appealReviewMapper;
    private final FineRecordMapper fineRecordMapper;
    private final DeductionRecordMapper deductionRecordMapper;
    private final PaymentRecordMapper paymentRecordMapper;
    private final OffenseTypeDictMapper offenseTypeDictMapper;
    private final SysUserMapper sysUserMapper;
    private final SysRoleMapper sysRoleMapper;
    private final SysUserRoleMapper sysUserRoleMapper;
    private final SysPermissionMapper sysPermissionMapper;
    private final SysDictMapper sysDictMapper;
    private final SysSettingsMapper sysSettingsMapper;
    private final SysBackupRestoreMapper sysBackupRestoreMapper;
    private final SysRequestHistoryMapper sysRequestHistoryMapper;
    private final SysRolePermissionMapper sysRolePermissionMapper;
    private final AuditLoginLogMapper auditLoginLogMapper;
    private final AuditOperationLogMapper auditOperationLogMapper;

    private final @Lazy VehicleInformationSearchRepository vehicleInformationSearchRepository;
    private final @Lazy DriverInformationSearchRepository driverInformationSearchRepository;
    private final @Lazy DriverVehicleSearchRepository driverVehicleSearchRepository;
    private final @Lazy OffenseInformationSearchRepository offenseInformationSearchRepository;
    private final @Lazy AppealRecordSearchRepository appealRecordSearchRepository;
    private final @Lazy AppealReviewSearchRepository appealReviewSearchRepository;
    private final @Lazy FineRecordSearchRepository fineRecordSearchRepository;
    private final @Lazy DeductionRecordSearchRepository deductionRecordSearchRepository;
    private final @Lazy PaymentRecordSearchRepository paymentRecordSearchRepository;
    private final @Lazy OffenseTypeDictSearchRepository offenseTypeDictSearchRepository;
    private final @Lazy SysUserSearchRepository sysUserSearchRepository;
    private final @Lazy SysRoleSearchRepository sysRoleSearchRepository;
    private final @Lazy SysUserRoleSearchRepository sysUserRoleSearchRepository;
    private final @Lazy SysPermissionSearchRepository sysPermissionSearchRepository;
    private final @Lazy SysDictSearchRepository sysDictSearchRepository;
    private final @Lazy SysSettingsSearchRepository sysSettingsSearchRepository;
    private final @Lazy SysBackupRestoreSearchRepository sysBackupRestoreSearchRepository;
    private final @Lazy SysRequestHistorySearchRepository sysRequestHistorySearchRepository;
    private final @Lazy SysRolePermissionSearchRepository sysRolePermissionSearchRepository;
    private final @Lazy AuditLoginLogSearchRepository auditLoginLogSearchRepository;
    private final @Lazy AuditOperationLogSearchRepository auditOperationLogSearchRepository;

    public ElasticSearchConfig(
            @Value("${app.elasticsearch.sync-on-startup:false}") boolean syncOnStartup,
            @Value("${app.elasticsearch.sync-batch-size:500}") int syncBatchSize,
            VehicleInformationMapper vehicleInformationMapper,
            DriverInformationMapper driverInformationMapper,
            DriverVehicleMapper driverVehicleMapper,
            OffenseRecordMapper offenseRecordMapper,
            AppealRecordMapper appealRecordMapper,
            AppealReviewMapper appealReviewMapper,
            FineRecordMapper fineRecordMapper,
            DeductionRecordMapper deductionRecordMapper,
            PaymentRecordMapper paymentRecordMapper,
            OffenseTypeDictMapper offenseTypeDictMapper,
            SysUserMapper sysUserMapper,
            SysRoleMapper sysRoleMapper,
            SysUserRoleMapper sysUserRoleMapper,
            SysPermissionMapper sysPermissionMapper,
            SysDictMapper sysDictMapper,
            SysSettingsMapper sysSettingsMapper,
            SysBackupRestoreMapper sysBackupRestoreMapper,
            SysRequestHistoryMapper sysRequestHistoryMapper,
            SysRolePermissionMapper sysRolePermissionMapper,
            AuditLoginLogMapper auditLoginLogMapper,
            AuditOperationLogMapper auditOperationLogMapper,
            @Lazy VehicleInformationSearchRepository vehicleInformationSearchRepository,
            @Lazy DriverInformationSearchRepository driverInformationSearchRepository,
            @Lazy DriverVehicleSearchRepository driverVehicleSearchRepository,
            @Lazy OffenseInformationSearchRepository offenseInformationSearchRepository,
            @Lazy AppealRecordSearchRepository appealRecordSearchRepository,
            @Lazy AppealReviewSearchRepository appealReviewSearchRepository,
            @Lazy FineRecordSearchRepository fineRecordSearchRepository,
            @Lazy DeductionRecordSearchRepository deductionRecordSearchRepository,
            @Lazy PaymentRecordSearchRepository paymentRecordSearchRepository,
            @Lazy OffenseTypeDictSearchRepository offenseTypeDictSearchRepository,
            @Lazy SysUserSearchRepository sysUserSearchRepository,
            @Lazy SysRoleSearchRepository sysRoleSearchRepository,
            @Lazy SysUserRoleSearchRepository sysUserRoleSearchRepository,
            @Lazy SysPermissionSearchRepository sysPermissionSearchRepository,
            @Lazy SysDictSearchRepository sysDictSearchRepository,
            @Lazy SysSettingsSearchRepository sysSettingsSearchRepository,
            @Lazy SysBackupRestoreSearchRepository sysBackupRestoreSearchRepository,
            @Lazy SysRequestHistorySearchRepository sysRequestHistorySearchRepository,
            @Lazy SysRolePermissionSearchRepository sysRolePermissionSearchRepository,
            @Lazy AuditLoginLogSearchRepository auditLoginLogSearchRepository,
            @Lazy AuditOperationLogSearchRepository auditOperationLogSearchRepository) {
        this.syncOnStartup = syncOnStartup;
        this.syncBatchSize = Math.max(1, syncBatchSize);
        this.vehicleInformationMapper = vehicleInformationMapper;
        this.driverInformationMapper = driverInformationMapper;
        this.driverVehicleMapper = driverVehicleMapper;
        this.offenseRecordMapper = offenseRecordMapper;
        this.appealRecordMapper = appealRecordMapper;
        this.appealReviewMapper = appealReviewMapper;
        this.fineRecordMapper = fineRecordMapper;
        this.deductionRecordMapper = deductionRecordMapper;
        this.paymentRecordMapper = paymentRecordMapper;
        this.offenseTypeDictMapper = offenseTypeDictMapper;
        this.sysUserMapper = sysUserMapper;
        this.sysRoleMapper = sysRoleMapper;
        this.sysUserRoleMapper = sysUserRoleMapper;
        this.sysPermissionMapper = sysPermissionMapper;
        this.sysDictMapper = sysDictMapper;
        this.sysSettingsMapper = sysSettingsMapper;
        this.sysBackupRestoreMapper = sysBackupRestoreMapper;
        this.sysRequestHistoryMapper = sysRequestHistoryMapper;
        this.sysRolePermissionMapper = sysRolePermissionMapper;
        this.auditLoginLogMapper = auditLoginLogMapper;
        this.auditOperationLogMapper = auditOperationLogMapper;
        this.vehicleInformationSearchRepository = vehicleInformationSearchRepository;
        this.driverInformationSearchRepository = driverInformationSearchRepository;
        this.driverVehicleSearchRepository = driverVehicleSearchRepository;
        this.offenseInformationSearchRepository = offenseInformationSearchRepository;
        this.appealRecordSearchRepository = appealRecordSearchRepository;
        this.appealReviewSearchRepository = appealReviewSearchRepository;
        this.fineRecordSearchRepository = fineRecordSearchRepository;
        this.deductionRecordSearchRepository = deductionRecordSearchRepository;
        this.paymentRecordSearchRepository = paymentRecordSearchRepository;
        this.offenseTypeDictSearchRepository = offenseTypeDictSearchRepository;
        this.sysUserSearchRepository = sysUserSearchRepository;
        this.sysRoleSearchRepository = sysRoleSearchRepository;
        this.sysUserRoleSearchRepository = sysUserRoleSearchRepository;
        this.sysPermissionSearchRepository = sysPermissionSearchRepository;
        this.sysDictSearchRepository = sysDictSearchRepository;
        this.sysSettingsSearchRepository = sysSettingsSearchRepository;
        this.sysBackupRestoreSearchRepository = sysBackupRestoreSearchRepository;
        this.sysRequestHistorySearchRepository = sysRequestHistorySearchRepository;
        this.sysRolePermissionSearchRepository = sysRolePermissionSearchRepository;
        this.auditLoginLogSearchRepository = auditLoginLogSearchRepository;
        this.auditOperationLogSearchRepository = auditOperationLogSearchRepository;
    }

    @PostConstruct
    public void syncDatabaseToElasticsearch() {
        if (!syncOnStartup) {
            LOG.log(Level.INFO, "Skipping startup database to Elasticsearch sync because app.elasticsearch.sync-on-startup=false");
            return;
        }

        LOG.log(Level.INFO, "Starting startup database to Elasticsearch sync with batch size {0}", syncBatchSize);

        syncEntities("vehicle_information", vehicleInformationMapper, vehicleInformationSearchRepository, VehicleInformationDocument::fromEntity, VehicleInformation::getVehicleId);
        syncEntities("driver_information", driverInformationMapper, driverInformationSearchRepository, DriverInformationDocument::fromEntity, DriverInformation::getDriverId);
        syncEntities("driver_vehicle", driverVehicleMapper, driverVehicleSearchRepository, DriverVehicleDocument::fromEntity, DriverVehicle::getId);
        syncEntities("offense_record", offenseRecordMapper, offenseInformationSearchRepository, OffenseRecordDocument::fromEntity, OffenseRecord::getOffenseId);
        syncEntities("appeal_record", appealRecordMapper, appealRecordSearchRepository, AppealRecordDocument::fromEntity, AppealRecord::getAppealId);
        syncEntities("appeal_review", appealReviewMapper, appealReviewSearchRepository, AppealReviewDocument::fromEntity, AppealReview::getReviewId);
        syncEntities("fine_record", fineRecordMapper, fineRecordSearchRepository, FineRecordDocument::fromEntity, FineRecord::getFineId);
        syncEntities("deduction_record", deductionRecordMapper, deductionRecordSearchRepository, DeductionRecordDocument::fromEntity, DeductionRecord::getDeductionId);
        syncEntities("payment_record", paymentRecordMapper, paymentRecordSearchRepository, PaymentRecordDocument::fromEntity, PaymentRecord::getPaymentId);
        syncEntities("offense_type_dict", offenseTypeDictMapper, offenseTypeDictSearchRepository, OffenseTypeDictDocument::fromEntity, OffenseTypeDict::getTypeId);
        syncEntities("sys_user", sysUserMapper, sysUserSearchRepository, SysUserDocument::fromEntity, SysUser::getUserId);
        syncEntities("sys_role", sysRoleMapper, sysRoleSearchRepository, SysRoleDocument::fromEntity, SysRole::getRoleId);
        syncEntities("sys_user_role", sysUserRoleMapper, sysUserRoleSearchRepository, SysUserRoleDocument::fromEntity, SysUserRole::getId);
        syncEntities("sys_permission", sysPermissionMapper, sysPermissionSearchRepository, SysPermissionDocument::fromEntity, SysPermission::getPermissionId);
        syncEntities("sys_dict", sysDictMapper, sysDictSearchRepository, SysDictDocument::fromEntity, SysDict::getDictId);
        syncEntities("sys_settings", sysSettingsMapper, sysSettingsSearchRepository, SysSettingsDocument::fromEntity, SysSettings::getSettingId);
        syncEntities("sys_backup_restore", sysBackupRestoreMapper, sysBackupRestoreSearchRepository, SysBackupRestoreDocument::fromEntity, SysBackupRestore::getBackupId);
        syncEntities("sys_request_history", sysRequestHistoryMapper, sysRequestHistorySearchRepository, SysRequestHistoryDocument::fromEntity, SysRequestHistory::getId);
        syncEntities("sys_role_permission", sysRolePermissionMapper, sysRolePermissionSearchRepository, SysRolePermissionDocument::fromEntity, SysRolePermission::getId);
        syncEntities("audit_login_log", auditLoginLogMapper, auditLoginLogSearchRepository, AuditLoginLogDocument::fromEntity, AuditLoginLog::getLogId);
        syncEntities("audit_operation_log", auditOperationLogMapper, auditOperationLogSearchRepository, AuditOperationLogDocument::fromEntity, AuditOperationLog::getLogId);

        LOG.log(Level.INFO, "Finished startup database to Elasticsearch sync");
    }

    private <T, ID, D> void syncEntities(String entityType,
                                         BaseMapper<T> mapper,
                                         ElasticsearchRepository<D, ID> repository,
                                         Function<T, D> converter,
                                         Function<T, ID> idExtractor) {
        long pageNumber = 1L;
        int savedCount = 0;
        int failedCount = 0;
        int batchCount = 0;

        while (true) {
            Page<T> batchPage = new Page<>(pageNumber, syncBatchSize, false);
            List<T> records = mapper.selectPage(batchPage, null).getRecords();
            if (records == null || records.isEmpty()) {
                break;
            }

            List<D> documents = new ArrayList<>(records.size());
            for (T entity : records) {
                try {
                    D document = converter.apply(entity);
                    if (document == null) {
                        failedCount++;
                        LOG.log(Level.WARNING, "Skipping {0} record because document conversion returned null. id={1}",
                                new Object[]{entityType, idExtractor.apply(entity)});
                        continue;
                    }
                    documents.add(document);
                } catch (Exception error) {
                    failedCount++;
                    LOG.log(Level.WARNING, "Failed to convert {0} record. id={1}, error={2}",
                            new Object[]{entityType, idExtractor.apply(entity), error.getMessage()});
                }
            }

            savedCount += saveBatch(entityType, repository, documents, records, converter, idExtractor);
            batchCount++;
            LOG.log(Level.INFO, "Synced Elasticsearch batch for {0}: batch={1}, fetched={2}, saved={3}, failed={4}",
                    new Object[]{entityType, batchCount, records.size(), savedCount, failedCount});

            if (records.size() < syncBatchSize) {
                break;
            }
            pageNumber++;
        }

        if (batchCount == 0) {
            LOG.log(Level.INFO, "No records found for Elasticsearch startup sync: {0}", entityType);
            return;
        }

        LOG.log(Level.INFO, "Completed Elasticsearch startup sync for {0}: batches={1}, saved={2}, failed={3}",
                new Object[]{entityType, batchCount, savedCount, failedCount});
    }

    private <T, ID, D> int saveBatch(String entityType,
                                     ElasticsearchRepository<D, ID> repository,
                                     List<D> documents,
                                     List<T> sourceRecords,
                                     Function<T, D> converter,
                                     Function<T, ID> idExtractor) {
        if (documents == null || documents.isEmpty()) {
            return 0;
        }

        try {
            repository.saveAll(documents);
            return documents.size();
        } catch (Exception batchError) {
            LOG.log(Level.SEVERE, "Batch sync failed for {0}, retrying each document individually: {1}",
                    new Object[]{entityType, batchError.getMessage()});
        }

        int saved = 0;
        for (T entity : sourceRecords) {
            try {
                D document = converter.apply(entity);
                if (document == null) {
                    continue;
                }
                repository.save(document);
                saved++;
            } catch (Exception itemError) {
                LOG.log(Level.SEVERE, "Failed to sync {0} record to Elasticsearch. id={1}, error={2}",
                        new Object[]{entityType, idExtractor.apply(entity), itemError.getMessage()});
            }
        }
        return saved;
    }
}
