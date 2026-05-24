package com.tutict.finalassignmentbackend.service.statemachine;

import com.tutict.finalassignmentbackend.config.statemachine.events.AppealAcceptanceEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.AppealProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.OffenseProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.PaymentEvent;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealAcceptanceState;
import com.tutict.finalassignmentbackend.config.statemachine.states.AppealProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.OffenseProcessState;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.statemachine.StateMachine;
import org.springframework.statemachine.StateMachineContext;
import org.springframework.statemachine.StateMachineEventResult;
import org.springframework.statemachine.config.StateMachineFactory;
import org.springframework.statemachine.support.DefaultStateMachineContext;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

@Service
public class StateMachineService {

    private static final Logger LOG = Logger.getLogger(StateMachineService.class.getName());

    private final StateMachineFactory<OffenseProcessState, OffenseProcessEvent> offenseProcessStateMachineFactory;
    private final StateMachineFactory<PaymentState, PaymentEvent> paymentStateMachineFactory;
    private final StateMachineFactory<AppealProcessState, AppealProcessEvent> appealProcessStateMachineFactory;
    private final StateMachineFactory<AppealAcceptanceState, AppealAcceptanceEvent> appealAcceptanceStateMachineFactory;

    public StateMachineService(
            @Qualifier("offenseProcessStateMachineFactory")
            StateMachineFactory<OffenseProcessState, OffenseProcessEvent> offenseProcessStateMachineFactory,
            @Qualifier("paymentStateMachineFactory")
            StateMachineFactory<PaymentState, PaymentEvent> paymentStateMachineFactory,
            @Qualifier("appealProcessStateMachineFactory")
            StateMachineFactory<AppealProcessState, AppealProcessEvent> appealProcessStateMachineFactory,
            @Qualifier("appealAcceptanceStateMachineFactory")
            StateMachineFactory<AppealAcceptanceState, AppealAcceptanceEvent> appealAcceptanceStateMachineFactory) {
        this.offenseProcessStateMachineFactory = offenseProcessStateMachineFactory;
        this.paymentStateMachineFactory = paymentStateMachineFactory;
        this.appealProcessStateMachineFactory = appealProcessStateMachineFactory;
        this.appealAcceptanceStateMachineFactory = appealAcceptanceStateMachineFactory;
    }

