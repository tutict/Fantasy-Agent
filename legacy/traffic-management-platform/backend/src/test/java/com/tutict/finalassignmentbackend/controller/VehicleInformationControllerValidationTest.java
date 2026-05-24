package com.tutict.finalassignmentbackend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.exception.global.GlobalExceptionHandler;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.DriverVehicleService;
import com.tutict.finalassignmentbackend.service.VehicleInformationService;
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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class VehicleInformationControllerValidationTest {

    private MockMvc mockMvc;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private CurrentUserTrafficSupportService currentUserTrafficSupportService;

    @BeforeEach
    void setUp() {
        VehicleInformationService vehicleInformationService = Mockito.mock(VehicleInformationService.class);
        DriverVehicleService driverVehicleService = Mockito.mock(DriverVehicleService.class);
        currentUserTrafficSupportService = Mockito.mock(CurrentUserTrafficSupportService.class);
        VehicleInformationController controller = new VehicleInformationController(
                vehicleInformationService,
                driverVehicleService,
                currentUserTrafficSupportService);
        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void createVehicleShouldRejectBlankLicensePlate() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "licensePlate", "   ",
                "vehicleType", "SUV"));

        mockMvc.perform(post("/api/vehicles")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("licensePlate")));
    }

    @Test
    void createCurrentUserVehicleShouldRejectBlankLicensePlate() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "licensePlate", "   ",
                "vehicleType", "Sedan"));

        mockMvc.perform(post("/api/vehicles/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("licensePlate")));
    }

    @Test
    void createVehicleShouldRejectOverlongOwnerName() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "licensePlate", "沪A12345",
                "ownerName", "X".repeat(129)));

        mockMvc.perform(post("/api/vehicles")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("ownerName")));
    }

    @Test
    void updateCurrentUserVehicleShouldReturnForbiddenWhenVehicleIsOutsideScope() throws Exception {
        Mockito.when(currentUserTrafficSupportService.updateVehicleForCurrentUser(eq(77L), any()))
                .thenThrow(new IllegalStateException("Vehicle does not belong to current user"));

        String body = objectMapper.writeValueAsString(Map.of(
                "licensePlate", "沪A12345",
                "vehicleType", "SUV"));

        mockMvc.perform(put("/api/vehicles/me/77")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isForbidden());
    }

    @Test
    void deleteCurrentUserVehicleShouldReturnNotFoundWhenVehicleDoesNotExist() throws Exception {
        Mockito.doThrow(new IllegalStateException("Vehicle not found"))
                .when(currentUserTrafficSupportService)
                .deleteVehicleForCurrentUser(77L);

        mockMvc.perform(delete("/api/vehicles/me/77"))
                .andExpect(status().isNotFound());
    }

    @Test
    void listCurrentUserVehiclesShouldReturnConflictWhenProfileHasNoIdCardNumber() throws Exception {
        Mockito.when(currentUserTrafficSupportService.listCurrentUserVehicles(1, 100))
                .thenThrow(new IllegalStateException("Current user profile has no ID card number"));

        mockMvc.perform(get("/api/vehicles/me"))
                .andExpect(status().isConflict());
    }

    @Test
    void bindDriverShouldRejectMissingDriverId() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "relationship", "Owner",
                "isPrimary", true));

        mockMvc.perform(post("/api/vehicles/88/drivers")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("driverId")));
    }

    @Test
    void updateBindingShouldRejectMissingVehicleId() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "driverId", 66,
                "relationship", "Borrower"));

        mockMvc.perform(put("/api/vehicles/bindings/99")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed"))
                .andExpect(jsonPath("$.errors[*].field", hasItem("vehicleId")));
    }
}
