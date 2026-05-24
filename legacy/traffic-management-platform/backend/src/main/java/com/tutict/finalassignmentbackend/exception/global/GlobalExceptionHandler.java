package com.tutict.finalassignmentbackend.exception.global;

import com.github.dockerjava.api.exception.UnauthorizedException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import jakarta.ws.rs.ForbiddenException;
import org.apache.kafka.common.errors.ResourceNotFoundException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

@ControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger LOGGER = Logger.getLogger(GlobalExceptionHandler.class.getName());

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleResourceNotFoundException(ResourceNotFoundException ex,
                                                                               HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Resource not found: {0}", ex.getMessage());
        return buildResponse(HttpStatus.NOT_FOUND, safeMessage(ex.getMessage(), "Resource not found"), request, null);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalArgumentException(IllegalArgumentException ex,
                                                                              HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Invalid request: {0}", ex.getMessage());
        return buildResponse(HttpStatus.BAD_REQUEST, safeMessage(ex.getMessage(), "Invalid request"), request, null);
    }

    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalStateException(IllegalStateException ex,
                                                                           HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Invalid request state: {0}", ex.getMessage());
        return buildResponse(HttpStatus.BAD_REQUEST, safeMessage(ex.getMessage(), "Invalid request state"), request, null);
    }

    @ExceptionHandler(UnauthorizedException.class)
    public ResponseEntity<Map<String, Object>> handleUnauthorizedException(UnauthorizedException ex,
                                                                           HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Unauthorized request: {0}", ex.getMessage());
        return buildResponse(HttpStatus.UNAUTHORIZED, "Unauthorized", request, null);
    }

    @ExceptionHandler(ForbiddenException.class)
    public ResponseEntity<Map<String, Object>> handleForbiddenException(ForbiddenException ex,
                                                                        HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Forbidden request: {0}", ex.getMessage());
        return buildResponse(HttpStatus.FORBIDDEN, "Forbidden", request, null);
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<Map<String, Object>> handleDataIntegrityViolationException(
            DataIntegrityViolationException ex,
            HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Data integrity violation: {0}", ex.getMessage());
        return buildResponse(HttpStatus.CONFLICT, "Data integrity violation", request, null);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleMethodArgumentNotValidException(
            MethodArgumentNotValidException ex,
            HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Request validation failed: {0}", ex.getMessage());
        List<Map<String, String>> fieldErrors = ex.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(error -> Map.of(
                        "field", error.getField(),
                        "message", error.getDefaultMessage() == null ? "" : error.getDefaultMessage()))
                .toList();
        return buildResponse(HttpStatus.BAD_REQUEST, "Request validation failed", request, Map.of("errors", fieldErrors));
    }

    @ExceptionHandler(BindException.class)
    public ResponseEntity<Map<String, Object>> handleBindException(BindException ex,
                                                                   HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Request binding failed: {0}", ex.getMessage());
        List<Map<String, String>> fieldErrors = ex.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(error -> Map.of(
                        "field", error.getField(),
                        "message", error.getDefaultMessage() == null ? "" : error.getDefaultMessage()))
                .toList();
        return buildResponse(HttpStatus.BAD_REQUEST, "Request binding failed", request, Map.of("errors", fieldErrors));
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<Map<String, Object>> handleConstraintViolationException(
            ConstraintViolationException ex,
            HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Constraint violation: {0}", ex.getMessage());
        List<Map<String, String>> violations = ex.getConstraintViolations()
                .stream()
                .map(ConstraintViolation::getMessage)
                .map(message -> Map.of("message", message))
                .toList();
        return buildResponse(HttpStatus.BAD_REQUEST, "Constraint violation", request, Map.of("violations", violations));
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<Map<String, Object>> handleMissingServletRequestParameterException(
            MissingServletRequestParameterException ex,
            HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Missing request parameter: {0}", ex.getParameterName());
        return buildResponse(HttpStatus.BAD_REQUEST,
                "Missing request parameter: " + ex.getParameterName(), request, null);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, Object>> handleHttpMessageNotReadableException(
            HttpMessageNotReadableException ex,
            HttpServletRequest request) {
        LOGGER.log(Level.WARNING, "Request body is missing or unreadable: {0}", ex.getMessage());
        return buildResponse(HttpStatus.BAD_REQUEST, "Request body is missing or unreadable", request, null);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGenericException(Exception ex,
                                                                      HttpServletRequest request) {
        LOGGER.log(Level.SEVERE, "Unhandled exception", ex);
        return buildResponse(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error", request, null);
    }

    private ResponseEntity<Map<String, Object>> buildResponse(HttpStatus status,
                                                              String message,
                                                              HttpServletRequest request,
                                                              Map<String, Object> extra) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", OffsetDateTime.now().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
        body.put("status", status.value());
        body.put("error", status.getReasonPhrase());
        body.put("message", message);
        body.put("path", request == null ? "" : request.getRequestURI());
        if (extra != null && !extra.isEmpty()) {
            body.putAll(extra);
        }
        return ResponseEntity.status(status).body(body);
    }

    private String safeMessage(String message, String fallback) {
        if (message == null) {
            return fallback;
        }
        String normalized = message.trim();
        return normalized.isEmpty() ? fallback : normalized;
    }
}
