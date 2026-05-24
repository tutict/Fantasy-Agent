package com.tutict.finalassignmentbackend.config.bootstrap;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.tutict.finalassignmentbackend.config.product.OperationsProperties;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import com.tutict.finalassignmentbackend.entity.OffenseTypeDict;
import com.tutict.finalassignmentbackend.entity.SysDict;
import com.tutict.finalassignmentbackend.entity.SysPermission;
import com.tutict.finalassignmentbackend.entity.SysRole;
import com.tutict.finalassignmentbackend.entity.SysRolePermission;
import com.tutict.finalassignmentbackend.entity.SysSettings;
import com.tutict.finalassignmentbackend.enums.DataScope;
import com.tutict.finalassignmentbackend.enums.RoleType;
import com.tutict.finalassignmentbackend.mapper.OffenseTypeDictMapper;
import com.tutict.finalassignmentbackend.mapper.SysDictMapper;
import com.tutict.finalassignmentbackend.mapper.SysPermissionMapper;
import com.tutict.finalassignmentbackend.mapper.SysRolePermissionMapper;
import com.tutict.finalassignmentbackend.service.OffenseTypeDictService;
import com.tutict.finalassignmentbackend.service.SysDictService;
import com.tutict.finalassignmentbackend.service.SysPermissionService;
import com.tutict.finalassignmentbackend.service.SysRolePermissionService;
import com.tutict.finalassignmentbackend.service.SysRoleService;
import com.tutict.finalassignmentbackend.service.SysSettingsService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Configuration
public class StandardProductSeedConfig {

    private static final Logger logger = LoggerFactory.getLogger(StandardProductSeedConfig.class);
    private static final String SYSTEM_OPERATOR = "system-seed";

