package com.tutict.finalassignmentbackend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.exception.global.GlobalExceptionHandler;
import com.tutict.finalassignmentbackend.service.AppealRecordService;
import com.tutict.finalassignmentbackend.service.AppealReviewService;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.Map;

import static org.hamcrest.Matchers.hasItem;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class AppealManagementControllerValidationTest {

    private MockMvc mockMvc;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private CurrentUserTrafficSupportService currentUserTrafficSupportService;

    @BeforeEach
    void setUp() {
        AppealRecordService appealRecordService = Mockito.mock(AppealRecordService.class);
        AppealReviewService appealReviewService = Mockito.mock(AppealReviewService.class);
        currentUserTrafficSupportService =
                Mockito.mock(CurrentUserTrafficSupportService.class);
        AppealManagementController controller = new AppealManagementController(
                appealRecordService,
                appealReviewService,
                currentUserTrafficSupportService);
        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void createCurrentUserAppealShouldRejectBlankReason() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "offenseId", 500,
                "appealReason", "   "));

        mockMvc.perform(post("/api/appeals/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("appealReason")));
    }

    @Test
    void createAppealShouldRejectMissingOffenseId() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "appealReason", "Need review"));

        mockMvc.perform(post("/api/appeals")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("offenseId")));
    }

    @Test
    void createReviewShouldRejectBlankReviewLevel() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "reviewLevel", "   ",
                "reviewResult", "Approved"));

        mockMvc.perform(post("/api/appeals/81/reviews")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("reviewLevel")));
    }

    @Test
    void createCurrentUserAppealShouldReturnNotFoundWhenOffenseDoesNotExist() throws Exception {
        Mockito.when(currentUserTrafficSupportService.createAppealForCurrentUser(any()))
                .thenThrow(new IllegalStateException("Offense not found"));

        String body = objectMapper.writeValueAsString(Map.of(
                "offenseId", 500,
                "appealReason", "Need review"));

        mockMvc.perform(post("/api/appeals/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isNotFound());
    }

    @Test
    void listCurrentUserAppealsShouldReturnUnauthorizedWhenCurrentUserIsMissing() throws Exception {
        Mockito.when(currentUserTrafficSupportService.listCurrentUserAppeals(1, 20))
                .thenThrow(new IllegalStateException("Current user not found"));

        mockMvc.perform(get("/api/appeals/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void triggerCurrentUserAppealAcceptanceEventShouldReturnForbiddenWhenAppealIsOutsideScope() throws Exception {
        Mockito.when(currentUserTrafficSupportService.triggerCurrentUserAppealAcceptanceEvent(anyLong(), any(), any()))
                .thenThrow(new IllegalStateException("Appeal does not belong to current user"));

        mockMvc.perform(post("/api/appeals/me/88/acceptance-events/SUPPLEMENT_COMPLETE")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isForbidden());
    }
}
