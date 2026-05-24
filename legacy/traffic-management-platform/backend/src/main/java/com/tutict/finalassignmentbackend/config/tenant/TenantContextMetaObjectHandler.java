package com.tutict.finalassignmentbackend.config.tenant;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;

@Component
public class TenantContextMetaObjectHandler implements MetaObjectHandler {

    private final TenantAwareSupport tenantAwareSupport;

    public TenantContextMetaObjectHandler(TenantAwareSupport tenantAwareSupport) {
        this.tenantAwareSupport = tenantAwareSupport;
    }

    @Override
    public void insertFill(MetaObject metaObject) {
        String tenantId = tenantAwareSupport.currentTenantId();
        if (StringUtils.hasText(tenantId) && metaObject.hasSetter("tenantId") && getFieldValByName("tenantId", metaObject) == null) {
            setFieldValByName("tenantId", tenantId.trim(), metaObject);
        }
        fillStringField(metaObject, "organizationCode", TenantContextHolder.getOrganizationCode());
        fillStringField(metaObject, "regionCode", TenantContextHolder.getRegionCode());
        fillStringField(metaObject, "departmentCode", TenantContextHolder.getDepartmentCode());
        if (metaObject.hasSetter("updatedAt") && getFieldValByName("updatedAt", metaObject) == null) {
            setFieldValByName("updatedAt", LocalDateTime.now(), metaObject);
        }
        if (metaObject.hasSetter("createdAt") && getFieldValByName("createdAt", metaObject) == null) {
            setFieldValByName("createdAt", LocalDateTime.now(), metaObject);
        }
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        if (metaObject.hasSetter("updatedAt")) {
            setFieldValByName("updatedAt", LocalDateTime.now(), metaObject);
        }
    }

    private void fillStringField(MetaObject metaObject, String fieldName, String value) {
        if (!StringUtils.hasText(value) || !metaObject.hasSetter(fieldName) || getFieldValByName(fieldName, metaObject) != null) {
            return;
        }
        setFieldValByName(fieldName, value.trim(), metaObject);
    }
}
