package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.service.AuthWsService;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.verifyNoInteractions;

class AuthControllerTest {

    @Test
    void registerUserShouldReturnBadRequestForNullBody() {
        AuthWsService authWsService = Mockito.mock(AuthWsService.class);
        AuthController controller = new AuthController(authWsService);

        CompletableFuture<ResponseEntity<Map<String, String>>> future = controller.registerUser(null);

        assertEquals(HttpStatus.BAD_REQUEST, future.join().getStatusCode());
        assertEquals("Username and password are required", future.join().getBody().get("error"));
        verifyNoInteractions(authWsService);
    }

    @Test
    void loginShouldReturnBadRequestForBlankCredentials() {
        AuthWsService authWsService = Mockito.mock(AuthWsService.class);
        AuthController controller = new AuthController(authWsService);
        AuthWsService.LoginRequest request = new AuthWsService.LoginRequest();
        request.setUsername("  ");
        request.setPassword("");

        CompletableFuture<ResponseEntity<Map<String, Object>>> future = controller.login(request);

        assertEquals(HttpStatus.BAD_REQUEST, future.join().getStatusCode());
        assertEquals("Username and password are required", future.join().getBody().get("error"));
        verifyNoInteractions(authWsService);
    }
}
