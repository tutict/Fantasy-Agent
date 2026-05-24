package com.tutict.finalassignmentbackend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.exception.global.GlobalExceptionHandler;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.PaymentRecordService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.Map;

import static org.hamcrest.Matchers.hasItem;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PaymentRecordControllerValidationTest {

    private MockMvc mockMvc;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private CurrentUserTrafficSupportService currentUserTrafficSupportService;

    @BeforeEach
    void setUp() {
        PaymentRecordService paymentRecordService = Mockito.mock(PaymentRecordService.class);
        currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        PaymentRecordController controller = new PaymentRecordController(
                paymentRecordService,
                currentUserTrafficSupportService);
        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void createPaymentShouldRejectMissingPayerName() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "fineId", 901,
                "paymentAmount", 100.00,
                "payerIdCard", "110101199001010033"));

        mockMvc.perform(post("/api/payments")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("payerName")));
    }

    @Test
    void confirmCurrentUserPaymentShouldRejectBlankTransactionId() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "transactionId", "   ",
                "receiptUrl", "https://example.com/proof/902"));

        mockMvc.perform(post("/api/payments/me/902/confirm")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("transactionId")));
    }

    @Test
    void listCurrentUserPaymentsShouldReturnUnauthorizedWhenCurrentUserIsMissing() throws Exception {
        Mockito.when(currentUserTrafficSupportService.listCurrentUserPayments(1, 20))
                .thenThrow(new IllegalStateException("Current user not found"));

        mockMvc.perform(get("/api/payments/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void confirmCurrentUserPaymentShouldReturnNotFoundWhenPaymentDoesNotExist() throws Exception {
        Mockito.when(currentUserTrafficSupportService.confirmCurrentUserPayment(eq(902L), any(PaymentRecord.class)))
                .thenThrow(new IllegalStateException("Payment record not found"));

        String body = objectMapper.writeValueAsString(Map.of(
                "transactionId", "WX-20260410-0003"));

        mockMvc.perform(post("/api/payments/me/902/confirm")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateCurrentUserPaymentProofShouldReturnForbiddenWhenPaymentIsOutsideScope() throws Exception {
        Mockito.when(currentUserTrafficSupportService.updateCurrentUserPaymentProof(eq(902L), any(PaymentRecord.class)))
                .thenThrow(new IllegalStateException("Payment record does not belong to current user"));

        String body = objectMapper.writeValueAsString(Map.of(
                "receiptUrl", "https://example.com/proof/902"));

        mockMvc.perform(post("/api/payments/me/902/proof")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isForbidden());
    }

    @Test
    void createCurrentUserPaymentShouldReturnConflictWhenFineAlreadyHasPendingPayment() throws Exception {
        Mockito.when(currentUserTrafficSupportService.createPaymentForCurrentUser(any(PaymentRecord.class)))
                .thenThrow(new IllegalStateException(
                        "Current fine already has a pending self-service payment waiting for confirmation"));

        String body = objectMapper.writeValueAsString(Map.of(
                "fineId", 901,
                "paymentAmount", 100.00));

        mockMvc.perform(post("/api/payments/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isConflict());
    }
}
