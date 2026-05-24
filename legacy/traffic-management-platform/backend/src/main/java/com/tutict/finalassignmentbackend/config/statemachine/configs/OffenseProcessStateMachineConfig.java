package com.tutict.finalassignmentbackend.config.statemachine.configs;

import com.tutict.finalassignmentbackend.config.statemachine.events.OffenseProcessEvent;
import com.tutict.finalassignmentbackend.config.statemachine.states.OffenseProcessState;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.statemachine.config.EnableStateMachineFactory;
import org.springframework.statemachine.config.StateMachineConfigurerAdapter;
import org.springframework.statemachine.config.builders.StateMachineConfigurationConfigurer;
import org.springframework.statemachine.config.builders.StateMachineStateConfigurer;
import org.springframework.statemachine.config.builders.StateMachineTransitionConfigurer;
import org.springframework.statemachine.listener.StateMachineListener;
import org.springframework.statemachine.listener.StateMachineListenerAdapter;
import org.springframework.statemachine.state.State;
import org.springframework.statemachine.transition.Transition;

import java.util.EnumSet;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * State machine configuration for offense processing workflow.
 */
@Configuration
@EnableStateMachineFactory(name = "offenseProcessStateMachineFactory")
public class OffenseProcessStateMachineConfig extends StateMachineConfigurerAdapter<OffenseProcessState, OffenseProcessEvent> {

    private static final Logger LOG = Logger.getLogger(OffenseProcessStateMachineConfig.class.getName());

    @Override
    public void configure(StateMachineConfigurationConfigurer<OffenseProcessState, OffenseProcessEvent> config)
            throws Exception {
        config.withConfiguration()
                .autoStartup(true)
                .listener(offenseProcessStateMachineListener());
    }

    @Override
    public void configure(StateMachineStateConfigurer<OffenseProcessState, OffenseProcessEvent> states)
            throws Exception {
        states.withStates()
                .initial(OffenseProcessState.UNPROCESSED)
                .states(EnumSet.allOf(OffenseProcessState.class));
    }

    @Override
    public void configure(StateMachineTransitionConfigurer<OffenseProcessState, OffenseProcessEvent> transitions)
            throws Exception {
        transitions
                // Unprocessed -> Processing
                .withExternal()
                .source(OffenseProcessState.UNPROCESSED)
                .target(OffenseProcessState.PROCESSING)
                .event(OffenseProcessEvent.START_PROCESSING)
                .and()

                // Processing -> Processed
                .withExternal()
                .source(OffenseProcessState.PROCESSING)
                .target(OffenseProcessState.PROCESSED)
                .event(OffenseProcessEvent.COMPLETE_PROCESSING)
                .and()

                // Processed -> Appealing
                .withExternal()
                .source(OffenseProcessState.PROCESSED)
                .target(OffenseProcessState.APPEALING)
                .event(OffenseProcessEvent.SUBMIT_APPEAL)
                .and()

                // Appeal rejected -> Appealing again
                .withExternal()
                .source(OffenseProcessState.APPEAL_REJECTED)
                .target(OffenseProcessState.APPEALING)
                .event(OffenseProcessEvent.SUBMIT_APPEAL)
                .and()

                // Appealing -> Appeal approved
                .withExternal()
                .source(OffenseProcessState.APPEALING)
                .target(OffenseProcessState.APPEAL_APPROVED)
                .event(OffenseProcessEvent.APPROVE_APPEAL)
                .and()

                // Appealing -> Appeal rejected
                .withExternal()
                .source(OffenseProcessState.APPEALING)
                .target(OffenseProcessState.APPEAL_REJECTED)
                .event(OffenseProcessEvent.REJECT_APPEAL)
                .and()

                // Appealing -> Processed (appeal withdrawn)
                .withExternal()
                .source(OffenseProcessState.APPEALING)
                .target(OffenseProcessState.PROCESSED)
                .event(OffenseProcessEvent.WITHDRAW_APPEAL)
                .and()

                // Any active workflow state -> Cancelled
                .withExternal()
                .source(OffenseProcessState.UNPROCESSED)
                .target(OffenseProcessState.CANCELLED)
                .event(OffenseProcessEvent.CANCEL)
                .and()
                .withExternal()
                .source(OffenseProcessState.PROCESSING)
                .target(OffenseProcessState.CANCELLED)
                .event(OffenseProcessEvent.CANCEL)
                .and()
                .withExternal()
                .source(OffenseProcessState.PROCESSED)
                .target(OffenseProcessState.CANCELLED)
                .event(OffenseProcessEvent.CANCEL)
                .and()
                .withExternal()
                .source(OffenseProcessState.APPEALING)
                .target(OffenseProcessState.CANCELLED)
                .event(OffenseProcessEvent.CANCEL)
                .and()
                .withExternal()
                .source(OffenseProcessState.APPEAL_APPROVED)
                .target(OffenseProcessState.CANCELLED)
                .event(OffenseProcessEvent.CANCEL)
                .and()
                .withExternal()
                .source(OffenseProcessState.APPEAL_REJECTED)
                .target(OffenseProcessState.CANCELLED)
                .event(OffenseProcessEvent.CANCEL);
    }

    @Bean
    public StateMachineListener<OffenseProcessState, OffenseProcessEvent> offenseProcessStateMachineListener() {
        return new StateMachineListenerAdapter<OffenseProcessState, OffenseProcessEvent>() {
            @Override
            public void stateChanged(State<OffenseProcessState, OffenseProcessEvent> from,
                                     State<OffenseProcessState, OffenseProcessEvent> to) {
                LOG.log(Level.INFO, "Offense process state changed: {0} -> {1}",
                        new Object[]{from != null ? from.getId() : "null", to != null ? to.getId() : "null"});
            }

            @Override
            public void transition(Transition<OffenseProcessState, OffenseProcessEvent> transition) {
                if (transition.getSource() != null && transition.getTarget() != null && transition.getTrigger() != null) {
                    LOG.log(Level.INFO, "Offense process transition: {0} -> {1} via {2}",
                            new Object[]{transition.getSource().getId(),
                                    transition.getTarget().getId(),
                                    transition.getTrigger().getEvent()});
                }
            }
        };
    }
}
