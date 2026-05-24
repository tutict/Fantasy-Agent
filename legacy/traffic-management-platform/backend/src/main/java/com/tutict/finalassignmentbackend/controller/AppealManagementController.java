package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.config.statemachine.events.AppealAcceptanceEvent;
import com.tutict.finalassignmentbackend.config.statemachine.events.AppealProcessEvent;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.AppealReview;
import com.tutict.finalassignmentbackend.service.AppealRecordService;
import com.tutict.finalassignmentbackend.service.AppealReviewService;
import com.tutict.finalassignmentbackend.service.CurrentUserTrafficSupportService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
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
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/appeals")
@Tag(name = "Appeal Management", description = "Appeal Management endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN", "APPEAL_REVIEWER"})
public class AppealManagementController {

    private static final Logger LOG = Logger.getLogger(AppealManagementController.class.getName());

    private final AppealRecordService appealRecordService;
    private final AppealReviewService appealReviewService;
    private final CurrentUserTrafficSupportService currentUserTrafficSupportService;

    public AppealManagementController(AppealRecordService appealRecordService,
                                      AppealReviewService appealReviewService,
                                      CurrentUserTrafficSupportService currentUserTrafficSupportService) {
        this.appealRecordService = appealRecordService;
        this.appealReviewService = appealReviewService;
        this.currentUserTrafficSupportService = currentUserTrafficSupportService;
    }

