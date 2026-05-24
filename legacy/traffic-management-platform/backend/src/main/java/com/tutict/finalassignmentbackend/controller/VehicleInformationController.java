package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.DriverVehicle;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import com.tutict.finalassignmentbackend.service.DriverVehicleService;
import com.tutict.finalassignmentbackend.service.VehicleInformationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Supplier;

@RestController
@RequestMapping("/api/vehicles")
@Tag(name = "Vehicle Information", description = "Vehicle Information endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE"})
public class VehicleInformationController {
    private final VehicleInformationService vehicleInformationService;
    private final DriverVehicleService driverVehicleService;
    private final CurrentUserTrafficSupportService currentUserTrafficSupportService;

    public VehicleInformationController(VehicleInformationService vehicleInformationService,
                                        DriverVehicleService driverVehicleService,
                                        CurrentUserTrafficSupportService currentUserTrafficSupportService) {
        this.vehicleInformationService = vehicleInformationService;
        this.driverVehicleService = driverVehicleService;
        this.currentUserTrafficSupportService = currentUserTrafficSupportService;
    }

    @GetMapping("/me")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "USER"})
    @Operation(summary = "List Current User Vehicles")
    public ResponseEntity<List<VehicleInformation>> listCurrentUserVehicles(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int size) {
        try {
            return ResponseEntity.ok(currentUserTrafficSupportService.listCurrentUserVehicles(page, size));
        } catch (IllegalStateException ex) {
            return handleCurrentUserVehicleState(ex);
        }
    }

    @PostMapping("/me")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "USER"})
    @Operation(summary = "Create Current User Vehicle")
    public ResponseEntity<VehicleInformation> createCurrentUserVehicle(
            @Valid @RequestBody VehicleMutationRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        VehicleInformation draft = toVehicleInformation(request);
        try {
            return executeIdempotentVehicleAction(
                    idempotencyKey,
                    draft,
                    "create",
                    HttpStatus.CREATED,
                    () -> currentUserTrafficSupportService.createVehicleForCurrentUser(draft));
        } catch (IllegalStateException ex) {
            return handleCurrentUserVehicleState(ex);
        }
    }

    @PutMapping("/me/{vehicleId}")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "USER"})
    @Operation(summary = "Update Current User Vehicle")
    public ResponseEntity<VehicleInformation> updateCurrentUserVehicle(@PathVariable Long vehicleId,
                                                                       @Valid @RequestBody VehicleMutationRequest request,
                                                                       @RequestHeader(value = "Idempotency-Key",
                                                                               required = false) String idempotencyKey) {
        VehicleInformation draft = toVehicleInformation(request);
        try {
            return executeIdempotentVehicleAction(
                    idempotencyKey,
                    draft,
                    "update",
                    HttpStatus.OK,
                    () -> currentUserTrafficSupportService.updateVehicleForCurrentUser(vehicleId, draft));
        } catch (IllegalStateException ex) {
            return handleCurrentUserVehicleState(ex);
        }
    }

    @DeleteMapping("/me/{vehicleId}")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "USER"})
    @Operation(summary = "Delete Current User Vehicle")
    public ResponseEntity<Void> deleteCurrentUserVehicle(@PathVariable Long vehicleId) {
        try {
            currentUserTrafficSupportService.deleteVehicleForCurrentUser(vehicleId);
            return ResponseEntity.noContent().build();
        } catch (IllegalStateException ex) {
            return handleCurrentUserVehicleState(ex);
        }
    }

    @PostMapping
    @Operation(summary = "Create Vehicle")
    public ResponseEntity<VehicleInformation> createVehicle(
                                                            @Valid @RequestBody VehicleMutationRequest request,
                                                            @RequestHeader(value = "Idempotency-Key", required = false)
                                                            String idempotencyKey) {
        VehicleInformation draft = toVehicleInformation(request);
        return executeIdempotentVehicleAction(
                idempotencyKey,
                draft,
                "create",
                HttpStatus.CREATED,
                () -> vehicleInformationService.createVehicleInformation(draft));
    }

    @PutMapping("/{vehicleId}")
    @Operation(summary = "Update Vehicle")
    public ResponseEntity<VehicleInformation> updateVehicle(@PathVariable Long vehicleId,
                                                            @Valid @RequestBody VehicleMutationRequest request,
                                                            @RequestHeader(value = "Idempotency-Key", required = false)
                                                            String idempotencyKey) {
        VehicleInformation draft = toVehicleInformation(request);
        draft.setVehicleId(vehicleId);
        return executeIdempotentVehicleAction(
                idempotencyKey,
                draft,
                "update",
                HttpStatus.OK,
                () -> vehicleInformationService.updateVehicleInformation(draft));
    }

    @DeleteMapping("/{vehicleId}")
    @Operation(summary = "Delete Vehicle")
    public ResponseEntity<Void> deleteVehicle(@PathVariable Long vehicleId) {
        vehicleInformationService.deleteVehicleInformation(vehicleId);
        return ResponseEntity.noContent().build();
    }

    @DeleteMapping("/license/{licensePlate}")
    @Operation(summary = "Delete Vehicle By License")
    public ResponseEntity<Void> deleteVehicleByLicense(@PathVariable String licensePlate) {
        vehicleInformationService.deleteVehicleInformationByLicensePlate(licensePlate);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{vehicleId}")
    @Operation(summary = "Get Vehicle")
    public ResponseEntity<VehicleInformation> getVehicle(@PathVariable Long vehicleId) {
        VehicleInformation vehicle = vehicleInformationService.getVehicleInformationById(vehicleId);
        return vehicle == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(vehicle);
    }

    @GetMapping
    @Operation(summary = "List Vehicles")
    public ResponseEntity<List<VehicleInformation>> listVehicles(@RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(vehicleInformationService.listVehicles(page, size));
    }

    @GetMapping("/search/license")
    @Operation(summary = "Search By License")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE"})
    public ResponseEntity<VehicleInformation> searchByLicense(@RequestParam String licensePlate) {
        VehicleInformation vehicle = vehicleInformationService.getVehicleInformationByLicensePlate(licensePlate);
        return vehicle == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(vehicle);
    }

    @GetMapping("/search/owner")
    @Operation(summary = "Search By Owner Id Card")
    public ResponseEntity<List<VehicleInformation>> searchByOwnerIdCard(@RequestParam String idCard,
                                                                        @RequestParam(defaultValue = "1") int page,
                                                                        @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(vehicleInformationService.searchByOwnerIdCard(idCard, page, size));
    }

    @GetMapping("/search/type")
    @Operation(summary = "Search By Type")
    public ResponseEntity<List<VehicleInformation>> searchByType(@RequestParam String type,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(vehicleInformationService.searchByVehicleType(type, page, size));
    }

    @GetMapping("/search/owner/name")
    @Operation(summary = "Search By Owner Name")
    public ResponseEntity<List<VehicleInformation>> searchByOwnerName(@RequestParam String ownerName,
                                                                      @RequestParam(defaultValue = "1") int page,
                                                                      @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(vehicleInformationService.searchByOwnerName(ownerName, page, size));
    }

    @GetMapping("/search/status")
    @Operation(summary = "Search By Status")
    public ResponseEntity<List<VehicleInformation>> searchByStatus(@RequestParam String status,
                                                                   @RequestParam(defaultValue = "1") int page,
                                                                   @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(vehicleInformationService.searchByStatus(status, page, size));
    }

    @GetMapping("/search/general")
    @Operation(summary = "Search Vehicles")
    public ResponseEntity<List<VehicleInformation>> searchVehicles(@RequestParam String keywords,
                                                                   @RequestParam(defaultValue = "1") int page,
                                                                   @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(vehicleInformationService.searchVehicles(keywords, page, size));
    }

    @PostMapping("/{vehicleId}/drivers")
    @Operation(summary = "Bind Driver")
    public ResponseEntity<DriverVehicle> bindDriver(@PathVariable Long vehicleId,
                                                    @Valid @RequestBody CreateDriverBindingRequest request,
                                                    @RequestHeader(value = "Idempotency-Key", required = false)
                                                    String idempotencyKey) {
        DriverVehicle draft = toDriverVehicle(request);
        draft.setVehicleId(vehicleId);
        return executeIdempotentBindingAction(
                idempotencyKey,
                draft,
                "create",
                HttpStatus.CREATED,
                () -> driverVehicleService.createBinding(draft));
    }

    @GetMapping("/{vehicleId}/drivers")
    @Operation(summary = "List Bindings")
    public ResponseEntity<List<DriverVehicle>> listBindings(@PathVariable Long vehicleId,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(driverVehicleService.findByVehicleId(vehicleId, page, size));
    }

    @DeleteMapping("/bindings/{bindingId}")
    @Operation(summary = "Delete Binding")
    public ResponseEntity<Void> deleteBinding(@PathVariable Long bindingId) {
        driverVehicleService.deleteBinding(bindingId);
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/bindings/{bindingId}")
    @Operation(summary = "Update Binding")
    public ResponseEntity<DriverVehicle> updateBinding(@PathVariable Long bindingId,
                                                       @Valid @RequestBody UpdateDriverBindingRequest request,
                                                       @RequestHeader(value = "Idempotency-Key", required = false)
                                                       String idempotencyKey) {
        DriverVehicle draft = toDriverVehicle(request);
        draft.setId(bindingId);
        return executeIdempotentBindingAction(
                idempotencyKey,
                draft,
                "update",
                HttpStatus.OK,
                () -> driverVehicleService.updateBinding(draft));
    }

    @GetMapping("/bindings/{bindingId}")
    @Operation(summary = "Get Binding")
    public ResponseEntity<DriverVehicle> getBinding(@PathVariable Long bindingId) {
        DriverVehicle binding = driverVehicleService.findById(bindingId);
        return binding == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(binding);
    }

    @GetMapping("/bindings")
    @Operation(summary = "List Bindings Overview")
    public ResponseEntity<List<DriverVehicle>> listBindingsOverview(@RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(driverVehicleService.findAll(page, size));
    }

    @GetMapping("/drivers/{driverId}/vehicles")
    @Operation(summary = "List By Driver")
    public ResponseEntity<List<DriverVehicle>> listByDriver(@PathVariable Long driverId,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(driverVehicleService.findByDriverId(driverId, page, size));
    }

    @GetMapping("/drivers/{driverId}/vehicles/primary")
    @Operation(summary = "Primary Binding")
    public ResponseEntity<List<DriverVehicle>> primaryBinding(@PathVariable Long driverId) {
        return ResponseEntity.ok(driverVehicleService.findPrimaryBinding(driverId));
    }

    @GetMapping("/bindings/search/relationship")
    @Operation(summary = "Search By Relationship")
    public ResponseEntity<List<DriverVehicle>> searchByRelationship(@RequestParam String relationship,
                                                                    @RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(driverVehicleService.searchByRelationship(relationship, page, size));
    }

    @GetMapping("/me/autocomplete/plates")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "USER"})
    @Operation(summary = "Current User Plate Autocomplete")
    public ResponseEntity<List<String>> currentUserPlateAutocomplete(@RequestParam String prefix,
                                                                     @RequestParam(defaultValue = "10") int size) {
        try {
            return ResponseEntity.ok(currentUserTrafficSupportService.getCurrentUserVehiclePlateSuggestions(prefix, size));
        } catch (IllegalStateException ex) {
            return handleCurrentUserVehicleState(ex);
        }
    }

    @GetMapping("/me/autocomplete/types")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "USER"})
    @Operation(summary = "Current User Vehicle Type Autocomplete")
    public ResponseEntity<List<String>> currentUserVehicleTypeAutocomplete(@RequestParam String prefix,
                                                                           @RequestParam(defaultValue = "10") int size) {
        try {
            return ResponseEntity.ok(currentUserTrafficSupportService.getCurrentUserVehicleTypeSuggestions(prefix, size));
        } catch (IllegalStateException ex) {
            return handleCurrentUserVehicleState(ex);
        }
    }

    @GetMapping("/search/license/global")
    @Operation(summary = "Global Plate Suggestions")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "FINANCE"})
    public ResponseEntity<List<String>> globalPlateSuggestions(@RequestParam String prefix,
                                                               @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(vehicleInformationService.getVehicleInformationByLicensePlateGlobally(prefix, size));
    }

    @GetMapping("/autocomplete/plates")
    @Operation(summary = "Plate Autocomplete")
    public ResponseEntity<List<String>> plateAutocomplete(@RequestParam String prefix,
                                                          @RequestParam(defaultValue = "10") int size,
                                                          @RequestParam String idCard) {
        return ResponseEntity.ok(vehicleInformationService.getLicensePlateAutocompleteSuggestions(prefix, size, idCard));
    }

    @GetMapping("/autocomplete/types")
    @Operation(summary = "Vehicle Type Autocomplete")
    public ResponseEntity<List<String>> vehicleTypeAutocomplete(@RequestParam String idCard,
                                                                @RequestParam String prefix,
                                                                @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(vehicleInformationService.getVehicleTypeAutocompleteSuggestions(idCard, prefix, size));
    }

    @GetMapping("/autocomplete/types/global")
    @Operation(summary = "Vehicle Type Autocomplete Global")
    public ResponseEntity<List<String>> vehicleTypeAutocompleteGlobal(@RequestParam String prefix,
                                                                      @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(vehicleInformationService.getVehicleTypesByPrefixGlobally(prefix, size));
    }

    @GetMapping("/exists/{licensePlate}")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE", "USER"})
    @Operation(summary = "License Exists")
    public ResponseEntity<Map<String, Boolean>> licenseExists(@PathVariable String licensePlate) {
        boolean exists = vehicleInformationService.isLicensePlateExists(licensePlate);
        return ResponseEntity.ok(Map.of("exists", exists));
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private <T> ResponseEntity<T> handleCurrentUserVehicleState(IllegalStateException ex) {
        String message = ex == null || ex.getMessage() == null
                ? ""
                : ex.getMessage().trim().toLowerCase(Locale.ROOT);
        if (message.contains("vehicle not found")) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        if (message.contains("current user is not authenticated")
                || message.contains("current user not found")) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        if (message.contains("does not belong to current user")
                || message.contains("outside the current user scope")) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }
        if (message.contains("profile has no id card number")) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
        throw ex;
    }

    private ResponseEntity<VehicleInformation> executeIdempotentVehicleAction(String idempotencyKey,
                                                                              VehicleInformation draft,
                                                                              String action,
                                                                              HttpStatus successStatus,
                                                                              Supplier<VehicleInformation> operation) {
        boolean useKey = hasKey(idempotencyKey);
        if (useKey) {
            if (vehicleInformationService.shouldSkipProcessing(idempotencyKey)) {
                return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
            }
            vehicleInformationService.checkAndInsertIdempotency(idempotencyKey, draft, action);
        }
        try {
            VehicleInformation saved = operation.get();
            if (useKey && saved != null && saved.getVehicleId() != null) {
                vehicleInformationService.markHistorySuccess(idempotencyKey, saved.getVehicleId());
            }
            return ResponseEntity.status(successStatus).body(saved);
        } catch (RuntimeException ex) {
            if (useKey) {
                vehicleInformationService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            throw ex;
        }
    }

    private ResponseEntity<DriverVehicle> executeIdempotentBindingAction(String idempotencyKey,
                                                                         DriverVehicle draft,
                                                                         String action,
                                                                         HttpStatus successStatus,
                                                                         Supplier<DriverVehicle> operation) {
        boolean useKey = hasKey(idempotencyKey);
        if (useKey) {
            if (driverVehicleService.shouldSkipProcessing(idempotencyKey)) {
                return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
            }
            driverVehicleService.checkAndInsertIdempotency(idempotencyKey, draft, action);
        }
        try {
            DriverVehicle saved = operation.get();
            if (useKey && saved != null && saved.getId() != null) {
                driverVehicleService.markHistorySuccess(idempotencyKey, saved.getId());
            }
            return ResponseEntity.status(successStatus).body(saved);
        } catch (RuntimeException ex) {
            if (useKey) {
                driverVehicleService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            throw ex;
        }
    }

    private VehicleInformation toVehicleInformation(VehicleMutationRequest request) {
        VehicleInformation vehicleInformation = new VehicleInformation();
        vehicleInformation.setLicensePlate(request.getLicensePlate());
        vehicleInformation.setPlateColor(request.getPlateColor());
        vehicleInformation.setVehicleType(request.getVehicleType());
        vehicleInformation.setBrand(request.getBrand());
        vehicleInformation.setModel(request.getModel());
        vehicleInformation.setVehicleColor(request.getVehicleColor());
        vehicleInformation.setEngineNumber(request.getEngineNumber());
        vehicleInformation.setFrameNumber(request.getFrameNumber());
        vehicleInformation.setOwnerName(request.getOwnerName());
        vehicleInformation.setOwnerIdCard(request.getOwnerIdCard());
        vehicleInformation.setOwnerContact(request.getOwnerContact());
        vehicleInformation.setOwnerAddress(request.getOwnerAddress());
        vehicleInformation.setFirstRegistrationDate(request.getFirstRegistrationDate());
        vehicleInformation.setRegistrationDate(request.getRegistrationDate());
        vehicleInformation.setIssuingAuthority(request.getIssuingAuthority());
        vehicleInformation.setStatus(request.getStatus());
        vehicleInformation.setInspectionExpiryDate(request.getInspectionExpiryDate());
        vehicleInformation.setInsuranceExpiryDate(request.getInsuranceExpiryDate());
        vehicleInformation.setRemarks(request.getRemarks());
        return vehicleInformation;
    }

    private DriverVehicle toDriverVehicle(DriverBindingRequest request) {
        DriverVehicle driverVehicle = new DriverVehicle();
        driverVehicle.setDriverId(request.getDriverId());
        driverVehicle.setVehicleId(request.getVehicleId());
        driverVehicle.setRelationship(request.getRelationship());
        driverVehicle.setIsPrimary(request.getIsPrimary());
        driverVehicle.setBindDate(request.getBindDate());
        driverVehicle.setUnbindDate(request.getUnbindDate());
        driverVehicle.setStatus(request.getStatus());
        driverVehicle.setRemarks(request.getRemarks());
        return driverVehicle;
    }

    public static class VehicleMutationRequest {
        @NotBlank(message = "License plate must not be blank")
        @Size(max = 32, message = "License plate must be at most 32 characters")
        private String licensePlate;
        @Size(max = 32, message = "Plate color must be at most 32 characters")
        private String plateColor;
        @Size(max = 64, message = "Vehicle type must be at most 64 characters")
        private String vehicleType;
        @Size(max = 64, message = "Brand must be at most 64 characters")
        private String brand;
        @Size(max = 64, message = "Model must be at most 64 characters")
        private String model;
        @Size(max = 32, message = "Vehicle color must be at most 32 characters")
        private String vehicleColor;
        @Size(max = 64, message = "Engine number must be at most 64 characters")
        private String engineNumber;
        @Size(max = 64, message = "Frame number must be at most 64 characters")
        private String frameNumber;
        @Size(max = 128, message = "Owner name must be at most 128 characters")
        private String ownerName;
        @Size(max = 32, message = "Owner ID card must be at most 32 characters")
        private String ownerIdCard;
        @Size(max = 64, message = "Owner contact must be at most 64 characters")
        private String ownerContact;
        @Size(max = 255, message = "Owner address must be at most 255 characters")
        private String ownerAddress;
        private java.time.LocalDate firstRegistrationDate;
        private java.time.LocalDate registrationDate;
        @Size(max = 128, message = "Issuing authority must be at most 128 characters")
        private String issuingAuthority;
        @Size(max = 32, message = "Status must be at most 32 characters")
        private String status;
        private java.time.LocalDate inspectionExpiryDate;
        private java.time.LocalDate insuranceExpiryDate;
        @Size(max = 255, message = "Remarks must be at most 255 characters")
        private String remarks;

        public String getLicensePlate() {
            return licensePlate;
        }

        public void setLicensePlate(String licensePlate) {
            this.licensePlate = licensePlate;
        }

        public String getPlateColor() {
            return plateColor;
        }

        public void setPlateColor(String plateColor) {
            this.plateColor = plateColor;
        }

        public String getVehicleType() {
            return vehicleType;
        }

        public void setVehicleType(String vehicleType) {
            this.vehicleType = vehicleType;
        }

        public String getBrand() {
            return brand;
        }

        public void setBrand(String brand) {
            this.brand = brand;
        }

        public String getModel() {
            return model;
        }

        public void setModel(String model) {
            this.model = model;
        }

        public String getVehicleColor() {
            return vehicleColor;
        }

        public void setVehicleColor(String vehicleColor) {
            this.vehicleColor = vehicleColor;
        }

        public String getEngineNumber() {
            return engineNumber;
        }

        public void setEngineNumber(String engineNumber) {
            this.engineNumber = engineNumber;
        }

        public String getFrameNumber() {
            return frameNumber;
        }

        public void setFrameNumber(String frameNumber) {
            this.frameNumber = frameNumber;
        }

        public String getOwnerName() {
            return ownerName;
        }

        public void setOwnerName(String ownerName) {
            this.ownerName = ownerName;
        }

        public String getOwnerIdCard() {
            return ownerIdCard;
        }

        public void setOwnerIdCard(String ownerIdCard) {
            this.ownerIdCard = ownerIdCard;
        }

        public String getOwnerContact() {
            return ownerContact;
        }

        public void setOwnerContact(String ownerContact) {
            this.ownerContact = ownerContact;
        }

        public String getOwnerAddress() {
            return ownerAddress;
        }

        public void setOwnerAddress(String ownerAddress) {
            this.ownerAddress = ownerAddress;
        }

        public java.time.LocalDate getFirstRegistrationDate() {
            return firstRegistrationDate;
        }

        public void setFirstRegistrationDate(java.time.LocalDate firstRegistrationDate) {
            this.firstRegistrationDate = firstRegistrationDate;
        }

        public java.time.LocalDate getRegistrationDate() {
            return registrationDate;
        }

        public void setRegistrationDate(java.time.LocalDate registrationDate) {
            this.registrationDate = registrationDate;
        }

        public String getIssuingAuthority() {
            return issuingAuthority;
        }

        public void setIssuingAuthority(String issuingAuthority) {
            this.issuingAuthority = issuingAuthority;
        }

        public String getStatus() {
            return status;
        }

        public void setStatus(String status) {
            this.status = status;
        }

        public java.time.LocalDate getInspectionExpiryDate() {
            return inspectionExpiryDate;
        }

        public void setInspectionExpiryDate(java.time.LocalDate inspectionExpiryDate) {
            this.inspectionExpiryDate = inspectionExpiryDate;
        }

        public java.time.LocalDate getInsuranceExpiryDate() {
            return insuranceExpiryDate;
        }

        public void setInsuranceExpiryDate(java.time.LocalDate insuranceExpiryDate) {
            this.insuranceExpiryDate = insuranceExpiryDate;
        }

        public String getRemarks() {
            return remarks;
        }

        public void setRemarks(String remarks) {
            this.remarks = remarks;
        }
    }

    public abstract static class DriverBindingRequest {
        @NotNull(message = "Driver ID is required")
        @Positive(message = "Driver ID must be greater than zero")
        private Long driverId;
        private Long vehicleId;
        private String relationship;
        private Boolean isPrimary;
        private java.time.LocalDate bindDate;
        private java.time.LocalDate unbindDate;
        private String status;
        private String remarks;

        public Long getDriverId() {
            return driverId;
        }

        public void setDriverId(Long driverId) {
            this.driverId = driverId;
        }

        public Long getVehicleId() {
            return vehicleId;
        }

        public void setVehicleId(Long vehicleId) {
            this.vehicleId = vehicleId;
        }

        public String getRelationship() {
            return relationship;
        }

        public void setRelationship(String relationship) {
            this.relationship = relationship;
        }

        public Boolean getIsPrimary() {
            return isPrimary;
        }

        public void setIsPrimary(Boolean isPrimary) {
            this.isPrimary = isPrimary;
        }

        public java.time.LocalDate getBindDate() {
            return bindDate;
        }

        public void setBindDate(java.time.LocalDate bindDate) {
            this.bindDate = bindDate;
        }

        public java.time.LocalDate getUnbindDate() {
            return unbindDate;
        }

        public void setUnbindDate(java.time.LocalDate unbindDate) {
            this.unbindDate = unbindDate;
        }

        public String getStatus() {
            return status;
        }

        public void setStatus(String status) {
            this.status = status;
        }

        public String getRemarks() {
            return remarks;
        }

        public void setRemarks(String remarks) {
            this.remarks = remarks;
        }
    }

    public static class CreateDriverBindingRequest extends DriverBindingRequest {
    }

    public static class UpdateDriverBindingRequest extends DriverBindingRequest {
        @Override
        @NotNull(message = "Vehicle ID is required")
        @Positive(message = "Vehicle ID must be greater than zero")
        public Long getVehicleId() {
            return super.getVehicleId();
        }
    }
}
