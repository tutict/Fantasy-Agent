package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.config.statemachine.events.AppealAcceptanceEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.AppealProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.OffenseProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.PaymentEvent;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealAcceptanceState;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.OffenseProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.service.AppealRecordService;
import com.tutict.finalassignmentbackend.service.OffenseRecordService;
import com.tutict.finalassignmentbackend.service.PaymentRecordService;
import com.tutict.finalassignmentbackend.service.statemachine.StateMachineService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/workflow")
@Tag(name = "Workflow Engine", description = "Workflow Engine endpoints")
@SecurityRequirement(name = "bearerAuth")
public class WorkflowController {

    private static final Logger LOG = Logger.getLogger(WorkflowController.class.getName());

    private final StateMachineService stateMachineService;
    private final OffenseRecordService offenseRecordService;
    private final PaymentRecordService paymentRecordService;
    private final AppealRecordService appealRecordService;

    public WorkflowController(StateMachineService stateMachineService,
                              OffenseRecordService offenseRecordService,
                              PaymentRecordService paymentRecordService,
                              AppealRecordService appealRecordService) {
        this.stateMachineService = stateMachineService;
        this.offenseRecordService = offenseRecordService;
        this.paymentRecordService = paymentRecordService;
        this.appealRecordService = appealRecordService;
    }

