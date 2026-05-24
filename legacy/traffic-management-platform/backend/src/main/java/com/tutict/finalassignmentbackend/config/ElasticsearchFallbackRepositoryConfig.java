package com.tutict.finalassignmentbackend.config;

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
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.data.elasticsearch.core.SearchHitsImpl;
import org.springframework.data.elasticsearch.core.SearchShardStatistics;
import org.springframework.data.elasticsearch.core.TotalHitsRelation;

import java.lang.reflect.Proxy;
import java.time.Duration;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Configuration
@ConditionalOnProperty(name = "spring.data.elasticsearch.repositories.enabled", havingValue = "false", matchIfMissing = true)
public class ElasticsearchFallbackRepositoryConfig {

    @Bean
    public AppealRecordSearchRepository appealRecordSearchRepository() {
        return noopRepository(AppealRecordSearchRepository.class);
    }

    @Bean
    public AppealReviewSearchRepository appealReviewSearchRepository() {
        return noopRepository(AppealReviewSearchRepository.class);
    }

    @Bean
    public AuditLoginLogSearchRepository auditLoginLogSearchRepository() {
        return noopRepository(AuditLoginLogSearchRepository.class);
    }

    @Bean
    public AuditOperationLogSearchRepository auditOperationLogSearchRepository() {
        return noopRepository(AuditOperationLogSearchRepository.class);
    }

    @Bean
    public DeductionRecordSearchRepository deductionRecordSearchRepository() {
        return noopRepository(DeductionRecordSearchRepository.class);
    }

    @Bean
    public DriverInformationSearchRepository driverInformationSearchRepository() {
        return noopRepository(DriverInformationSearchRepository.class);
    }

    @Bean
    public DriverVehicleSearchRepository driverVehicleSearchRepository() {
        return noopRepository(DriverVehicleSearchRepository.class);
    }

    @Bean
    public FineRecordSearchRepository fineRecordSearchRepository() {
        return noopRepository(FineRecordSearchRepository.class);
    }

    @Bean
    public OffenseInformationSearchRepository offenseInformationSearchRepository() {
        return noopRepository(OffenseInformationSearchRepository.class);
    }

    @Bean
    public OffenseTypeDictSearchRepository offenseTypeDictSearchRepository() {
        return noopRepository(OffenseTypeDictSearchRepository.class);
    }

    @Bean
    public PaymentRecordSearchRepository paymentRecordSearchRepository() {
        return noopRepository(PaymentRecordSearchRepository.class);
    }

    @Bean
    public SysBackupRestoreSearchRepository sysBackupRestoreSearchRepository() {
        return noopRepository(SysBackupRestoreSearchRepository.class);
    }

    @Bean
    public SysDictSearchRepository sysDictSearchRepository() {
        return noopRepository(SysDictSearchRepository.class);
    }

    @Bean
    public SysPermissionSearchRepository sysPermissionSearchRepository() {
        return noopRepository(SysPermissionSearchRepository.class);
    }

    @Bean
    public SysRequestHistorySearchRepository sysRequestHistorySearchRepository() {
        return noopRepository(SysRequestHistorySearchRepository.class);
    }

    @Bean
    public SysRolePermissionSearchRepository sysRolePermissionSearchRepository() {
        return noopRepository(SysRolePermissionSearchRepository.class);
    }

    @Bean
    public SysRoleSearchRepository sysRoleSearchRepository() {
        return noopRepository(SysRoleSearchRepository.class);
    }

    @Bean
    public SysSettingsSearchRepository sysSettingsSearchRepository() {
        return noopRepository(SysSettingsSearchRepository.class);
    }

    @Bean
    public SysUserRoleSearchRepository sysUserRoleSearchRepository() {
        return noopRepository(SysUserRoleSearchRepository.class);
    }

    @Bean
    public SysUserSearchRepository sysUserSearchRepository() {
        return noopRepository(SysUserSearchRepository.class);
    }

    @Bean
    public VehicleInformationSearchRepository vehicleInformationSearchRepository() {
        return noopRepository(VehicleInformationSearchRepository.class);
    }

    @SuppressWarnings("unchecked")
    private <T> T noopRepository(Class<T> repositoryType) {
        return (T) Proxy.newProxyInstance(
                repositoryType.getClassLoader(),
                new Class<?>[]{repositoryType},
                (proxy, method, args) -> {
                    if (method.getDeclaringClass() == Object.class) {
                        return switch (method.getName()) {
                            case "toString" -> repositoryType.getSimpleName() + "NoopProxy";
                            case "hashCode" -> System.identityHashCode(proxy);
                            case "equals" -> proxy == args[0];
                            default -> method.invoke(this, args);
                        };
                    }

                    String methodName = method.getName();
                    if ("save".equals(methodName)) {
                        return args != null && args.length > 0 ? args[0] : null;
                    }
                    if ("saveAll".equals(methodName)) {
                        return args != null && args.length > 0 ? args[0] : List.of();
                    }
                    if ("findById".equals(methodName)) {
                        return Optional.empty();
                    }
                    if ("findAllById".equals(methodName) || "findAll".equals(methodName)) {
                        return List.of();
                    }
                    if ("existsById".equals(methodName)) {
                        return false;
                    }
                    if ("count".equals(methodName)) {
                        return 0L;
                    }
                    if (method.getReturnType() == Void.TYPE) {
                        return null;
                    }

                    return defaultValue(method.getReturnType(), args);
                });
    }

    private Object defaultValue(Class<?> returnType, Object[] args) {
        if (returnType == Void.TYPE) {
            return null;
        }
        if (Optional.class.isAssignableFrom(returnType)) {
            return Optional.empty();
        }
        if (SearchHits.class.isAssignableFrom(returnType)) {
            return emptySearchHits();
        }
        if (Iterable.class.isAssignableFrom(returnType) || Collection.class.isAssignableFrom(returnType)) {
            return List.of();
        }
        if (Map.class.isAssignableFrom(returnType)) {
            return Map.of();
        }
        if (returnType == Boolean.TYPE || returnType == Boolean.class) {
            return false;
        }
        if (returnType == Integer.TYPE || returnType == Integer.class) {
            return 0;
        }
        if (returnType == Long.TYPE || returnType == Long.class) {
            return 0L;
        }
        if (returnType == Double.TYPE || returnType == Double.class) {
            return 0D;
        }
        if (returnType == Float.TYPE || returnType == Float.class) {
            return 0F;
        }
        if (returnType == Short.TYPE || returnType == Short.class) {
            return (short) 0;
        }
        if (returnType == Byte.TYPE || returnType == Byte.class) {
            return (byte) 0;
        }
        if (returnType == Character.TYPE || returnType == Character.class) {
            return '\0';
        }
        if (returnType == String.class) {
            return "";
        }
        if (args != null && args.length > 0 && returnType.isInstance(args[0])) {
            return args[0];
        }
        return null;
    }

    private <T> SearchHits<T> emptySearchHits() {
        return new SearchHitsImpl<>(
                0L,
                TotalHitsRelation.EQUAL_TO,
                0.0f,
                Duration.ZERO,
                null,
                null,
                List.<SearchHit<T>>of(),
                null,
                null,
                SearchShardStatistics.of(0, 0, 0, 0, List.of())
        );
    }
}