    @Bean
    public CommandLineRunner seedStandardProductBaseline(ProductGovernanceProperties productGovernanceProperties,
                                                         OperationsProperties operationsProperties,
                                                         SysRoleService sysRoleService,
                                                         SysPermissionService sysPermissionService,
                                                         SysRolePermissionService sysRolePermissionService,
                                                         SysSettingsService sysSettingsService,
                                                         SysDictService sysDictService,
                                                         OffenseTypeDictService offenseTypeDictService,
                                                         SysPermissionMapper sysPermissionMapper,
                                                         SysRolePermissionMapper sysRolePermissionMapper,
                                                         SysDictMapper sysDictMapper,
                                                         OffenseTypeDictMapper offenseTypeDictMapper) {
        return _ -> {
            if (!productGovernanceProperties.getSeed().isStandardEnabled()) {
                logger.info("Standard product seed is disabled");
                return;
            }

            ensureRole(sysRoleService, "ADMIN", "System Administrator", RoleType.SYSTEM.getCode(),
                    DataScope.ALL.getCode(), 1, "Platform-level administrator");
            ensureRole(sysRoleService, "CASE_OFFICER", "Case Officer", RoleType.BUSINESS.getCode(),
                    DataScope.DEPARTMENT_AND_SUB.getCode(), 10, "Violation record and archive operator");
            ensureRole(sysRoleService, "REVIEW_OFFICER", "Review Officer", RoleType.BUSINESS.getCode(),
                    DataScope.DEPARTMENT_AND_SUB.getCode(), 20, "Appeal and reconsideration reviewer");
            ensureRole(sysRoleService, "CASHIER", "Cashier", RoleType.BUSINESS.getCode(),
                    DataScope.DEPARTMENT.getCode(), 30, "Fine and payment operator");
            ensureRole(sysRoleService, "AUDITOR", "Auditor", RoleType.BUSINESS.getCode(),
                    DataScope.ALL.getCode(), 40, "Audit and traceability operator");
            ensureRole(sysRoleService, "OPS_ANALYST", "Operations Analyst", RoleType.BUSINESS.getCode(),
                    DataScope.ALL.getCode(), 50, "Dashboard and operations analyst");

            ensurePermission(sysPermissionService, sysPermissionMapper, "OFFENSE_RECORD_MANAGE",
                    "Offense Record Manage", "/api/offenses", 10,
                    "Standard product: violation record management");
            ensurePermission(sysPermissionService, sysPermissionMapper, "DRIVER_VEHICLE_ARCHIVE_MANAGE",
                    "Driver Vehicle Archive Manage", "/api/archives", 20,
                    "Standard product: driver and vehicle archives");
            ensurePermission(sysPermissionService, sysPermissionMapper, "FINE_PAYMENT_PROCESS",
                    "Fine Payment Process", "/api/payments", 30,
                    "Standard product: fine and payment process");
            ensurePermission(sysPermissionService, sysPermissionMapper, "APPEAL_REVIEW_PROCESS",
                    "Appeal Review Process", "/api/appeals", 40,
                    "Standard product: appeal and reconsideration process");
            ensurePermission(sysPermissionService, sysPermissionMapper, "AUDIT_LEDGER_VIEW",
                    "Audit Ledger View", "/api/system/logs", 50,
                    "Standard product: audit ledger and log traceability");
            ensurePermission(sysPermissionService, sysPermissionMapper, "ROLE_PERMISSION_MANAGE",
                    "Role Permission Manage", "/api/system/roles", 60,
                    "Standard product: role and permission governance");
            ensurePermission(sysPermissionService, sysPermissionMapper, "OPERATIONS_DASHBOARD_VIEW",
                    "Operations Dashboard View", "/api/dashboard", 70,
                    "Standard product: operations dashboard");
            ensurePermission(sysPermissionService, sysPermissionMapper, "AI_SEARCH_USE",
                    "AI Search Use", "/api/ai/search", 80,
                    "Controlled AI capability: intelligent retrieval");
            ensurePermission(sysPermissionService, sysPermissionMapper, "AI_SUMMARY_USE",
                    "AI Summary Use", "/api/ai/summary", 90,
                    "Controlled AI capability: intelligent summary");
            ensurePermission(sysPermissionService, sysPermissionMapper, "AI_QA_SUGGEST_USE",
                    "AI QA Suggest Use", "/api/ai/chat", 100,
                    "Controlled AI capability: question answering and workflow suggestions");
            ensurePermission(sysPermissionService, sysPermissionMapper, "BACKUP_RESTORE_MANAGE",
                    "Backup Restore Manage", "/api/system/backup", 110,
                    "Operational baseline: backup and restore management");

            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "OFFENSE_RECORD_MANAGE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "DRIVER_VEHICLE_ARCHIVE_MANAGE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "FINE_PAYMENT_PROCESS");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "APPEAL_REVIEW_PROCESS");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "AUDIT_LEDGER_VIEW");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "ROLE_PERMISSION_MANAGE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "OPERATIONS_DASHBOARD_VIEW");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "AI_SEARCH_USE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "AI_SUMMARY_USE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "AI_QA_SUGGEST_USE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "ADMIN", "BACKUP_RESTORE_MANAGE");

            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "CASE_OFFICER", "OFFENSE_RECORD_MANAGE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "CASE_OFFICER", "DRIVER_VEHICLE_ARCHIVE_MANAGE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "CASE_OFFICER", "AI_SEARCH_USE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "CASE_OFFICER", "AI_SUMMARY_USE");

            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "REVIEW_OFFICER", "APPEAL_REVIEW_PROCESS");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "REVIEW_OFFICER", "AUDIT_LEDGER_VIEW");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "REVIEW_OFFICER", "AI_SEARCH_USE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "REVIEW_OFFICER", "AI_SUMMARY_USE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "REVIEW_OFFICER", "AI_QA_SUGGEST_USE");

            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "CASHIER", "FINE_PAYMENT_PROCESS");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "CASHIER", "BACKUP_RESTORE_MANAGE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "AUDITOR", "AUDIT_LEDGER_VIEW");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "AUDITOR", "BACKUP_RESTORE_MANAGE");
            bindRolePermission(sysRoleService, sysPermissionMapper, sysRolePermissionService, sysRolePermissionMapper, "OPS_ANALYST", "OPERATIONS_DASHBOARD_VIEW");

            ensureDict(sysDictService, sysDictMapper, "product_edition", "GOV", "Gov Edition", "GOV", "Single-tenant private deployment", 10);
            ensureDict(sysDictService, sysDictMapper, "product_edition", "SAAS", "SaaS Edition", "SAAS", "Multi-tenant standardized deployment", 20);
            ensureDict(sysDictService, sysDictMapper, "payment_status", "UNPAID", "Unpaid", "Unpaid", "Fine payment not completed", 10);
            ensureDict(sysDictService, sysDictMapper, "payment_status", "PARTIAL", "Partial", "Partial", "Fine partially paid", 20);
            ensureDict(sysDictService, sysDictMapper, "payment_status", "PAID", "Paid", "Paid", "Fine fully paid", 30);
            ensureDict(sysDictService, sysDictMapper, "payment_status", "OVERDUE", "Overdue", "Overdue", "Fine payment overdue", 40);
            ensureDict(sysDictService, sysDictMapper, "appeal_status", "UNDER_REVIEW", "Under Review", "Under_Review", "Appeal under review", 10);
            ensureDict(sysDictService, sysDictMapper, "appeal_status", "APPROVED", "Approved", "Approved", "Appeal approved", 20);
            ensureDict(sysDictService, sysDictMapper, "appeal_status", "REJECTED", "Rejected", "Rejected", "Appeal rejected", 30);
            ensureDict(sysDictService, sysDictMapper, "ai_capability", "SEARCH", "Intelligent Search", "SEARCH", "Controlled AI search capability", 10);
            ensureDict(sysDictService, sysDictMapper, "ai_capability", "SUMMARY", "Intelligent Summary", "SUMMARY", "Controlled AI summary capability", 20);
            ensureDict(sysDictService, sysDictMapper, "ai_capability", "QA_WORKFLOW", "QA And Workflow Advice", "QA_WORKFLOW", "Controlled AI QA and workflow suggestion capability", 30);

            ensureSetting(sysSettingsService, "product.standard.scope",
                    "[\"违法记录管理\",\"车辆/驾驶人档案\",\"罚款与缴费流程\",\"申诉与复核流程\",\"审核台账与日志审计\",\"角色权限\",\"运营看板\"]",
                    "JSON", "product", "Standard product scope", false, false, 10);
            ensureSetting(sysSettingsService, "product.edition.mode", productGovernanceProperties.getEditionMode().name(),
                    "String", "product", "Current delivery edition mode", false, false, 20);
            ensureSetting(sysSettingsService, "product.tenant.isolation.enabled",
                    Boolean.toString(productGovernanceProperties.isTenantIsolationEnabled()),
                    "Boolean", "product", "Tenant and organization isolation guardrail", false, false, 30);
            ensureSetting(sysSettingsService, "product.ai.enabled",
                    Boolean.toString(productGovernanceProperties.getAi().isEnabled()),
                    "Boolean", "ai", "Global AI capability switch", false, false, 40);
            ensureSetting(sysSettingsService, "product.ai.advisory.only",
                    Boolean.toString(productGovernanceProperties.getAi().isAdvisoryOnly()),
                    "Boolean", "ai", "AI can only provide suggestions and never final rulings", false, false, 50);
            ensureSetting(sysSettingsService, "product.ai.traceable.output",
                    Boolean.toString(productGovernanceProperties.getAi().isTraceableOutput()),
                    "Boolean", "ai", "All AI outputs must be traceable", false, false, 60);
            ensureSetting(sysSettingsService, "product.ai.display.sources",
                    Boolean.toString(productGovernanceProperties.getAi().isDisplaySources()),
                    "Boolean", "ai", "AI outputs must display references", false, false, 70);
            ensureSetting(sysSettingsService, "product.ai.redact.sensitive.data",
                    Boolean.toString(productGovernanceProperties.getAi().isRedactSensitiveData()),
                    "Boolean", "ai", "Sensitive data masking before model interaction", false, false, 80);
            ensureSetting(sysSettingsService, "product.ai.auditable.configuration",
                    Boolean.toString(productGovernanceProperties.getAi().isAuditableConfiguration()),
                    "Boolean", "ai", "Prompt, knowledge base and model configuration auditability", false, false, 90);
            ensureSetting(sysSettingsService, "product.ai.tenant.can.disable",
                    Boolean.toString(productGovernanceProperties.getAi().isTenantCanDisable()),
                    "Boolean", "ai", "Tenant-level AI disable switch", false, false, 100);
            ensureSetting(sysSettingsService, "operations.backup.directory", operationsProperties.getBackupDirectory(),
                    "String", "operations", "Default operational backup directory", true, false, 110);
            ensureSetting(sysSettingsService, "operations.backup.retention.days",
                    Integer.toString(operationsProperties.getBackupRetentionDays()),
                    "Number", "operations", "Default operational backup retention days", true, false, 120);

            ensureOffenseType(offenseTypeDictService, offenseTypeDictMapper, "SPEEDING", "Speeding", "Traffic",
                    new BigDecimal("200.00"), 3, "Moderate", "Road Traffic Safety Law");
            ensureOffenseType(offenseTypeDictService, offenseTypeDictMapper, "RED_LIGHT", "Running Red Light", "Traffic",
                    new BigDecimal("200.00"), 6, "Severe", "Road Traffic Safety Law");
            ensureOffenseType(offenseTypeDictService, offenseTypeDictMapper, "ILLEGAL_PARKING", "Illegal Parking", "Traffic",
                    new BigDecimal("150.00"), 0, "Minor", "Road Traffic Safety Law");

            logger.info("Standard product baseline seed completed");
        };
    }

    private void ensureRole(SysRoleService sysRoleService, String roleCode, String roleName, String roleType,
                            String dataScope, int sortOrder, String description) {
        if (sysRoleService.findByRoleCode(roleCode) != null) {
            return;
        }
        SysRole role = new SysRole();
        role.setRoleCode(roleCode);
        role.setRoleName(roleName);
        role.setRoleType(roleType);
        role.setDataScope(dataScope);
        role.setRoleDescription(description);
        role.setStatus("Active");
        role.setSortOrder(sortOrder);
        role.setCreatedAt(LocalDateTime.now());
        role.setUpdatedAt(LocalDateTime.now());
        role.setCreatedBy(SYSTEM_OPERATOR);
        role.setUpdatedBy(SYSTEM_OPERATOR);
        role.setRemarks("Standard product baseline seed");
        sysRoleService.createSysRole(role);
    }

    private void ensurePermission(SysPermissionService sysPermissionService, SysPermissionMapper sysPermissionMapper,
                                  String permissionCode, String permissionName, String apiPath, int sortOrder,
                                  String description) {
        if (findPermissionByCode(sysPermissionMapper, permissionCode) != null) {
            return;
        }
        SysPermission permission = new SysPermission();
        permission.setParentId(0);
        permission.setPermissionCode(permissionCode);
        permission.setPermissionName(permissionName);
        permission.setPermissionType("API");
        permission.setPermissionDescription(description);
        permission.setApiPath(apiPath);
        permission.setApiMethod("POST");
        permission.setIsVisible(true);
        permission.setIsExternal(false);
        permission.setSortOrder(sortOrder);
        permission.setStatus("Active");
        permission.setCreatedAt(LocalDateTime.now());
        permission.setUpdatedAt(LocalDateTime.now());
        permission.setCreatedBy(SYSTEM_OPERATOR);
        permission.setUpdatedBy(SYSTEM_OPERATOR);
        permission.setRemarks("Standard product baseline seed");
        sysPermissionService.createSysPermission(permission);
    }

    private void bindRolePermission(SysRoleService sysRoleService, SysPermissionMapper sysPermissionMapper,
                                    SysRolePermissionService sysRolePermissionService,
                                    SysRolePermissionMapper sysRolePermissionMapper,
                                    String roleCode, String permissionCode) {
        SysRole role = sysRoleService.findByRoleCode(roleCode);
        SysPermission permission = findPermissionByCode(sysPermissionMapper, permissionCode);
        if (role == null || permission == null) {
            return;
        }
        QueryWrapper<SysRolePermission> wrapper = new QueryWrapper<>();
        wrapper.eq("role_id", role.getRoleId())
                .eq("permission_id", permission.getPermissionId())
                .isNull("deleted_at")
                .last("limit 1");
        if (sysRolePermissionMapper.selectOne(wrapper) != null) {
            return;
        }
        SysRolePermission relation = new SysRolePermission();
        relation.setRoleId(role.getRoleId());
        relation.setPermissionId(permission.getPermissionId());
        relation.setCreatedAt(LocalDateTime.now());
        relation.setCreatedBy(SYSTEM_OPERATOR);
        sysRolePermissionService.createRelation(relation);
    }

    private void ensureDict(SysDictService sysDictService, SysDictMapper sysDictMapper, String dictType,
                            String dictCode, String dictLabel, String dictValue, String description, int sortOrder) {
        if (findDict(sysDictMapper, dictType, dictCode) != null) {
            return;
        }
        SysDict dict = new SysDict();
        dict.setParentId(0);
        dict.setDictType(dictType);
        dict.setDictCode(dictCode);
        dict.setDictLabel(dictLabel);
        dict.setDictValue(dictValue);
        dict.setDictDescription(description);
        dict.setIsDefault(false);
        dict.setIsFixed(true);
        dict.setStatus("Active");
        dict.setSortOrder(sortOrder);
        dict.setCreatedAt(LocalDateTime.now());
        dict.setUpdatedAt(LocalDateTime.now());
        dict.setCreatedBy(SYSTEM_OPERATOR);
        dict.setUpdatedBy(SYSTEM_OPERATOR);
        dict.setRemarks("Standard product baseline seed");
        sysDictService.createSysDict(dict);
    }

    private void ensureSetting(SysSettingsService sysSettingsService, String settingKey, String settingValue,
                               String settingType, String category, String description, boolean editable,
                               boolean encrypted, int sortOrder) {
        if (sysSettingsService.findByKey(settingKey) != null) {
            return;
        }
        SysSettings settings = new SysSettings();
        settings.setSettingKey(settingKey);
        settings.setSettingValue(settingValue);
        settings.setSettingType(settingType);
        settings.setCategory(category);
        settings.setDescription(description);
        settings.setIsEditable(editable);
        settings.setIsEncrypted(encrypted);
        settings.setSortOrder(sortOrder);
        settings.setCreatedAt(LocalDateTime.now());
        settings.setUpdatedAt(LocalDateTime.now());
        settings.setUpdatedBy(SYSTEM_OPERATOR);
        settings.setRemarks("Standard product baseline seed");
        sysSettingsService.createSysSettings(settings);
    }

    private void ensureOffenseType(OffenseTypeDictService offenseTypeDictService,
                                   OffenseTypeDictMapper offenseTypeDictMapper,
                                   String offenseCode, String offenseName, String category,
                                   BigDecimal standardFineAmount, int deductedPoints,
                                   String severityLevel, String legalBasis) {
        if (findOffenseType(offenseTypeDictMapper, offenseCode) != null) {
            return;
        }
        OffenseTypeDict dict = new OffenseTypeDict();
        dict.setOffenseCode(offenseCode);
        dict.setOffenseName(offenseName);
        dict.setCategory(category);
        dict.setDescription("Standard seeded offense type");
        dict.setStandardFineAmount(standardFineAmount);
        dict.setMinFineAmount(standardFineAmount);
        dict.setMaxFineAmount(standardFineAmount);
        dict.setDeductedPoints(deductedPoints);
        dict.setDetentionDays(0);
        dict.setLicenseSuspensionDays(0);
        dict.setSeverityLevel(severityLevel);
        dict.setLegalBasis(legalBasis);
        dict.setStatus("Active");
        dict.setCreatedAt(LocalDateTime.now());
        dict.setUpdatedAt(LocalDateTime.now());
        dict.setRemarks("Standard product baseline seed");
        offenseTypeDictService.createDict(dict);
    }

    private SysPermission findPermissionByCode(SysPermissionMapper sysPermissionMapper, String permissionCode) {
        QueryWrapper<SysPermission> wrapper = new QueryWrapper<>();
        wrapper.eq("permission_code", permissionCode)
                .isNull("deleted_at")
                .last("limit 1");
        return sysPermissionMapper.selectOne(wrapper);
    }

    private SysDict findDict(SysDictMapper sysDictMapper, String dictType, String dictCode) {
        QueryWrapper<SysDict> wrapper = new QueryWrapper<>();
        wrapper.eq("dict_type", dictType)
                .eq("dict_code", dictCode)
                .isNull("deleted_at")
                .last("limit 1");
        return sysDictMapper.selectOne(wrapper);
    }

    private OffenseTypeDict findOffenseType(OffenseTypeDictMapper offenseTypeDictMapper, String offenseCode) {
        QueryWrapper<OffenseTypeDict> wrapper = new QueryWrapper<>();
        wrapper.eq("offense_code", offenseCode)
                .isNull("deleted_at")
                .last("limit 1");
        return offenseTypeDictMapper.selectOne(wrapper);
    }
}
