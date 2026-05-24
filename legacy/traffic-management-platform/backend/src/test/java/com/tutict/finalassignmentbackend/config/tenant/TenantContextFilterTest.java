package com.tutict.finalassignmentbackend.config.tenant;

import com.tutict.finalassignmentbackend.config.login.jwt.TokenProvider;
import com.tutict.finalassignmentbackend.config.product.ProductGovernanceProperties;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class TenantContextFilterTest {

    @AfterEach
    void clearContext() {
        TenantContextHolder.clear();
    }

    @Test
    void shouldRejectConflictingTenantHeaderWhenAuthenticatedTokenIsPresent() throws Exception {
        TokenProvider tokenProvider = mock(TokenProvider.class);
        TenantContextFilter filter = new TenantContextFilter(saasProperties(), new TenantIsolationProperties(), tokenProvider);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/payments");
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader("Authorization", "Bearer access-token");
        request.addHeader("X-Tenant-Id", "tenant-header");

        when(tokenProvider.validateToken("access-token")).thenReturn(true);
        when(tokenProvider.isAccessToken("access-token")).thenReturn(true);
        when(tokenProvider.getTenantId("access-token")).thenReturn("tenant-token");

        filter.doFilter(request, response, (req, res) -> {
            throw new AssertionError("Filter chain should not continue for conflicting tenant context");
        });

        assertEquals(403, response.getStatus());
        assertTrue(response.getContentAsString().contains("Tenant context header does not match authenticated tenant scope"));
        assertFalse(TenantContextHolder.hasContext());
    }

    @Test
    void shouldUseTokenTenantContextAndClearItAfterRequest() throws Exception {
        TokenProvider tokenProvider = mock(TokenProvider.class);
        TenantContextFilter filter = new TenantContextFilter(saasProperties(), new TenantIsolationProperties(), tokenProvider);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/payments");
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader("Authorization", "Bearer access-token");
        request.addHeader("X-Tenant-Id", "tenant-token");
        request.addHeader("X-Organization-Code", "org-a");

        when(tokenProvider.validateToken("access-token")).thenReturn(true);
        when(tokenProvider.isAccessToken("access-token")).thenReturn(true);
        when(tokenProvider.getTenantId("access-token")).thenReturn("tenant-token");
        when(tokenProvider.getOrganizationCode("access-token")).thenReturn("org-a");
        when(tokenProvider.getRegionCode("access-token")).thenReturn("region-a");
        when(tokenProvider.getDepartmentCode("access-token")).thenReturn("dept-a");

        filter.doFilter(request, response, (req, res) -> {
            assertEquals("tenant-token", TenantContextHolder.getTenantId());
            assertEquals("org-a", TenantContextHolder.getOrganizationCode());
            assertEquals("region-a", TenantContextHolder.getRegionCode());
            assertEquals("dept-a", TenantContextHolder.getDepartmentCode());
        });

        assertEquals(200, response.getStatus());
        assertFalse(TenantContextHolder.hasContext());
    }

    @Test
    void shouldAcceptHeaderTenantContextForAnonymousSaasRequest() throws Exception {
        TokenProvider tokenProvider = mock(TokenProvider.class);
        TenantContextFilter filter = new TenantContextFilter(saasProperties(), new TenantIsolationProperties(), tokenProvider);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/auth/login");
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader("X-Tenant-Id", "tenant-header");

        filter.doFilter(request, response, (req, res) ->
                assertEquals("tenant-header", TenantContextHolder.getTenantId()));

        assertEquals(200, response.getStatus());
        assertFalse(TenantContextHolder.hasContext());
        verifyNoInteractions(tokenProvider);
    }

    @Test
    void shouldPropagateDownstreamIllegalStateException() {
        TokenProvider tokenProvider = mock(TokenProvider.class);
        TenantContextFilter filter = new TenantContextFilter(saasProperties(), new TenantIsolationProperties(), tokenProvider);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/payments");
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader("X-Tenant-Id", "tenant-header");

        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> filter.doFilter(request, response, (req, res) -> {
                    throw new IllegalStateException("business rule rejected");
                }));

        assertEquals("business rule rejected", ex.getMessage());
        assertFalse(TenantContextHolder.hasContext());
    }

    private ProductGovernanceProperties saasProperties() {
        ProductGovernanceProperties properties = new ProductGovernanceProperties();
        properties.setEditionMode(ProductGovernanceProperties.EditionMode.SAAS);
        properties.setTenantIsolationEnabled(true);
        return properties;
    }
}
