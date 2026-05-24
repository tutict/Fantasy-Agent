package com.tutict.finalassignmentbackend.service;

import com.tutict.finalassignmentbackend.config.statemachine.events.AppealAcceptanceEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.AppealProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealAcceptanceState;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.DeductionRecord;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.entity.SysUser;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.service.statemachine.StateMachineService;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;

@Service
public class CurrentUserTrafficSupportService {

    private static final int DEFAULT_CURRENT_USER_LIST_PAGE_SIZE = 100;
    private static final int PAYMENT_SCAN_SIZE = 200;
    private static final Duration SELF_SERVICE_PAYMENT_CONFIRM_WINDOW = Duration.ofMinutes(15);
    private static final Pattern EMAIL_PATTERN =
            Pattern.compile("^[\\w.%+-]+@[\\w.-]+\\.[A-Za-z]{2,}$");
    private static final Pattern CONTACT_PATTERN = Pattern.compile("^1\\d{10}$");
    private static final Pattern ID_CARD_PATTERN =
            Pattern.compile("^(\\d{15}|\\d{17}[\\dXx])$");
    private static final Pattern DRIVER_LICENSE_PATTERN = Pattern.compile("^\\d{12}$");
    private static final Set<String> SELF_SERVICE_PAYMENT_CHANNELS = Set.of("APP", "USER_SELF_SERVICE");

    private final SysUserService sysUserService;
    private final DriverInformationService driverInformationService;
    private final OffenseRecordService offenseRecordService;
    private final FineRecordService fineRecordService;
    private final DeductionRecordService deductionRecordService;
    private final VehicleInformationService vehicleInformationService;
    private final AppealRecordService appealRecordService;
    private final PaymentRecordService paymentRecordService;
    private final StateMachineService stateMachineService;

    public CurrentUserTrafficSupportService(SysUserService sysUserService,
                                           DriverInformationService driverInformationService,
                                           OffenseRecordService offenseRecordService,
                                           FineRecordService fineRecordService,
                                           DeductionRecordService deductionRecordService,
                                           VehicleInformationService vehicleInformationService,
                                           AppealRecordService appealRecordService,
                                           PaymentRecordService paymentRecordService,
                                           StateMachineService stateMachineService) {
        this.sysUserService = sysUserService;
        this.driverInformationService = driverInformationService;
        this.offenseRecordService = offenseRecordService;
        this.fineRecordService = fineRecordService;
        this.deductionRecordService = deductionRecordService;
        this.vehicleInformationService = vehicleInformationService;
        this.appealRecordService = appealRecordService;
        this.paymentRecordService = paymentRecordService;
        this.stateMachineService = stateMachineService;
    }