    public OffenseProcessState processOffenseState(
            Long offenseId,
            OffenseProcessState currentState,
            OffenseProcessEvent event) {
        try {
            StateMachine<OffenseProcessState, OffenseProcessEvent> stateMachine =
                    offenseProcessStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);

            boolean transitioned = dispatchEvent(stateMachine, event);
            if (transitioned) {
                OffenseProcessState newState = stateMachine.getState().getId();
                LOG.log(Level.INFO,
                        "Offense {0} state transition succeeded: {1} -> {2} (event: {3})",
                        new Object[]{offenseId, currentState, newState, event});
                return newState;
            }

            LOG.log(Level.WARNING,
                    "Offense {0} state transition failed from {1} (event: {2})",
                    new Object[]{offenseId, currentState, event});
            return currentState;
        } catch (Exception e) {
            LOG.log(Level.SEVERE,
                    "Offense state transition failed with an exception: " + e.getMessage(),
                    e);
            return currentState;
        }
    }

    public PaymentState processPaymentState(Long fineId, PaymentState currentState, PaymentEvent event) {
        try {
            StateMachine<PaymentState, PaymentEvent> stateMachine = paymentStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);

            boolean transitioned = dispatchEvent(stateMachine, event);
            if (transitioned) {
                PaymentState newState = stateMachine.getState().getId();
                LOG.log(Level.INFO,
                        "Payment {0} state transition succeeded: {1} -> {2} (event: {3})",
                        new Object[]{fineId, currentState, newState, event});
                return newState;
            }

            LOG.log(Level.WARNING,
                    "Payment {0} state transition failed from {1} (event: {2})",
                    new Object[]{fineId, currentState, event});
            return currentState;
        } catch (Exception e) {
            LOG.log(Level.SEVERE,
                    "Payment state transition failed with an exception: " + e.getMessage(),
                    e);
            return currentState;
        }
    }

    public AppealProcessState processAppealState(
            Long appealId,
            AppealProcessState currentState,
            AppealProcessEvent event) {
        try {
            StateMachine<AppealProcessState, AppealProcessEvent> stateMachine =
                    appealProcessStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);

            boolean transitioned = dispatchEvent(stateMachine, event);
            if (transitioned) {
                AppealProcessState newState = stateMachine.getState().getId();
                LOG.log(Level.INFO,
                        "Appeal {0} state transition succeeded: {1} -> {2} (event: {3})",
                        new Object[]{appealId, currentState, newState, event});
                return newState;
            }

            LOG.log(Level.WARNING,
                    "Appeal {0} state transition failed from {1} (event: {2})",
                    new Object[]{appealId, currentState, event});
            return currentState;
        } catch (Exception e) {
            LOG.log(Level.SEVERE,
                    "Appeal state transition failed with an exception: " + e.getMessage(),
                    e);
            return currentState;
        }
    }

    public AppealAcceptanceState processAppealAcceptanceState(
            Long appealId,
            AppealAcceptanceState currentState,
            AppealAcceptanceEvent event) {
        try {
            StateMachine<AppealAcceptanceState, AppealAcceptanceEvent> stateMachine =
                    appealAcceptanceStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);

            boolean transitioned = dispatchEvent(stateMachine, event);
            if (transitioned) {
                AppealAcceptanceState newState = stateMachine.getState().getId();
                LOG.log(Level.INFO,
                        "Appeal acceptance state transition succeeded: {0} -> {1} (appeal: {2}, event: {3})",
                        new Object[]{currentState, newState, appealId, event});
                return newState;
            }

            LOG.log(Level.WARNING,
                    "Appeal acceptance state transition failed from {0} (appeal: {1}, event: {2})",
                    new Object[]{currentState, appealId, event});
            return currentState;
        } catch (Exception e) {
            LOG.log(Level.SEVERE,
                    "Appeal acceptance transition failed with an exception: " + e.getMessage(),
                    e);
            return currentState;
        }
    }

    public boolean canTransitionOffenseState(OffenseProcessState currentState, OffenseProcessEvent event) {
        try {
            StateMachine<OffenseProcessState, OffenseProcessEvent> stateMachine =
                    offenseProcessStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);
            return canTransition(stateMachine, currentState, event);
        } catch (Exception e) {
            LOG.log(Level.WARNING,
                    "Failed to validate offense transition availability: " + e.getMessage(),
                    e);
            return false;
        }
    }

    public boolean canTransitionPaymentState(PaymentState currentState, PaymentEvent event) {
        try {
            StateMachine<PaymentState, PaymentEvent> stateMachine = paymentStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);
            return canTransition(stateMachine, currentState, event);
        } catch (Exception e) {
            LOG.log(Level.WARNING,
                    "Failed to validate payment transition availability: " + e.getMessage(),
                    e);
            return false;
        }
    }

    public boolean canTransitionAppealState(AppealProcessState currentState, AppealProcessEvent event) {
        try {
            StateMachine<AppealProcessState, AppealProcessEvent> stateMachine =
                    appealProcessStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);
            return canTransition(stateMachine, currentState, event);
        } catch (Exception e) {
            LOG.log(Level.WARNING,
                    "Failed to validate appeal transition availability: " + e.getMessage(),
                    e);
            return false;
        }
    }

    public boolean canTransitionAppealAcceptanceState(
            AppealAcceptanceState currentState,
            AppealAcceptanceEvent event) {
        try {
            StateMachine<AppealAcceptanceState, AppealAcceptanceEvent> stateMachine =
                    appealAcceptanceStateMachineFactory.getStateMachine();
            resetStateMachine(stateMachine, currentState);
            return canTransition(stateMachine, currentState, event);
        } catch (Exception e) {
            LOG.log(Level.WARNING,
                    "Failed to validate appeal acceptance transition availability: " + e.getMessage(),
                    e);
            return false;
        }
    }

    private <S, E> void resetStateMachine(StateMachine<S, E> stateMachine, S currentState) {
        stateMachine.getStateMachineAccessor().doWithAllRegions(access ->
                access.resetStateMachineReactively(buildContext(currentState)).block()
        );
    }

    private <S, E> boolean dispatchEvent(StateMachine<S, E> stateMachine, E event) {
        List<StateMachineEventResult<S, E>> results = stateMachine
                .sendEventCollect(Mono.just(MessageBuilder.withPayload(event).build()))
                .block();

        if (results == null || results.isEmpty()) {
            return false;
        }

        for (StateMachineEventResult<S, E> result : results) {
            result.complete().block();
        }

        return results.stream()
                .map(StateMachineEventResult::getResultType)
                .anyMatch(resultType ->
                        resultType == StateMachineEventResult.ResultType.ACCEPTED
                                || resultType == StateMachineEventResult.ResultType.DEFERRED);
    }

    private <S, E> boolean canTransition(StateMachine<S, E> stateMachine, S currentState, E event) {
        return stateMachine.getTransitions().stream()
                .anyMatch(transition ->
                        transition.getSource().getId().equals(currentState)
                                && transition.getTrigger() != null
                                && transition.getTrigger().getEvent().equals(event));
    }

    private <S, E> StateMachineContext<S, E> buildContext(S state) {
        return new DefaultStateMachineContext<>(state, null, null, null);
    }
}
