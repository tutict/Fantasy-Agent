package com.tutict.finalassignmentbackend.config.tenant;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class TenantAwareSupport {

    private final ProductGovernanceProperties productGovernanceProperties;
    private final TenantIsolationProperties tenantIsolationProperties;

    public TenantAwareSupport(ProductGovernanceProperties productGovernanceProperties,
                              TenantIsolationProperties tenantIsolationProperties) {
        this.productGovernanceProperties = productGovernanceProperties;
        this.tenantIsolationProperties = tenantIsolationProperties;
    }

    public boolean isIsolationEnabled() {
        return productGovernanceProperties.getEditionMode() == ProductGovernanceProperties.EditionMode.SAAS
                && productGovernanceProperties.isTenantIsolationEnabled();
    }

    public String currentTenantId() {
        String tenantId = TenantContextHolder.getTenantId();
        if (StringUtils.hasText(tenantId)) {
            return tenantId.trim();
        }
        if (!TenantContextHolder.hasContext() && isIsolationEnabled()) {
            return tenantIsolationProperties.getPlatformTenantId();
        }
        return null;
    }

    public <T> QueryWrapper<T> applyTenantScope(QueryWrapper<T> wrapper) {
        if (wrapper == null || !isIsolationEnabled()) {
            return wrapper;
        }
        String tenantId = currentTenantId();
        if (StringUtils.hasText(tenantId)) {
            wrapper.eq("tenant_id", tenantId);
        }
        return wrapper;
    }
}
