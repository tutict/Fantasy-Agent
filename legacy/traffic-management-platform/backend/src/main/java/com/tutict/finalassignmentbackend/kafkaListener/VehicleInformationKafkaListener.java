package com.tutict.finalassignmentbackend.kafkaListener;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.service.VehicleInformationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Service;

import java.util.logging.Level;
import java.util.logging.Logger;

@Service
@EnableKafka
public class VehicleInformationKafkaListener {

    private static final Logger log = Logger.getLogger(VehicleInformationKafkaListener.class.getName());

    private final VehicleInformationService vehicleInformationService;
    private final ObjectMapper objectMapper;

    @Autowired
    public VehicleInformationKafkaListener(VehicleInformationService vehicleInformationService,
                                           ObjectMapper objectMapper) {
        this.vehicleInformationService = vehicleInformationService;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "vehicle_create", groupId = "vehicleInformationGroup", concurrency = "3")
    public void onVehicleInformationCreateReceived(@Header(value = KafkaHeaders.RECEIVED_KEY, required = false) byte[] rawKey,
                                                   @Payload String message) {
        String idempotencyKey = asKey(rawKey);
        log.log(Level.INFO, "Received Kafka message for vehicle create, key={0}", idempotencyKey);
        Thread.ofVirtual().start(() -> processMessage(idempotencyKey, message, "create"));
    }

    @KafkaListener(topics = "vehicle_update", groupId = "vehicleInformationGroup", concurrency = "3")
    public void onVehicleInformationUpdateReceived(@Header(value = KafkaHeaders.RECEIVED_KEY, required = false) byte[] rawKey,
                                                   @Payload String message) {
        String idempotencyKey = asKey(rawKey);
        log.log(Level.INFO, "Received Kafka message for vehicle update, key={0}", idempotencyKey);
        Thread.ofVirtual().start(() -> processMessage(idempotencyKey, message, "update"));
    }

    private void processMessage(String idempotencyKey, String message, String action) {
        if (isBlank(idempotencyKey)) {
            log.warning("Received VehicleInformation event without idempotency key, skipping");
            return;
        }
        VehicleInformation payload = deserializeMessage(message);
        try {
            if (payload == null) {
                log.warning("Received VehicleInformation event with empty payload, skipping");
                return;
            }
            if (vehicleInformationService.shouldSkipProcessing(idempotencyKey)) {
                log.log(Level.INFO, "Skipping duplicate VehicleInformation event (key={0}, action={1})",
                        new Object[]{idempotencyKey, action});
                return;
            }
            VehicleInformation result;
            if ("create".equalsIgnoreCase(action)) {
                payload.setVehicleId(null);
                result = vehicleInformationService.createVehicleInformation(payload);
            } else if ("update".equalsIgnoreCase(action)) {
                result = vehicleInformationService.updateVehicleInformation(payload);
            } else {
                log.log(Level.WARNING, "Unsupported VehicleInformation action: {0}", action);
                return;
            }
            vehicleInformationService.markHistorySuccess(idempotencyKey, result.getVehicleId());
            log.info(String.format("VehicleInformation %s action processed successfully (key=%s)", action, idempotencyKey));
        } catch (Exception ex) {
            vehicleInformationService.markHistoryFailure(idempotencyKey, ex.getMessage());
            log.log(Level.SEVERE,
                    String.format("Error processing %s VehicleInformation message (key=%s)", action, idempotencyKey),
                    ex);
            throw ex;
        }
    }

    private VehicleInformation deserializeMessage(String message) {
        try {
            return objectMapper.readValue(message, VehicleInformation.class);
        } catch (Exception ex) {
            log.log(Level.SEVERE, "Failed to deserialize VehicleInformation message: {0}", message);
            return null;
        }
    }

    private String asKey(byte[] rawKey) {
        return rawKey == null ? null : new String(rawKey);
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