    @GetMapping("/me")
    @RolesAllowed({"USER"})
    @Operation(summary = "List Current User Appeals")
    public ResponseEntity<List<AppealRecord>> listCurrentUserAppeals(@RequestParam(defaultValue = "1") int page,
                                                                     @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(currentUserTrafficSupportService.listCurrentUserAppeals(page, size));
        } catch (IllegalStateException ex) {
            return handleCurrentUserAppealState(ex);
        }
    }

    @PostMapping("/me")
    @RolesAllowed({"USER"})
    @Operation(summary = "Create Current User Appeal")
    public ResponseEntity<AppealRecord> createCurrentUserAppeal(
            @Valid @RequestBody CurrentUserAppealCreateRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        AppealRecord draft = request.toAppealRecord();
        try {
            return executeIdempotentAppealAction(
                    idempotencyKey,
                    draft,
                    "create",
                    HttpStatus.CREATED,
                    () -> currentUserTrafficSupportService.createAppealForCurrentUser(draft));
        } catch (IllegalStateException ex) {
            return handleCurrentUserAppealState(ex);
        }
    }

    @PostMapping("/me/{appealId}/acceptance-events/{event}")
    @RolesAllowed({"USER"})
    @Operation(summary = "Trigger Current User Appeal Acceptance Event")
    public ResponseEntity<AppealRecord> triggerCurrentUserAppealAcceptanceEvent(@PathVariable Long appealId,
                                                                                @PathVariable AppealAcceptanceEvent event,
                                                                                @Valid @RequestBody(required = false)
                                                                                CurrentUserAppealSubmissionRequest request) {
        try {
            return ResponseEntity.ok(
                    currentUserTrafficSupportService.triggerCurrentUserAppealAcceptanceEvent(
                            appealId,
                            event,
                            request == null ? null : request.toAppealRecord()));
        } catch (IllegalArgumentException ex) {
            LOG.log(Level.WARNING, "Current user appeal acceptance event rejected", ex);
            return ResponseEntity.badRequest().build();
        } catch (IllegalStateException ex) {
            LOG.log(Level.WARNING, "Current user appeal acceptance transition failed", ex);
            return handleCurrentUserAppealState(ex);
        } catch (Exception ex) {
            LOG.log(Level.SEVERE, "Current user appeal acceptance transition failed unexpectedly", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PostMapping("/me/{appealId}/process-events/{event}")
    @RolesAllowed({"USER"})
    @Operation(summary = "Trigger Current User Appeal Process Event")
    public ResponseEntity<AppealRecord> triggerCurrentUserAppealProcessEvent(@PathVariable Long appealId,
                                                                             @PathVariable AppealProcessEvent event) {
        try {
            return ResponseEntity.ok(
                    currentUserTrafficSupportService.triggerCurrentUserAppealProcessEvent(appealId, event));
        } catch (IllegalArgumentException ex) {
            LOG.log(Level.WARNING, "Current user appeal process event rejected", ex);
            return ResponseEntity.badRequest().build();
        } catch (IllegalStateException ex) {
            LOG.log(Level.WARNING, "Current user appeal process transition failed", ex);
            return handleCurrentUserAppealState(ex);
        } catch (Exception ex) {
            LOG.log(Level.SEVERE, "Current user appeal process transition failed unexpectedly", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PostMapping
    @Operation(summary = "Create Appeal")
    public ResponseEntity<AppealRecord> createAppeal(
            @Valid @RequestBody CreateAppealRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        AppealRecord draft = request.toAppealRecord();
        return executeIdempotentAppealAction(
                idempotencyKey,
                draft,
                "create",
                HttpStatus.CREATED,
                () -> appealRecordService.createAppeal(draft));
    }

    @PutMapping("/{appealId}")
    @Operation(summary = "Update Appeal")
    public ResponseEntity<AppealRecord> updateAppeal(@PathVariable Long appealId,
                                                     @RequestBody AppealRecord request,
                                                     @RequestHeader(value = "Idempotency-Key", required = false)
                                                     String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @DeleteMapping("/{appealId}")
    @Operation(summary = "Delete Appeal")
    public ResponseEntity<Void> deleteAppeal(@PathVariable Long appealId) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/{appealId}")
    @Operation(summary = "Get Appeal")
    public ResponseEntity<AppealRecord> getAppeal(@PathVariable Long appealId) {
        AppealRecord record = appealRecordService.getAppealById(appealId);
        return record == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(record);
    }

    @GetMapping
    @Operation(summary = "List Appeals")
    public ResponseEntity<List<AppealRecord>> listAppeals(@RequestParam(required = false) Long offenseId,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(offenseId == null
                ? appealRecordService.listAppeals(page, size)
                : appealRecordService.findByOffenseId(offenseId, page, size));
    }

    @GetMapping("/search/number/prefix")
    @Operation(summary = "Search By Number Prefix")
    public ResponseEntity<List<AppealRecord>> searchByNumberPrefix(@RequestParam String appealNumber,
                                                                   @RequestParam(defaultValue = "1") int page,
                                                                   @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAppealNumberPrefix(appealNumber, page, size));
    }

    @GetMapping("/search/number/fuzzy")
    @Operation(summary = "Search By Number Fuzzy")
    public ResponseEntity<List<AppealRecord>> searchByNumberFuzzy(@RequestParam String appealNumber,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAppealNumberFuzzy(appealNumber, page, size));
    }

    @GetMapping("/search/reason/fuzzy")
    @Operation(summary = "Search By Reason Fuzzy")
    public ResponseEntity<List<AppealRecord>> searchByReasonFuzzy(@RequestParam String appealReason,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAppealReasonFuzzy(appealReason, page, size));
    }

    @GetMapping("/search/appellant/name/prefix")
    @Operation(summary = "Search By Appellant Name Prefix")
    public ResponseEntity<List<AppealRecord>> searchByAppellantNamePrefix(@RequestParam String appellantName,
                                                                          @RequestParam(defaultValue = "1") int page,
                                                                          @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAppellantNamePrefix(appellantName, page, size));
    }

    @GetMapping("/search/appellant/name/fuzzy")
    @Operation(summary = "Search By Appellant Name Fuzzy")
    public ResponseEntity<List<AppealRecord>> searchByAppellantNameFuzzy(@RequestParam String appellantName,
                                                                         @RequestParam(defaultValue = "1") int page,
                                                                         @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAppellantNameFuzzy(appellantName, page, size));
    }

    @GetMapping("/search/appellant/id-card")
    @Operation(summary = "Search By Appellant Id Card")
    public ResponseEntity<List<AppealRecord>> searchByAppellantIdCard(@RequestParam String appellantIdCard,
                                                                      @RequestParam(defaultValue = "1") int page,
                                                                      @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAppellantIdCard(appellantIdCard, page, size));
    }

    @GetMapping("/search/acceptance-status")
    @Operation(summary = "Search By Acceptance Status")
    public ResponseEntity<List<AppealRecord>> searchByAcceptanceStatus(@RequestParam String acceptanceStatus,
                                                                       @RequestParam(defaultValue = "1") int page,
                                                                       @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAcceptanceStatus(acceptanceStatus, page, size));
    }

    @GetMapping("/search/process-status")
    @Operation(summary = "Search By Process Status")
    public ResponseEntity<List<AppealRecord>> searchByProcessStatus(@RequestParam String processStatus,
                                                                    @RequestParam(defaultValue = "1") int page,
                                                                    @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByProcessStatus(processStatus, page, size));
    }

    @GetMapping("/search/time-range")
    @Operation(summary = "Search By Time Range")
    public ResponseEntity<List<AppealRecord>> searchByTimeRange(@RequestParam String startTime,
                                                                @RequestParam String endTime,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAppealTimeRange(startTime, endTime, page, size));
    }

    @GetMapping("/search/handler")
    @Operation(summary = "Search By Handler")
    public ResponseEntity<List<AppealRecord>> searchByHandler(@RequestParam String acceptanceHandler,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealRecordService.searchByAcceptanceHandler(acceptanceHandler, page, size));
    }

    @PostMapping("/{appealId}/reviews")
    @Operation(summary = "Create Review")
    public ResponseEntity<AppealReview> createReview(@PathVariable Long appealId,
                                                     @Valid @RequestBody CreateAppealReviewRequest request,
                                                     @RequestHeader(value = "Idempotency-Key", required = false)
                                                     String idempotencyKey) {
        AppealReview review = request.toAppealReview();
        boolean useIdempotency = hasKey(idempotencyKey);
        try {
            review.setAppealId(appealId);
            if (useIdempotency) {
                if (appealReviewService.shouldSkipProcessing(idempotencyKey)) {
                    LOG.log(Level.INFO, "Appeal review skipped by idempotency key {0}", idempotencyKey);
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                appealReviewService.checkAndInsertIdempotency(idempotencyKey, review, "create");
            }
            AppealReview saved = appealReviewService.createReview(review);
            if (useIdempotency && saved.getReviewId() != null) {
                appealReviewService.markHistorySuccess(idempotencyKey, saved.getReviewId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useIdempotency) {
                appealReviewService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Create appeal review failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/reviews/{reviewId}")
    @Operation(summary = "Update Review")
    public ResponseEntity<AppealReview> updateReview(@PathVariable Long reviewId,
                                                     @RequestBody AppealReview review,
                                                     @RequestHeader(value = "Idempotency-Key", required = false)
                                                     String idempotencyKey) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @DeleteMapping("/reviews/{reviewId}")
    @Operation(summary = "Delete Review")
    public ResponseEntity<Void> deleteReview(@PathVariable Long reviewId) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).build();
    }

    @GetMapping("/reviews/{reviewId}")
    @Operation(summary = "Get Review")
    public ResponseEntity<AppealReview> getReview(@PathVariable Long reviewId) {
        try {
            AppealReview review = appealReviewService.findById(reviewId);
            return review == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(review);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get appeal review failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/reviews")
    @Operation(summary = "List Reviews")
    public ResponseEntity<List<AppealReview>> listReviews(@RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(appealReviewService.findAll(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List appeal reviews failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/{appealId}/reviews")
    @Operation(summary = "List Reviews By Appeal")
    public ResponseEntity<List<AppealReview>> listReviewsByAppeal(@PathVariable Long appealId,
                                                                  @RequestParam(defaultValue = "1") int page,
                                                                  @RequestParam(defaultValue = "20") int size) {
        try {
            return ResponseEntity.ok(appealReviewService.findByAppealId(appealId, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List appeal reviews by appeal failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/reviews/search/reviewer")
    @Operation(summary = "Search Reviews By Reviewer")
    public ResponseEntity<List<AppealReview>> searchReviewsByReviewer(@RequestParam String reviewer,
                                                                      @RequestParam(defaultValue = "1") int page,
                                                                      @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealReviewService.searchByReviewer(reviewer, page, size));
    }

    @GetMapping("/reviews/search/reviewer-dept")
    @Operation(summary = "Search Reviews By Reviewer Dept")
    public ResponseEntity<List<AppealReview>> searchReviewsByReviewerDept(@RequestParam String reviewerDept,
                                                                          @RequestParam(defaultValue = "1") int page,
                                                                          @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealReviewService.searchByReviewerDept(reviewerDept, page, size));
    }

    @GetMapping("/reviews/search/time-range")
    @Operation(summary = "Search Reviews By Time Range")
    public ResponseEntity<List<AppealReview>> searchReviewsByTimeRange(@RequestParam String startTime,
                                                                       @RequestParam String endTime,
                                                                       @RequestParam(defaultValue = "1") int page,
                                                                       @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(appealReviewService.searchByReviewTimeRange(startTime, endTime, page, size));
    }

    @GetMapping("/reviews/count")
    @Operation(summary = "Count Reviews")
    public ResponseEntity<Map<String, Object>> countReviews(@RequestParam("level") String reviewLevel) {
        try {
            long total = appealReviewService.countByReviewLevel(reviewLevel);
            return ResponseEntity.ok(Map.of("reviewLevel", reviewLevel, "count", total));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Count appeal reviews failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    private ResponseEntity<AppealRecord> executeIdempotentAppealAction(String idempotencyKey,
                                                                       AppealRecord draft,
                                                                       String action,
                                                                       HttpStatus successStatus,
                                                                       Supplier<AppealRecord> operation) {
        boolean useIdempotency = hasKey(idempotencyKey);
        if (useIdempotency) {
            if (appealRecordService.shouldSkipProcessing(idempotencyKey)) {
                return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
            }
            appealRecordService.checkAndInsertIdempotency(idempotencyKey, draft, action);
        }
        try {
            AppealRecord saved = operation.get();
            if (useIdempotency && saved != null && saved.getAppealId() != null) {
                appealRecordService.markHistorySuccess(idempotencyKey, saved.getAppealId());
            }
            return ResponseEntity.status(successStatus).body(saved);
        } catch (RuntimeException ex) {
            if (useIdempotency) {
                appealRecordService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            throw ex;
        }
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private <T> ResponseEntity<T> handleCurrentUserAppealState(IllegalStateException ex) {
        String message = ex == null || ex.getMessage() == null
                ? ""
                : ex.getMessage().trim().toLowerCase(Locale.ROOT);
        if (message.contains("appeal not found") || message.contains("offense not found")) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        if (message.contains("current user is not authenticated") || message.contains("current user not found")) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        if (message.contains("does not belong to current user") || message.contains("outside the current user scope")) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }
        if (message.contains("complete your personal profile")
                || message.contains("waiting for supplemental materials")
                || message.contains("must be resubmitted")
                || message.contains("not waiting for current user action")
                || message.contains("state does not allow this event")) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
        throw ex;
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }

    public static class CurrentUserAppealCreateRequest {
        @NotNull(message = "Offense ID is required")
        @Positive(message = "Offense ID must be greater than zero")
        private Long offenseId;

        @NotBlank(message = "Appeal reason must not be blank")
        @Size(max = 255, message = "Appeal reason must be at most 255 characters")
        private String appealReason;

        @Size(max = 64, message = "Appeal type must be at most 64 characters")
        private String appealType;

        @Size(max = 65535, message = "Evidence description is too long")
        private String evidenceDescription;

        @Size(max = 65535, message = "Evidence URLs payload is too long")
        private String evidenceUrls;

        public Long getOffenseId() {
            return offenseId;
        }

        public void setOffenseId(Long offenseId) {
            this.offenseId = offenseId;
        }

        public String getAppealReason() {
            return appealReason;
        }

        public void setAppealReason(String appealReason) {
            this.appealReason = appealReason;
        }

        public String getAppealType() {
            return appealType;
        }

        public void setAppealType(String appealType) {
            this.appealType = appealType;
        }

        public String getEvidenceDescription() {
            return evidenceDescription;
        }

        public void setEvidenceDescription(String evidenceDescription) {
            this.evidenceDescription = evidenceDescription;
        }

        public String getEvidenceUrls() {
            return evidenceUrls;
        }

        public void setEvidenceUrls(String evidenceUrls) {
            this.evidenceUrls = evidenceUrls;
        }

        public AppealRecord toAppealRecord() {
            AppealRecord appealRecord = new AppealRecord();
            appealRecord.setOffenseId(offenseId);
            appealRecord.setAppealReason(appealReason);
            appealRecord.setAppealType(appealType);
            appealRecord.setEvidenceDescription(evidenceDescription);
            appealRecord.setEvidenceUrls(evidenceUrls);
            return appealRecord;
        }
    }

    public static class CreateAppealReviewRequest {
        @NotBlank(message = "Review level must not be blank")
        @Size(max = 32, message = "Review level must be at most 32 characters")
        private String reviewLevel;

        @NotBlank(message = "Review result must not be blank")
        @Size(max = 32, message = "Review result must be at most 32 characters")
        private String reviewResult;

        @Size(max = 65535, message = "Review opinion is too long")
        private String reviewOpinion;

        @Size(max = 64, message = "Suggested action must be at most 64 characters")
        private String suggestedAction;

        @PositiveOrZero(message = "Suggested fine amount must not be negative")
        private java.math.BigDecimal suggestedFineAmount;

        @PositiveOrZero(message = "Suggested points must not be negative")
        private Integer suggestedPoints;

        @Size(max = 255, message = "Remarks must be at most 255 characters")
        private String remarks;

        public String getReviewLevel() {
            return reviewLevel;
        }

        public void setReviewLevel(String reviewLevel) {
            this.reviewLevel = reviewLevel;
        }

        public String getReviewResult() {
            return reviewResult;
        }

        public void setReviewResult(String reviewResult) {
            this.reviewResult = reviewResult;
        }

        public String getReviewOpinion() {
            return reviewOpinion;
        }

        public void setReviewOpinion(String reviewOpinion) {
            this.reviewOpinion = reviewOpinion;
        }

        public String getSuggestedAction() {
            return suggestedAction;
        }

        public void setSuggestedAction(String suggestedAction) {
            this.suggestedAction = suggestedAction;
        }

        public java.math.BigDecimal getSuggestedFineAmount() {
            return suggestedFineAmount;
        }

        public void setSuggestedFineAmount(java.math.BigDecimal suggestedFineAmount) {
            this.suggestedFineAmount = suggestedFineAmount;
        }

        public Integer getSuggestedPoints() {
            return suggestedPoints;
        }

        public void setSuggestedPoints(Integer suggestedPoints) {
            this.suggestedPoints = suggestedPoints;
        }

        public String getRemarks() {
            return remarks;
        }

        public void setRemarks(String remarks) {
            this.remarks = remarks;
        }

        public AppealReview toAppealReview() {
            AppealReview review = new AppealReview();
            review.setReviewLevel(reviewLevel);
            review.setReviewResult(reviewResult);
            review.setReviewOpinion(reviewOpinion);
            review.setSuggestedAction(suggestedAction);
            review.setSuggestedFineAmount(suggestedFineAmount);
            review.setSuggestedPoints(suggestedPoints);
            review.setRemarks(remarks);
            return review;
        }
    }

    public static class CreateAppealRequest {
        @NotNull(message = "Offense ID is required")
        @Positive(message = "Offense ID must be greater than zero")
        private Long offenseId;

        @Size(max = 128, message = "Appellant name must be at most 128 characters")
        private String appellantName;

        @Size(max = 32, message = "Appellant ID card must be at most 32 characters")
        private String appellantIdCard;

        @Size(max = 64, message = "Appellant contact must be at most 64 characters")
        private String appellantContact;

        @Size(max = 128, message = "Appellant email must be at most 128 characters")
        private String appellantEmail;

        @Size(max = 255, message = "Appellant address must be at most 255 characters")
        private String appellantAddress;

        @Size(max = 64, message = "Appeal type must be at most 64 characters")
        private String appealType;

        @NotBlank(message = "Appeal reason must not be blank")
        @Size(max = 255, message = "Appeal reason must be at most 255 characters")
        private String appealReason;

        @Size(max = 65535, message = "Evidence description is too long")
        private String evidenceDescription;

        @Size(max = 65535, message = "Evidence URLs payload is too long")
        private String evidenceUrls;

        @Size(max = 255, message = "Remarks must be at most 255 characters")
        private String remarks;

        public Long getOffenseId() {
            return offenseId;
        }

        public void setOffenseId(Long offenseId) {
            this.offenseId = offenseId;
        }

        public String getAppellantName() {
            return appellantName;
        }

        public void setAppellantName(String appellantName) {
            this.appellantName = appellantName;
        }

        public String getAppellantIdCard() {
            return appellantIdCard;
        }

        public void setAppellantIdCard(String appellantIdCard) {
            this.appellantIdCard = appellantIdCard;
        }

        public String getAppellantContact() {
            return appellantContact;
        }

        public void setAppellantContact(String appellantContact) {
            this.appellantContact = appellantContact;
        }

        public String getAppellantEmail() {
            return appellantEmail;
        }

        public void setAppellantEmail(String appellantEmail) {
            this.appellantEmail = appellantEmail;
        }

        public String getAppellantAddress() {
            return appellantAddress;
        }

        public void setAppellantAddress(String appellantAddress) {
            this.appellantAddress = appellantAddress;
        }

        public String getAppealType() {
            return appealType;
        }

        public void setAppealType(String appealType) {
            this.appealType = appealType;
        }

        public String getAppealReason() {
            return appealReason;
        }

        public void setAppealReason(String appealReason) {
            this.appealReason = appealReason;
        }

        public String getEvidenceDescription() {
            return evidenceDescription;
        }

        public void setEvidenceDescription(String evidenceDescription) {
            this.evidenceDescription = evidenceDescription;
        }

        public String getEvidenceUrls() {
            return evidenceUrls;
        }

        public void setEvidenceUrls(String evidenceUrls) {
            this.evidenceUrls = evidenceUrls;
        }

        public String getRemarks() {
            return remarks;
        }

        public void setRemarks(String remarks) {
            this.remarks = remarks;
        }

        public AppealRecord toAppealRecord() {
            AppealRecord appealRecord = new AppealRecord();
            appealRecord.setOffenseId(offenseId);
            appealRecord.setAppellantName(appellantName);
            appealRecord.setAppellantIdCard(appellantIdCard);
            appealRecord.setAppellantContact(appellantContact);
            appealRecord.setAppellantEmail(appellantEmail);
            appealRecord.setAppellantAddress(appellantAddress);
            appealRecord.setAppealType(appealType);
            appealRecord.setAppealReason(appealReason);
            appealRecord.setEvidenceDescription(evidenceDescription);
            appealRecord.setEvidenceUrls(evidenceUrls);
            appealRecord.setRemarks(remarks);
            return appealRecord;
        }
    }

    public static class CurrentUserAppealSubmissionRequest {
        @Size(max = 255, message = "Appeal reason must be at most 255 characters")
        private String appealReason;

        @Size(max = 65535, message = "Evidence description is too long")
        private String evidenceDescription;

        @Size(max = 65535, message = "Evidence URLs payload is too long")
        private String evidenceUrls;

        public String getAppealReason() {
            return appealReason;
        }

        public void setAppealReason(String appealReason) {
            this.appealReason = appealReason;
        }

        public String getEvidenceDescription() {
            return evidenceDescription;
        }

        public void setEvidenceDescription(String evidenceDescription) {
            this.evidenceDescription = evidenceDescription;
        }

        public String getEvidenceUrls() {
            return evidenceUrls;
        }

        public void setEvidenceUrls(String evidenceUrls) {
            this.evidenceUrls = evidenceUrls;
        }

        public AppealRecord toAppealRecord() {
            AppealRecord appealRecord = new AppealRecord();
            appealRecord.setAppealReason(appealReason);
            appealRecord.setEvidenceDescription(evidenceDescription);
            appealRecord.setEvidenceUrls(evidenceUrls);
            return appealRecord;
        }
    }
}
