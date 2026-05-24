package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.model.news.TrafficNewsArticle;
import com.tutict.finalassignmentbackend.service.TrafficNewsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/news")
@Tag(name = "Traffic News", description = "Traffic news aggregation endpoints")
@SecurityRequirement(name = "bearerAuth")
public class TrafficNewsController {

    private static final Logger LOG = Logger.getLogger(TrafficNewsController.class.getName());

    private final TrafficNewsService trafficNewsService;

    public TrafficNewsController(TrafficNewsService trafficNewsService) {
        this.trafficNewsService = trafficNewsService;
    }

    @GetMapping("/traffic")
    @Operation(summary = "List traffic news")
    public ResponseEntity<?> listTrafficNews(
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "10") Integer limit) {
        try {
            List<TrafficNewsArticle> articles = trafficNewsService.fetchTrafficNews(keyword, limit);
            return ResponseEntity.ok(articles);
        } catch (IllegalStateException ex) {
            LOG.log(Level.WARNING, "Traffic news request failed", ex);
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(ex.getMessage());
        } catch (Exception ex) {
            LOG.log(Level.SEVERE, "Traffic news aggregation failed", ex);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body("Traffic news aggregation failed");
        }
    }
}