    @PostMapping("/offenses/{offenseId}/events/{event}")
    @Operation(summary = "Trigger Offense Event")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "TRAFFIC_POLICE"})
    public ResponseEntity<OffenseRecord> triggerOffenseEvent(@PathVariable Long offenseId,
                                                             @PathVariable OffenseProcessEvent event) {
        OffenseRecord record = offenseRecordService.findById(offenseId);
        if (record == null) {
            return ResponseEntity.notFound().build();
        }
        if (event == OffenseProcessEvent.SUBMIT_APPEAL
                || event == OffenseProcessEvent.APPROVE_APPEAL
                || event == OffenseProcessEvent.REJECT_APPEAL
                || event == OffenseProcessEvent.WITHDRAW_APPEAL) {
            LOG.log(Level.WARNING,
                    "Offense {0} attempted to use derived appeal event {1} directly; appeal records must drive these transitions",
                    new Object[]{offenseId, event});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        OffenseProcessState currentState = resolveOffenseState(record.getProcessStatus());
        OffenseProcessState newState = stateMachineService.processOffenseState(offenseId, currentState, event);
        if (newState == currentState) {
            LOG.log(Level.WARNING, "Offense {0} event {1} rejected at state {2}", new Object[]{offenseId, event, currentState});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        OffenseRecord updated = offenseRecordService.updateProcessStatus(offenseId, newState);
        return ResponseEntity.ok(updated);
    }

    @PostMapping("/payments/{paymentId}/events/{event}")
    @Operation(summary = "Trigger Payment Event")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "FINANCE"})
    public ResponseEntity<PaymentRecord> triggerPaymentEvent(@PathVariable Long paymentId,
                                                             @PathVariable PaymentEvent event) {
        PaymentRecord record = paymentRecordService.findById(paymentId);
        if (record == null) {
            return ResponseEntity.notFound().build();
        }
        if (event == PaymentEvent.WAIVE_FINE) {
            LOG.log(Level.WARNING,
                    "Payment {0} attempted to use workflow event {1} directly; waivers must use the waiver/refund workflow",
                    new Object[]{paymentId, event});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        PaymentState currentState = resolvePaymentState(record.getPaymentStatus());
        PaymentState newState = stateMachineService.processPaymentState(paymentId, currentState, event);
        if (newState == currentState) {
            LOG.log(Level.WARNING, "Payment {0} event {1} rejected at state {2}", new Object[]{paymentId, event, currentState});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        PaymentRecord updated = paymentRecordService.updatePaymentStatus(paymentId, newState);
        return ResponseEntity.ok(updated);
    }

    @PostMapping("/appeals/{appealId}/events/{event}")
    @Operation(summary = "Trigger Appeal Event")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "APPEAL_REVIEWER"})
    public ResponseEntity<AppealRecord> triggerAppealEvent(@PathVariable Long appealId,
                                                           @PathVariable AppealProcessEvent event) {
        AppealRecord record = appealRecordService.getAppealById(appealId);
        if (record == null) {
            return ResponseEntity.notFound().build();
        }
        if (event == AppealProcessEvent.APPROVE || event == AppealProcessEvent.REJECT) {
            LOG.log(Level.WARNING,
                    "Appeal {0} attempted to use workflow event {1} directly; final decisions must come from review records",
                    new Object[]{appealId, event});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        if (event == AppealProcessEvent.START_REVIEW
                && resolveAppealAcceptanceState(record.getAcceptanceStatus()) != AppealAcceptanceState.ACCEPTED) {
            LOG.log(Level.WARNING, "Appeal {0} cannot start review before acceptance", appealId);
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        AppealProcessState currentState = resolveAppealState(record.getProcessStatus());
        AppealProcessState newState = stateMachineService.processAppealState(appealId, currentState, event);
        if (newState == currentState) {
            LOG.log(Level.WARNING, "Appeal {0} event {1} rejected at state {2}", new Object[]{appealId, event, currentState});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        AppealRecord updated = appealRecordService.updateProcessStatus(appealId, newState);
        return ResponseEntity.ok(updated);
    }

    @PostMapping("/appeals/{appealId}/acceptance-events/{event}")
    @Operation(summary = "Trigger Appeal Acceptance Event")
    @RolesAllowed({"SUPER_ADMIN", "ADMIN", "APPEAL_REVIEWER"})
    public ResponseEntity<AppealRecord> triggerAppealAcceptanceEvent(@PathVariable Long appealId,
                                                                     @PathVariable AppealAcceptanceEvent event,
                                                                     @RequestBody(required = false)
                                                                     AppealAcceptanceActionRequest request) {
        AppealRecord record = appealRecordService.getAppealById(appealId);
        if (record == null) {
            return ResponseEntity.notFound().build();
        }
        if ((event == AppealAcceptanceEvent.REJECT || event == AppealAcceptanceEvent.REQUEST_SUPPLEMENT)
                && (request == null || isBlank(request.getRejectionReason()))) {
            LOG.log(Level.WARNING, "Appeal acceptance {0} requires a rejection reason for event {1}",
                    new Object[]{appealId, event});
            return ResponseEntity.badRequest().body(record);
        }
        if (event == AppealAcceptanceEvent.SUPPLEMENT_COMPLETE
                || event == AppealAcceptanceEvent.RESUBMIT) {
            LOG.log(Level.WARNING,
                    "Appeal acceptance {0} attempted to use self-service event {1} directly; the appellant must submit the update",
                    new Object[]{appealId, event});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        AppealAcceptanceState currentState = resolveAppealAcceptanceState(record.getAcceptanceStatus());
        AppealAcceptanceState newState =
                stateMachineService.processAppealAcceptanceState(appealId, currentState, event);
        if (newState == currentState) {
            LOG.log(Level.WARNING, "Appeal acceptance {0} event {1} rejected at state {2}",
                    new Object[]{appealId, event, currentState});
            return ResponseEntity.status(HttpStatus.CONFLICT).body(record);
        }
        AppealRecord updated = appealRecordService.updateAcceptanceStatus(
                appealId,
                newState,
                request == null ? null : request.getRejectionReason());
        return ResponseEntity.ok(updated);
    }

    private OffenseProcessState resolveOffenseState(String code) {
        OffenseProcessState state = OffenseProcessState.fromCode(code);
        return state != null ? state : OffenseProcessState.UNPROCESSED;
    }

    private PaymentState resolvePaymentState(String code) {
        PaymentState state = PaymentState.fromCode(code);
        return state != null ? state : PaymentState.UNPAID;
    }

    private AppealProcessState resolveAppealState(String code) {
        AppealProcessState state = AppealProcessState.fromCode(code);
        return state != null ? state : AppealProcessState.UNPROCESSED;
    }

    private AppealAcceptanceState resolveAppealAcceptanceState(String code) {
        AppealAcceptanceState state = AppealAcceptanceState.fromCode(code);
        return state != null ? state : AppealAcceptanceState.PENDING;
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    public static class AppealAcceptanceActionRequest {
        private String rejectionReason;

        public String getRejectionReason() {
            return rejectionReason;
        }

        public void setRejectionReason(String rejectionReason) {
            this.rejectionReason = rejectionReason;
        }
    }
}