    public SysUser requireCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken) {
            throw new IllegalStateException("Current user is not authenticated");
        }
        SysUser user = sysUserService.findByUsername(authentication.getName());
        if (user == null) {
            throw new IllegalStateException("Current user not found");
        }
        return user;
    }

    public DriverInformation getCurrentDriver() {
        return resolveCurrentUserScope().driver();
    }

    public String getCurrentUserIdCardNumber() {
        return requireCurrentUserIdCardNumber(resolveCurrentUserScope());
    }

    @Transactional
    public SysUser updateCurrentUserProfile(SysUser draft) {
        SysUser currentUser = requireCurrentUser();
        DriverInformation currentDriver = resolveCurrentDriver();
        if (draft == null) {
            throw new IllegalArgumentException("Current user draft must not be null");
        }

        currentUser.setRealName(firstNonBlank(trimToNull(draft.getRealName()), currentUser.getRealName()));
        currentUser.setContactNumber(firstNonBlank(trimToNull(draft.getContactNumber()), currentUser.getContactNumber()));
        currentUser.setGender(firstNonBlank(trimToNull(draft.getGender()), currentUser.getGender()));
        currentUser.setEmail(firstNonBlank(trimToNull(draft.getEmail()), currentUser.getEmail()));
        currentUser.setRemarks(firstNonBlank(trimToNull(draft.getRemarks()), currentUser.getRemarks()));
        currentUser.setUpdatedAt(LocalDateTime.now());

        validateSelfServiceProfile(currentUser, currentDriver);
        SysUser updatedUser = sysUserService.updateSysUser(currentUser);
        syncExistingDriverProfile(updatedUser, currentDriver);
        return updatedUser;
    }

    @Transactional
    public DriverInformation saveCurrentDriver(DriverInformation draft) {
        SysUser user = requireCurrentUser();
        DriverInformation existing = resolveCurrentDriver();
        String previousIdCardNumber = firstNonBlank(
                trimToNull(existing == null ? null : existing.getIdCardNumber()),
                trimToNull(user.getIdCardNumber()));
        DriverInformation merged = existing == null ? new DriverInformation() : existing;
        merged.setName(firstNonBlank(trimToNull(draft == null ? null : draft.getName()),
                existing == null ? null : existing.getName(),
                user.getRealName(),
                user.getUsername()));
        merged.setContactNumber(firstNonBlank(trimToNull(draft == null ? null : draft.getContactNumber()),
                existing == null ? null : existing.getContactNumber(),
                user.getContactNumber()));
        merged.setIdCardNumber(firstNonBlank(trimToNull(draft == null ? null : draft.getIdCardNumber()),
                existing == null ? null : existing.getIdCardNumber(),
                user.getIdCardNumber()));
        merged.setDriverLicenseNumber(firstNonBlank(
                trimToNull(draft == null ? null : draft.getDriverLicenseNumber()),
                existing == null ? null : existing.getDriverLicenseNumber()));
        merged.setGender(firstNonBlank(trimToNull(draft == null ? null : draft.getGender()),
                existing == null ? null : existing.getGender(),
                user.getGender()));
        merged.setEmail(firstNonBlank(trimToNull(draft == null ? null : draft.getEmail()),
                existing == null ? null : existing.getEmail(),
                user.getEmail()));
        merged.setAddress(firstNonBlank(trimToNull(draft == null ? null : draft.getAddress()),
                existing == null ? null : existing.getAddress()));
        merged.setLicenseType(firstNonBlank(trimToNull(draft == null ? null : draft.getLicenseType()),
                existing == null ? null : existing.getLicenseType()));
        merged.setIssuingAuthority(firstNonBlank(trimToNull(draft == null ? null : draft.getIssuingAuthority()),
                existing == null ? null : existing.getIssuingAuthority()));
        merged.setStatus(firstNonBlank(existing == null ? null : existing.getStatus()));
        merged.setBirthdate(firstNonNull(draft == null ? null : draft.getBirthdate(),
                existing == null ? null : existing.getBirthdate()));
        merged.setFirstLicenseDate(firstNonNull(draft == null ? null : draft.getFirstLicenseDate(),
                existing == null ? null : existing.getFirstLicenseDate()));
        merged.setIssueDate(firstNonNull(draft == null ? null : draft.getIssueDate(),
                existing == null ? null : existing.getIssueDate()));
        merged.setExpiryDate(firstNonNull(draft == null ? null : draft.getExpiryDate(),
                existing == null ? null : existing.getExpiryDate()));
        merged.setCurrentPoints(existing == null ? null : existing.getCurrentPoints());
        merged.setTotalDeductedPoints(existing == null ? null : existing.getTotalDeductedPoints());
        merged.setUpdatedAt(LocalDateTime.now());

        validateSelfServiceProfile(user, merged);
        requireStableDriverLink(existing, merged);
        syncCurrentUserProfile(user, merged, previousIdCardNumber);

        if (existing == null) {
            merged.setCreatedAt(LocalDateTime.now());
            return driverInformationService.createDriver(merged);
        }
        return driverInformationService.updateDriver(merged);
    }

    public List<OffenseRecord> listCurrentUserOffenses(int page, int size) {
        DriverInformation driver = resolveCurrentDriver(requireCurrentUser());
        return offenseRecordService.findByDriverIds(new ArrayList<>(resolveCandidateDriverIds(driver)), page, size);
    }

    public List<FineRecord> listCurrentUserFines(int page, int size) {
        List<Long> offenseIds = resolveCurrentUserOffenseIds(resolveCurrentUserScope());
        if (offenseIds.isEmpty()) {
            return List.of();
        }
        return fineRecordService.findByOffenseIds(offenseIds, page, size);
    }

    public List<Long> listCurrentUserFineIds() {
        CurrentUserScope scope = resolveCurrentUserScope();
        List<Long> offenseIds = resolveCurrentUserOffenseIds(scope);
        if (offenseIds.isEmpty()) {
            return List.of();
        }
        return fineRecordService.findIdsByOffenseIds(offenseIds);
    }

    public List<AppealRecord> listCurrentUserAppeals(int page, int size) {
        List<Long> offenseIds = resolveCurrentUserOffenseIds(resolveCurrentUserScope());
        if (offenseIds.isEmpty()) {
            return List.of();
        }
        return appealRecordService.findByOffenseIds(offenseIds, page, size);
    }

    public List<PaymentRecord> listCurrentUserPayments(int page, int size) {
        CurrentUserScope scope = resolveCurrentUserScope();
        return paymentRecordService.searchByPayerIdCard(requireCurrentUserIdCardNumber(scope), page, size);
    }

    public List<PaymentRecord> listCurrentUserPaymentsByFineId(Long fineId, int page, int size) {
        CurrentUserScope scope = resolveCurrentUserScope();
        String currentUserIdCardNumber = requireCurrentUserIdCardNumber(scope);
        if (fineId == null) {
            return paymentRecordService.searchByPayerIdCard(currentUserIdCardNumber, page, size);
        }
        requireCurrentUserFine(fineId, scope);
        return paymentRecordService.findByFineIdAndPayerIdCard(fineId, currentUserIdCardNumber, page, size);
    }

    public List<DeductionRecord> listCurrentUserDeductions(int page, int size) {
        return deductionRecordService.findByDriverIds(
                new ArrayList<>(resolveCurrentUserScope().candidateDriverIds()),
                page,
                size);
    }

    public List<Long> listCurrentUserDeductionIds() {
        return deductionRecordService.findIdsByDriverIds(resolveCurrentUserScope().candidateDriverIds());
    }

    @Transactional
    public PaymentRecord createPaymentForCurrentUser(PaymentRecord draft) {
        Objects.requireNonNull(draft, "Payment record cannot be null");
        CurrentUserScope scope = resolveCurrentUserScope();
        SysUser user = scope.user();
        DriverInformation driver = scope.driver();
        Long fineId = draft.getFineId();
        if (fineId == null || fineId <= 0) {
            throw new IllegalArgumentException("Fine ID must be greater than zero");
        }
        FineRecord fineRecord = requireCurrentUserFineContext(fineId, scope).fineRecord();

        draft.setPayerName(firstNonBlank(
                driver == null ? null : driver.getName(),
                user.getRealName(),
                user.getUsername()));
        draft.setPayerIdCard(requireCurrentUserIdCardNumber(scope));
        ensureNoPendingSelfServicePayment(fineId, draft.getPayerIdCard());
        draft.setPayerContact(firstNonBlank(
                driver == null ? null : driver.getContactNumber(),
                user.getContactNumber()));
        draft.setPaymentChannel(firstNonBlank(trimToNull(draft.getPaymentChannel()), "USER_SELF_SERVICE"));
        draft.setPaymentMethod(firstNonBlank(trimToNull(draft.getPaymentMethod()), "WeChat"));
        draft.setRemarks(firstNonBlank(trimToNull(draft.getRemarks()), "Current user self-service payment"));
        draft.setPaymentStatus(null);
        draft.setRefundAmount(null);
        draft.setRefundTime(null);
        return paymentRecordService.createPaymentRecord(draft);
    }

    @Transactional
    public PaymentRecord confirmCurrentUserPayment(Long paymentId, PaymentRecord confirmationDraft) {
        Objects.requireNonNull(confirmationDraft, "Payment confirmation cannot be null");
        CurrentUserPaymentContext paymentContext = requireCurrentUserPaymentContext(paymentId);
        PaymentRecord paymentRecord = paymentContext.paymentRecord();
        ensureCurrentUserCanConfirmPayment(paymentRecord);

        FineRecord fineRecord = paymentContext.fineRecord();
        BigDecimal remainingPayableAmount = resolveRemainingPayableAmount(fineRecord);
        if (remainingPayableAmount.signum() <= 0) {
            throw new IllegalStateException("Fine is already fully paid");
        }

        BigDecimal paymentAmount = normalizeAmount(paymentRecord.getPaymentAmount());
        if (paymentAmount.signum() <= 0) {
            throw new IllegalStateException("Pending payment order has no payable amount");
        }
        if (paymentAmount.compareTo(remainingPayableAmount) > 0) {
            throw new IllegalStateException("Payment amount exceeds current remaining payable amount");
        }

        PaymentState targetState = paymentAmount.compareTo(remainingPayableAmount) == 0
                ? PaymentState.PAID
                : PaymentState.PARTIAL;
        return paymentRecordService.confirmSelfServicePayment(
                paymentId,
                confirmationDraft.getTransactionId(),
                confirmationDraft.getReceiptUrl(),
                targetState);
    }

    @Transactional
    public PaymentRecord updateCurrentUserPaymentProof(Long paymentId, PaymentRecord proofDraft) {
        Objects.requireNonNull(proofDraft, "Payment proof update cannot be null");
        CurrentUserPaymentContext paymentContext = requireCurrentUserPaymentContext(paymentId);
        FineRecord fineRecord = paymentContext.fineRecord();
        if (Objects.equals(trimToNull(fineRecord.getPaymentStatus()), PaymentState.WAIVED.getCode())) {
            throw new IllegalStateException("Waived fines do not require payment proof updates");
        }
        return paymentRecordService.updateSelfServicePaymentReceiptProof(
                paymentContext.paymentRecord(),
                proofDraft.getReceiptUrl());
    }

    public List<VehicleInformation> listCurrentUserVehicles() {
        return listCurrentUserVehicles(1, DEFAULT_CURRENT_USER_LIST_PAGE_SIZE);
    }

    public List<VehicleInformation> listCurrentUserVehicles(int page, int size) {
        return vehicleInformationService.searchByOwnerIdCard(
                requireCurrentUserIdCardNumber(),
                page,
                size);
    }

    public List<Long> listCurrentUserVehicleIds() {
        return vehicleInformationService.findIdsByOwnerIdCard(requireCurrentUserIdCardNumber());
    }

    @Transactional
    public VehicleInformation createVehicleForCurrentUser(VehicleInformation draft) {
        Objects.requireNonNull(draft, "Vehicle information cannot be null");
        CurrentUserScope scope = resolveCurrentUserScope();
        SysUser user = scope.user();
        DriverInformation driver = scope.driver();
        String ownerIdCardNumber = requireCurrentUserIdCardNumber(scope);

        ensureCurrentUserOwnsVehicleDraft(draft.getOwnerIdCard(), ownerIdCardNumber);
        draft.setOwnerIdCard(ownerIdCardNumber);
        draft.setOwnerName(resolveCurrentOwnerName(user, driver, null));
        draft.setOwnerContact(resolveCurrentOwnerContact(user, driver, null));
        draft.setUpdatedAt(LocalDateTime.now());
        return vehicleInformationService.createVehicleInformation(draft);
    }

    @Transactional
    public VehicleInformation updateVehicleForCurrentUser(Long vehicleId, VehicleInformation draft) {
        Objects.requireNonNull(draft, "Vehicle information cannot be null");
        CurrentUserScope scope = resolveCurrentUserScope();
        SysUser user = scope.user();
        DriverInformation driver = scope.driver();
        VehicleInformation existingVehicle = requireCurrentUserVehicle(vehicleId, scope);
        String ownerIdCardNumber = firstNonBlank(trimToNull(existingVehicle.getOwnerIdCard()),
                requireCurrentUserIdCardNumber(scope));

        ensureCurrentUserOwnsVehicleDraft(draft.getOwnerIdCard(), ownerIdCardNumber);
        draft.setVehicleId(vehicleId);
        draft.setOwnerIdCard(ownerIdCardNumber);
        draft.setOwnerName(resolveCurrentOwnerName(user, driver, existingVehicle));
        draft.setOwnerContact(resolveCurrentOwnerContact(user, driver, existingVehicle));
        draft.setUpdatedAt(LocalDateTime.now());
        return vehicleInformationService.updateVehicleInformation(draft);
    }

    @Transactional
    public void deleteVehicleForCurrentUser(Long vehicleId) {
        VehicleInformation vehicle = requireCurrentUserVehicle(vehicleId);
        vehicleInformationService.deleteVehicleInformation(vehicle.getVehicleId());
    }

    public List<String> getCurrentUserVehiclePlateSuggestions(String prefix, int size) {
        return vehicleInformationService.getLicensePlateAutocompleteSuggestions(
                prefix, size, requireCurrentUserIdCardNumber());
    }

    public List<String> getCurrentUserVehicleTypeSuggestions(String prefix, int size) {
        return vehicleInformationService.getVehicleTypeAutocompleteSuggestions(
                requireCurrentUserIdCardNumber(), prefix, size);
    }

    public AppealRecord createAppealForCurrentUser(AppealRecord appealRecord) {
        Objects.requireNonNull(appealRecord, "Appeal record cannot be null");
        CurrentUserScope scope = resolveCurrentUserScope();
        SysUser user = scope.user();
        DriverInformation driver = scope.driver();
        if (appealRecord.getOffenseId() == null) {
            throw new IllegalArgumentException("Offense ID must not be empty");
        }
        OffenseRecord offense = offenseRecordService.findById(appealRecord.getOffenseId());
        if (offense == null) {
            throw new IllegalStateException("Offense not found");
        }
        if (!scope.candidateDriverIds().contains(offense.getDriverId())) {
            throw new IllegalStateException("Offense does not belong to current user");
        }

        String appellantName = firstNonBlank(
                driver == null ? null : driver.getName(),
                user.getRealName(),
                user.getUsername());
        String appellantIdCard = firstNonBlank(
                driver == null ? null : driver.getIdCardNumber(),
                user.getIdCardNumber());
        String appellantContact = firstNonBlank(
                driver == null ? null : driver.getContactNumber(),
                user.getContactNumber());

        ensureCurrentUserAppealProfileComplete(appellantName, appellantIdCard, appellantContact);

        appealRecord.setAppellantName(appellantName);
        appealRecord.setAppellantIdCard(appellantIdCard);
        appealRecord.setAppellantContact(appellantContact);
        appealRecord.setAppellantEmail(firstNonBlank(
                driver == null ? null : driver.getEmail(),
                user.getEmail()));
        return appealRecordService.createAppeal(appealRecord);
    }

    @Transactional
    public AppealRecord triggerCurrentUserAppealAcceptanceEvent(Long appealId, AppealAcceptanceEvent event) {
        return triggerCurrentUserAppealAcceptanceEvent(appealId, event, null);
    }

    @Transactional
    public AppealRecord triggerCurrentUserAppealAcceptanceEvent(Long appealId,
                                                                AppealAcceptanceEvent event,
                                                                AppealRecord supplementDraft) {
        if (appealId == null || appealId <= 0) {
            throw new IllegalArgumentException("Appeal ID must be greater than zero");
        }
        if (event == null) {
            throw new IllegalArgumentException("Appeal acceptance event must not be empty");
        }
        ensureCurrentUserCanTriggerAcceptanceEvent(event);
        AppealRecord appeal = requireCurrentUserAppeal(appealId, resolveCurrentUserScope());
        ensureCurrentUserEventMatchesAppealState(appeal, event);
        if (hasSupplementPayload(supplementDraft)) {
            appeal = appealRecordService.updateSupplementFieldsSystemManaged(appealId, supplementDraft);
        }
        AppealAcceptanceState currentState = resolveAppealAcceptanceState(appeal.getAcceptanceStatus());
        AppealAcceptanceState newState =
                stateMachineService.processAppealAcceptanceState(appealId, currentState, event);
        if (newState == currentState) {
            throw new IllegalStateException("Appeal acceptance state does not allow this event");
        }
        return appealRecordService.updateAcceptanceStatus(appealId, newState);
    }

    @Transactional
    public AppealRecord triggerCurrentUserAppealProcessEvent(Long appealId, AppealProcessEvent event) {
        if (appealId == null || appealId <= 0) {
            throw new IllegalArgumentException("Appeal ID must be greater than zero");
        }
        if (event == null) {
            throw new IllegalArgumentException("Appeal process event must not be empty");
        }
        if (event != AppealProcessEvent.WITHDRAW) {
            throw new IllegalArgumentException("Current user can only withdraw appeals");
        }

        AppealRecord appeal = requireCurrentUserAppeal(appealId, resolveCurrentUserScope());
        AppealProcessState currentState = resolveAppealProcessState(appeal.getProcessStatus());
        AppealProcessState newState = stateMachineService.processAppealState(appealId, currentState, event);
        if (newState == currentState) {
            throw new IllegalStateException("Appeal process state does not allow this event");
        }
        return appealRecordService.updateProcessStatus(appealId, newState);
    }

    private DriverInformation resolveCurrentDriver() {
        return resolveCurrentDriver(requireCurrentUser());
    }

    private DriverInformation resolveCurrentDriver(SysUser user) {
        return driverInformationService.findLinkedDriverForUser(user);
    }

    private AppealRecord requireCurrentUserAppeal(Long appealId) {
        return requireCurrentUserAppeal(appealId, resolveCurrentUserScope());
    }

    private AppealRecord requireCurrentUserAppeal(Long appealId, CurrentUserScope scope) {
        AppealRecord appeal = appealRecordService.getAppealById(appealId);
        if (appeal == null) {
            throw new IllegalStateException("Appeal not found");
        }
        if (appeal.getOffenseId() == null) {
            throw new IllegalStateException("Appeal offense does not belong to current user");
        }
        OffenseRecord offense = offenseRecordService.findById(appeal.getOffenseId());
        if (offense == null || !scope.candidateDriverIds().contains(offense.getDriverId())) {
            throw new IllegalStateException("Appeal does not belong to current user");
        }
        return appeal;
    }

    private void ensureCurrentUserCanTriggerAcceptanceEvent(AppealAcceptanceEvent event) {
        if (event != AppealAcceptanceEvent.SUPPLEMENT_COMPLETE
                && event != AppealAcceptanceEvent.RESUBMIT) {
            throw new IllegalArgumentException("Current user can only complete supplements or resubmit appeals");
        }
    }

    private void ensureCurrentUserAppealProfileComplete(String appellantName,
                                                        String appellantIdCard,
                                                        String appellantContact) {
        if (trimToNull(appellantName) == null
                || trimToNull(appellantIdCard) == null
                || trimToNull(appellantContact) == null) {
            throw new IllegalStateException(
                    "Complete your personal profile before submitting an appeal");
        }
    }

    private void ensureCurrentUserEventMatchesAppealState(AppealRecord appeal, AppealAcceptanceEvent event) {
        AppealAcceptanceState currentState = resolveAppealAcceptanceState(appeal.getAcceptanceStatus());
        if (currentState == AppealAcceptanceState.NEED_SUPPLEMENT
                && event != AppealAcceptanceEvent.SUPPLEMENT_COMPLETE) {
            throw new IllegalStateException("Appeal is waiting for supplemental materials");
        }
        if (currentState == AppealAcceptanceState.REJECTED
                && event != AppealAcceptanceEvent.RESUBMIT) {
            throw new IllegalStateException("Rejected appeal must be resubmitted");
        }
        if (currentState != AppealAcceptanceState.NEED_SUPPLEMENT
                && currentState != AppealAcceptanceState.REJECTED) {
            throw new IllegalStateException("Appeal is not waiting for current user action");
        }
    }

    private boolean hasSupplementPayload(AppealRecord supplementDraft) {
        return supplementDraft != null
                && (supplementDraft.getAppealReason() != null
                || supplementDraft.getEvidenceDescription() != null
                || supplementDraft.getEvidenceUrls() != null);
    }

    private AppealAcceptanceState resolveAppealAcceptanceState(String code) {
        AppealAcceptanceState state = AppealAcceptanceState.fromCode(code);
        return state != null ? state : AppealAcceptanceState.PENDING;
    }

    private AppealProcessState resolveAppealProcessState(String code) {
        AppealProcessState state = AppealProcessState.fromCode(code);
        return state != null ? state : AppealProcessState.UNPROCESSED;
    }

    private VehicleInformation requireCurrentUserVehicle(Long vehicleId) {
        return requireCurrentUserVehicle(vehicleId, resolveCurrentUserScope());
    }

    private VehicleInformation requireCurrentUserVehicle(Long vehicleId, CurrentUserScope scope) {
        if (vehicleId == null || vehicleId <= 0) {
            throw new IllegalArgumentException("Vehicle ID must be greater than zero");
        }
        VehicleInformation vehicle = vehicleInformationService.getVehicleInformationById(vehicleId);
        if (vehicle == null) {
            throw new IllegalStateException("Vehicle not found");
        }
        String ownerIdCardNumber = trimToNull(vehicle.getOwnerIdCard());
        if (!Objects.equals(ownerIdCardNumber, requireCurrentUserIdCardNumber(scope))) {
            throw new IllegalStateException("Vehicle does not belong to current user");
        }
        return vehicle;
    }

    private FineRecord requireCurrentUserFine(Long fineId) {
        return requireCurrentUserFineContext(fineId, resolveCurrentUserScope()).fineRecord();
    }

    private FineRecord requireCurrentUserFine(Long fineId, CurrentUserScope scope) {
        return requireCurrentUserFineContext(fineId, scope).fineRecord();
    }

    private FineRecord requireCurrentUserFine(Long fineId, Set<Long> candidateDriverIds) {
        return requireCurrentUserFineContext(fineId, candidateDriverIds).fineRecord();
    }

    private CurrentUserFineContext requireCurrentUserFineContext(Long fineId, CurrentUserScope scope) {
        return requireCurrentUserFineContext(fineId, scope.candidateDriverIds());
    }

    private CurrentUserFineContext requireCurrentUserFineContext(Long fineId, Set<Long> candidateDriverIds) {
        if (fineId == null || fineId <= 0) {
            throw new IllegalArgumentException("Fine ID must be greater than zero");
        }
        FineRecord fineRecord = fineRecordService.findById(fineId);
        if (fineRecord == null) {
            throw new IllegalStateException("Fine record not found");
        }
        OffenseRecord offense = offenseRecordService.findById(fineRecord.getOffenseId());
        if (offense == null || !candidateDriverIds.contains(offense.getDriverId())) {
            throw new IllegalStateException("Fine does not belong to current user");
        }
        return new CurrentUserFineContext(fineRecord, offense);
    }

    private PaymentRecord requireCurrentUserPayment(Long paymentId) {
        return requireCurrentUserPaymentContext(paymentId, resolveCurrentUserScope()).paymentRecord();
    }

    private CurrentUserPaymentContext requireCurrentUserPaymentContext(Long paymentId) {
        return requireCurrentUserPaymentContext(paymentId, resolveCurrentUserScope());
    }

    private CurrentUserPaymentContext requireCurrentUserPaymentContext(Long paymentId, CurrentUserScope scope) {
        if (paymentId == null || paymentId <= 0) {
            throw new IllegalArgumentException("Payment ID must be greater than zero");
        }
        PaymentRecord paymentRecord = paymentRecordService.findById(paymentId);
        if (paymentRecord == null) {
            throw new IllegalStateException("Payment record not found");
        }
        if (!Objects.equals(trimToNull(paymentRecord.getPayerIdCard()), trimToNull(requireCurrentUserIdCardNumber(scope)))) {
            throw new IllegalStateException("Payment record does not belong to current user");
        }
        if (paymentRecord.getFineId() == null) {
            throw new IllegalStateException("Payment record is missing the linked fine");
        }
        FineRecord fineRecord = requireCurrentUserFineContext(paymentRecord.getFineId(), scope).fineRecord();
        return new CurrentUserPaymentContext(paymentRecord, fineRecord);
    }

    private void ensureNoPendingSelfServicePayment(Long fineId, String payerIdCard) {
        List<PaymentRecord> paymentRecords = paymentRecordService.findByFineIdAndPayerIdCard(
                fineId,
                payerIdCard,
                1,
                PAYMENT_SCAN_SIZE);
        for (PaymentRecord paymentRecord : paymentRecords) {
            if (isActivePendingSelfServicePayment(paymentRecord, payerIdCard)) {
                throw new IllegalStateException(
                        "Current fine already has a pending self-service payment waiting for confirmation");
            }
        }
    }

    private void ensureCurrentUserCanConfirmPayment(PaymentRecord paymentRecord) {
        if (!isSelfServicePaymentChannel(paymentRecord == null ? null : paymentRecord.getPaymentChannel())) {
            throw new IllegalStateException("Only self-service payment orders can be confirmed by the current user");
        }
        String paymentStatus = trimToNull(paymentRecord == null ? null : paymentRecord.getPaymentStatus());
        if (!Objects.equals(paymentStatus, PaymentState.UNPAID.getCode())) {
            throw new IllegalStateException("Only pending self-service payment orders can be confirmed");
        }
        if (isExpiredPendingSelfServicePayment(paymentRecord)) {
            throw new IllegalStateException("Pending self-service payment order has expired");
        }
    }

    private boolean isActivePendingSelfServicePayment(PaymentRecord paymentRecord, String payerIdCard) {
        if (paymentRecord == null) {
            return false;
        }
        if (!Objects.equals(trimToNull(paymentRecord.getPayerIdCard()), trimToNull(payerIdCard))) {
            return false;
        }
        if (!isSelfServicePaymentChannel(paymentRecord.getPaymentChannel())) {
            return false;
        }
        return Objects.equals(trimToNull(paymentRecord.getPaymentStatus()), PaymentState.UNPAID.getCode())
                && !isExpiredPendingSelfServicePayment(paymentRecord);
    }

    private boolean isExpiredPendingSelfServicePayment(PaymentRecord paymentRecord) {
        LocalDateTime pendingSince = resolvePendingSince(paymentRecord);
        if (pendingSince == null) {
            return false;
        }
        return pendingSince.plus(SELF_SERVICE_PAYMENT_CONFIRM_WINDOW).isBefore(LocalDateTime.now());
    }

    private LocalDateTime resolvePendingSince(PaymentRecord paymentRecord) {
        if (paymentRecord == null) {
            return null;
        }
        return firstNonNull(paymentRecord.getCreatedAt(), paymentRecord.getPaymentTime(), paymentRecord.getUpdatedAt());
    }

    private boolean isSelfServicePaymentChannel(String paymentChannel) {
        String normalizedChannel = trimToNull(paymentChannel);
        return normalizedChannel != null && SELF_SERVICE_PAYMENT_CHANNELS.contains(normalizedChannel.toUpperCase());
    }

    private BigDecimal resolveRemainingPayableAmount(FineRecord fineRecord) {
        if (fineRecord == null) {
            return BigDecimal.ZERO;
        }
        BigDecimal totalAmount = fineRecord.getTotalAmount() != null
                ? fineRecord.getTotalAmount()
                : normalizeAmount(fineRecord.getFineAmount()).add(normalizeAmount(fineRecord.getLateFee()));
        BigDecimal remaining = totalAmount.subtract(normalizeAmount(fineRecord.getPaidAmount()));
        return remaining.signum() < 0 ? BigDecimal.ZERO : remaining;
    }

    private BigDecimal normalizeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }

    private Set<Long> resolveCandidateDriverIds() {
        return resolveCandidateDriverIds(resolveCurrentDriver());
    }

    private Set<Long> resolveCandidateDriverIds(DriverInformation driver) {
        Set<Long> candidateIds = new LinkedHashSet<>();
        if (driver != null && driver.getDriverId() != null) {
            candidateIds.add(driver.getDriverId());
        }
        return candidateIds;
    }

    private List<Long> resolveCurrentUserOffenseIds() {
        return resolveCurrentUserOffenseIds(resolveCurrentUserScope());
    }

    private List<Long> resolveCurrentUserOffenseIds(CurrentUserScope scope) {
        return offenseRecordService.findIdsByDriverIds(new ArrayList<>(scope.candidateDriverIds()));
    }

    public List<Long> listCurrentUserOffenseIds() {
        return resolveCurrentUserOffenseIds(resolveCurrentUserScope());
    }

    private String firstNonBlank(String... candidates) {
        if (candidates == null) {
            return null;
        }
        for (String candidate : candidates) {
            if (candidate != null && !candidate.isBlank()) {
                return candidate;
            }
        }
        return null;
    }

    @SafeVarargs
    private final <T> T firstNonNull(T... candidates) {
        if (candidates == null) {
            return null;
        }
        for (T candidate : candidates) {
            if (candidate != null) {
                return candidate;
            }
        }
        return null;
    }

    private String requireCurrentUserIdCardNumber() {
        return requireCurrentUserIdCardNumber(resolveCurrentUserScope());
    }

    private String requireCurrentUserIdCardNumber(CurrentUserScope scope) {
        return requireCurrentUserIdCardNumber(scope == null ? null : scope.user(), scope == null ? null : scope.driver());
    }

    private String requireCurrentUserIdCardNumber(SysUser user, DriverInformation driver) {
        String idCardNumber = firstNonBlank(
                trimToNull(driver == null ? null : driver.getIdCardNumber()),
                trimToNull(user == null ? null : user.getIdCardNumber()));
        if (idCardNumber == null) {
            throw new IllegalStateException("Current user profile has no ID card number");
        }
        return idCardNumber;
    }

    private CurrentUserScope resolveCurrentUserScope() {
        return resolveCurrentUserScope(requireCurrentUser());
    }

    private CurrentUserScope resolveCurrentUserScope(SysUser user) {
        DriverInformation driver = resolveCurrentDriver(user);
        return new CurrentUserScope(
                user,
                driver,
                firstNonBlank(
                        trimToNull(driver == null ? null : driver.getIdCardNumber()),
                        trimToNull(user == null ? null : user.getIdCardNumber())),
                Set.copyOf(resolveCandidateDriverIds(driver)));
    }

    private void ensureCurrentUserOwnsVehicleDraft(String ownerIdCardNumber, String currentUserIdCardNumber) {
        String normalizedOwnerIdCard = trimToNull(ownerIdCardNumber);
        if (normalizedOwnerIdCard == null) {
            return;
        }
        if (!Objects.equals(normalizedOwnerIdCard, currentUserIdCardNumber)) {
            throw new IllegalStateException("Vehicle owner ID card is outside the current user scope");
        }
    }

    private String resolveCurrentOwnerName(SysUser user, DriverInformation driver, VehicleInformation existingVehicle) {
        return firstNonBlank(
                trimToNull(driver == null ? null : driver.getName()),
                trimToNull(user == null ? null : user.getRealName()),
                trimToNull(user == null ? null : user.getUsername()),
                trimToNull(existingVehicle == null ? null : existingVehicle.getOwnerName()));
    }

    private String resolveCurrentOwnerContact(SysUser user, DriverInformation driver, VehicleInformation existingVehicle) {
        return firstNonBlank(
                trimToNull(driver == null ? null : driver.getContactNumber()),
                trimToNull(user == null ? null : user.getContactNumber()),
                trimToNull(existingVehicle == null ? null : existingVehicle.getOwnerContact()));
    }

    private void syncCurrentUserProfile(SysUser user, DriverInformation driver, String previousIdCardNumber) {
        if (user == null || driver == null) {
            return;
        }
        String nextIdCardNumber = firstNonBlank(driver.getIdCardNumber(), user.getIdCardNumber());
        user.setRealName(firstNonBlank(driver.getName(), user.getRealName()));
        user.setIdCardNumber(nextIdCardNumber);
        user.setContactNumber(firstNonBlank(driver.getContactNumber(), user.getContactNumber()));
        user.setGender(firstNonBlank(driver.getGender(), user.getGender()));
        user.setEmail(firstNonBlank(driver.getEmail(), user.getEmail()));
        user.setUpdatedAt(LocalDateTime.now());
        sysUserService.updateSysUser(user);
        if (!Objects.equals(trimToNull(previousIdCardNumber), trimToNull(nextIdCardNumber))) {
            vehicleInformationService.reassignOwnerIdCard(
                    previousIdCardNumber,
                    nextIdCardNumber,
                    firstNonBlank(driver.getName(), user.getRealName(), user.getUsername()),
                    firstNonBlank(driver.getContactNumber(), user.getContactNumber()));
        }
    }

    private void syncExistingDriverProfile(SysUser user, DriverInformation driver) {
        if (driver == null) {
            return;
        }
        driver.setName(firstNonBlank(user.getRealName(), driver.getName(), user.getUsername()));
        driver.setContactNumber(firstNonBlank(user.getContactNumber(), driver.getContactNumber()));
        driver.setGender(firstNonBlank(user.getGender(), driver.getGender()));
        driver.setEmail(firstNonBlank(user.getEmail(), driver.getEmail()));
        driver.setUpdatedAt(LocalDateTime.now());
        driverInformationService.updateDriver(driver);
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private void requireStableDriverLink(DriverInformation existing, DriverInformation merged) {
        if (existing != null) {
            return;
        }
        if (trimToNull(merged == null ? null : merged.getIdCardNumber()) == null) {
            throw new IllegalArgumentException("ID card number is required to create a driver profile.");
        }
    }

    private void validateSelfServiceProfile(SysUser user, DriverInformation driver) {
        String realName = firstNonBlank(
                trimToNull(driver == null ? null : driver.getName()),
                trimToNull(user == null ? null : user.getRealName()));
        String contactNumber = firstNonBlank(
                trimToNull(driver == null ? null : driver.getContactNumber()),
                trimToNull(user == null ? null : user.getContactNumber()));
        String idCardNumber = firstNonBlank(
                trimToNull(driver == null ? null : driver.getIdCardNumber()),
                trimToNull(user == null ? null : user.getIdCardNumber()));
        String email = firstNonBlank(
                trimToNull(driver == null ? null : driver.getEmail()),
                trimToNull(user == null ? null : user.getEmail()));
        String driverLicenseNumber = trimToNull(driver == null ? null : driver.getDriverLicenseNumber());

        if (realName != null && (realName.length() < 2 || realName.length() > 50)) {
            throw new IllegalArgumentException("Name must be between 2 and 50 characters.");
        }
        if (contactNumber != null && !CONTACT_PATTERN.matcher(contactNumber).matches()) {
            throw new IllegalArgumentException("Enter a valid 11-digit phone number.");
        }
        if (idCardNumber != null && !ID_CARD_PATTERN.matcher(idCardNumber).matches()) {
            throw new IllegalArgumentException("Enter a valid ID card number (15 or 18 digits).");
        }
        if (email != null && !EMAIL_PATTERN.matcher(email).matches()) {
            throw new IllegalArgumentException("Enter a valid email address.");
        }
        if (driverLicenseNumber != null && !DRIVER_LICENSE_PATTERN.matcher(driverLicenseNumber).matches()) {
            throw new IllegalArgumentException("Enter a valid 12-digit driver license number.");
        }

        ensureUniqueEmail(user, email);
        ensureUniqueIdCard(user, driver, idCardNumber);
        ensureUniqueDriverLicense(driver);
    }

    private void ensureUniqueEmail(SysUser user, String effectiveEmail) {
        String email = trimToNull(effectiveEmail);
        if (email == null) {
            return;
        }
        SysUser existingUser = sysUserService.findByExactEmail(email);
        if (existingUser != null && !Objects.equals(existingUser.getUserId(), user.getUserId())) {
            throw new IllegalArgumentException("Email already exists.");
        }
    }

    private void ensureUniqueIdCard(SysUser user, DriverInformation driver, String effectiveIdCardNumber) {
        String idCardNumber = trimToNull(effectiveIdCardNumber);
        if (idCardNumber == null) {
            return;
        }
        SysUser existingUser = sysUserService.findByExactIdCardNumber(idCardNumber);
        if (existingUser != null && !Objects.equals(existingUser.getUserId(), user.getUserId())) {
            throw new IllegalArgumentException("ID card number already exists.");
        }
        DriverInformation existingDriver = driverInformationService.findByExactIdCardNumber(idCardNumber);
        Long currentDriverId = driver == null ? null : driver.getDriverId();
        if (existingDriver != null && !Objects.equals(existingDriver.getDriverId(), currentDriverId)) {
            throw new IllegalArgumentException("ID card number already exists.");
        }
    }

    private void ensureUniqueDriverLicense(DriverInformation driver) {
        String driverLicenseNumber = trimToNull(driver == null ? null : driver.getDriverLicenseNumber());
        if (driverLicenseNumber == null) {
            return;
        }
        DriverInformation existingDriver = driverInformationService.findByExactDriverLicenseNumber(driverLicenseNumber);
        if (existingDriver != null && !Objects.equals(existingDriver.getDriverId(), driver.getDriverId())) {
            throw new IllegalArgumentException("Driver license number already exists.");
        }
    }

    private record CurrentUserScope(SysUser user,
                                    DriverInformation driver,
                                    String idCardNumber,
                                    Set<Long> candidateDriverIds) {
    }

    private record CurrentUserFineContext(FineRecord fineRecord,
                                          OffenseRecord offenseRecord) {
    }

    private record CurrentUserPaymentContext(PaymentRecord paymentRecord,
                                             FineRecord fineRecord) {
    }
}
