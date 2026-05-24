package com.tutict.finalassignmentbackend.controller;

import com.tutict.finalassignmentbackend.entity.SysDict;
import com.tutict.finalassignmentbackend.entity.SysSettings;
import com.tutict.finalassignmentbackend.service.SysDictService;
import com.tutict.finalassignmentbackend.service.SysSettingsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.security.RolesAllowed;
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
import java.util.logging.Level;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/system/settings")
@Tag(name = "System Settings", description = "System Settings endpoints")
@SecurityRequirement(name = "bearerAuth")
@RolesAllowed({"SUPER_ADMIN", "ADMIN"})
public class SystemSettingsController {

    private static final Logger LOG = Logger.getLogger(SystemSettingsController.class.getName());

    private final SysSettingsService sysSettingsService;
    private final SysDictService sysDictService;

    public SystemSettingsController(SysSettingsService sysSettingsService,
                                    SysDictService sysDictService) {
        this.sysSettingsService = sysSettingsService;
        this.sysDictService = sysDictService;
    }

    @PostMapping
    @Operation(summary = "Create Setting")
    public ResponseEntity<SysSettings> createSetting(@RequestBody SysSettings request,
                                                     @RequestHeader(value = "Idempotency-Key", required = false)
                                                     String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            if (useKey) {
                if (sysSettingsService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysSettingsService.checkAndInsertIdempotency(idempotencyKey, request, "create");
            }
            SysSettings saved = sysSettingsService.createSysSettings(request);
            if (useKey && saved.getSettingId() != null) {
                sysSettingsService.markHistorySuccess(idempotencyKey, saved.getSettingId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                sysSettingsService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Create setting failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/{settingId}")
    @Operation(summary = "Update Setting")
    public ResponseEntity<SysSettings> updateSetting(@PathVariable Integer settingId,
                                                     @RequestBody SysSettings request,
                                                     @RequestHeader(value = "Idempotency-Key", required = false)
                                                     String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            request.setSettingId(settingId);
            if (useKey) {
                if (sysSettingsService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysSettingsService.checkAndInsertIdempotency(idempotencyKey, request, "update");
            }
            SysSettings updated = sysSettingsService.updateSysSettings(request);
            if (useKey && updated.getSettingId() != null) {
                sysSettingsService.markHistorySuccess(idempotencyKey, updated.getSettingId());
            }
            return ResponseEntity.ok(updated);
        } catch (Exception ex) {
            if (useKey) {
                sysSettingsService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Update setting failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @DeleteMapping("/{settingId}")
    @Operation(summary = "Delete Setting")
    public ResponseEntity<Void> deleteSetting(@PathVariable Integer settingId) {
        try {
            sysSettingsService.deleteSysSettings(settingId);
            return ResponseEntity.noContent().build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Delete setting failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/{settingId}")
    @Operation(summary = "Get Setting")
    public ResponseEntity<SysSettings> getSetting(@PathVariable Integer settingId) {
        try {
            SysSettings settings = sysSettingsService.findById(settingId);
            return settings == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(settings);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get setting failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping
    @Operation(summary = "List Settings")
    public ResponseEntity<List<SysSettings>> listSettings(@RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "50") int size) {
        try {
            return ResponseEntity.ok(sysSettingsService.findAll(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List settings failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/key/{settingKey}")
    @Operation(summary = "Get By Key")
    public ResponseEntity<SysSettings> getByKey(@PathVariable String settingKey) {
        try {
            SysSettings settings = sysSettingsService.findByKey(settingKey);
            return settings == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(settings);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get setting by key failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/category/{category}")
    @Operation(summary = "Get By Category")
    public ResponseEntity<List<SysSettings>> getByCategory(@PathVariable String category,
                                                           @RequestParam(defaultValue = "1") int page,
                                                           @RequestParam(defaultValue = "50") int size) {
        try {
            return ResponseEntity.ok(sysSettingsService.findByCategory(category, page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List settings by category failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/search/key/prefix")
    @Operation(summary = "Search By Key Prefix")
    public ResponseEntity<List<SysSettings>> searchByKeyPrefix(@RequestParam String settingKey,
                                                               @RequestParam(defaultValue = "1") int page,
                                                               @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysSettingsService.searchBySettingKeyPrefix(settingKey, page, size));
    }

    @GetMapping("/search/key/fuzzy")
    @Operation(summary = "Search By Key Fuzzy")
    public ResponseEntity<List<SysSettings>> searchByKeyFuzzy(@RequestParam String settingKey,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysSettingsService.searchBySettingKeyFuzzy(settingKey, page, size));
    }

    @GetMapping("/search/type")
    @Operation(summary = "Search By Type")
    public ResponseEntity<List<SysSettings>> searchByType(@RequestParam String settingType,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysSettingsService.searchBySettingType(settingType, page, size));
    }

    @GetMapping("/search/editable")
    @Operation(summary = "Search By Editable")
    public ResponseEntity<List<SysSettings>> searchByEditable(@RequestParam boolean isEditable,
                                                              @RequestParam(defaultValue = "1") int page,
                                                              @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysSettingsService.searchByIsEditable(isEditable, page, size));
    }

    @GetMapping("/search/encrypted")
    @Operation(summary = "Search By Encrypted")
    public ResponseEntity<List<SysSettings>> searchByEncrypted(@RequestParam boolean isEncrypted,
                                                               @RequestParam(defaultValue = "1") int page,
                                                               @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysSettingsService.searchByIsEncrypted(isEncrypted, page, size));
    }

    @PostMapping("/dicts")
    @Operation(summary = "Create Dict")
    public ResponseEntity<SysDict> createDict(@RequestBody SysDict request,
                                              @RequestHeader(value = "Idempotency-Key", required = false)
                                              String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            if (useKey) {
                if (sysDictService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysDictService.checkAndInsertIdempotency(idempotencyKey, request, "create");
            }
            SysDict saved = sysDictService.createSysDict(request);
            if (useKey && saved.getDictId() != null) {
                sysDictService.markHistorySuccess(idempotencyKey, saved.getDictId());
            }
            return ResponseEntity.status(HttpStatus.CREATED).body(saved);
        } catch (Exception ex) {
            if (useKey) {
                sysDictService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Create dict failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @PutMapping("/dicts/{dictId}")
    @Operation(summary = "Update Dict")
    public ResponseEntity<SysDict> updateDict(@PathVariable Integer dictId,
                                              @RequestBody SysDict request,
                                              @RequestHeader(value = "Idempotency-Key", required = false)
                                              String idempotencyKey) {
        boolean useKey = hasKey(idempotencyKey);
        try {
            request.setDictId(dictId);
            if (useKey) {
                if (sysDictService.shouldSkipProcessing(idempotencyKey)) {
                    return ResponseEntity.status(HttpStatus.ALREADY_REPORTED).build();
                }
                sysDictService.checkAndInsertIdempotency(idempotencyKey, request, "update");
            }
            SysDict updated = sysDictService.updateSysDict(request);
            if (useKey && updated.getDictId() != null) {
                sysDictService.markHistorySuccess(idempotencyKey, updated.getDictId());
            }
            return ResponseEntity.ok(updated);
        } catch (Exception ex) {
            if (useKey) {
                sysDictService.markHistoryFailure(idempotencyKey, ex.getMessage());
            }
            LOG.log(Level.SEVERE, "Update dict failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @DeleteMapping("/dicts/{dictId}")
    @Operation(summary = "Delete Dict")
    public ResponseEntity<Void> deleteDict(@PathVariable Integer dictId) {
        try {
            sysDictService.deleteSysDict(dictId);
            return ResponseEntity.noContent().build();
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Delete dict failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/dicts/{dictId}")
    @Operation(summary = "Get Dict")
    public ResponseEntity<SysDict> getDict(@PathVariable Integer dictId) {
        try {
            SysDict dict = sysDictService.findById(dictId);
            return dict == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(dict);
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "Get dict failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    @GetMapping("/dicts/search/type")
    @Operation(summary = "Search Dict By Type")
    public ResponseEntity<List<SysDict>> searchDictByType(@RequestParam String dictType,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysDictService.searchByDictType(dictType, page, size));
    }

    @GetMapping("/dicts/search/code")
    @Operation(summary = "Search Dict By Code")
    public ResponseEntity<List<SysDict>> searchDictByCode(@RequestParam String dictCode,
                                                          @RequestParam(defaultValue = "1") int page,
                                                          @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysDictService.searchByDictCodePrefix(dictCode, page, size));
    }

    @GetMapping("/dicts/search/label/prefix")
    @Operation(summary = "Search Dict By Label Prefix")
    public ResponseEntity<List<SysDict>> searchDictByLabelPrefix(@RequestParam String dictLabel,
                                                                 @RequestParam(defaultValue = "1") int page,
                                                                 @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysDictService.searchByDictLabelPrefix(dictLabel, page, size));
    }

    @GetMapping("/dicts/search/label/fuzzy")
    @Operation(summary = "Search Dict By Label Fuzzy")
    public ResponseEntity<List<SysDict>> searchDictByLabelFuzzy(@RequestParam String dictLabel,
                                                                @RequestParam(defaultValue = "1") int page,
                                                                @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysDictService.searchByDictLabelFuzzy(dictLabel, page, size));
    }

    @GetMapping("/dicts/search/parent")
    @Operation(summary = "Search Dict By Parent")
    public ResponseEntity<List<SysDict>> searchDictByParent(@RequestParam Integer parentId,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysDictService.findByParentId(parentId, page, size));
    }

    @GetMapping("/dicts/search/default")
    @Operation(summary = "Search Dict By Default")
    public ResponseEntity<List<SysDict>> searchDictByDefault(@RequestParam boolean isDefault,
                                                             @RequestParam(defaultValue = "1") int page,
                                                             @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysDictService.searchByIsDefault(isDefault, page, size));
    }

    @GetMapping("/dicts/search/status")
    @Operation(summary = "Search Dict By Status")
    public ResponseEntity<List<SysDict>> searchDictByStatus(@RequestParam String status,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "50") int size) {
        return ResponseEntity.ok(sysDictService.searchByStatus(status, page, size));
    }

    @GetMapping("/dicts")
    @Operation(summary = "List Dicts")
    public ResponseEntity<List<SysDict>> listDicts(@RequestParam(defaultValue = "1") int page,
                                                   @RequestParam(defaultValue = "50") int size) {
        try {
            return ResponseEntity.ok(sysDictService.findAll(page, size));
        } catch (Exception ex) {
            LOG.log(Level.WARNING, "List dicts failed", ex);
            return ResponseEntity.status(resolveStatus(ex)).build();
        }
    }

    private boolean hasKey(String value) {
        return value != null && !value.isBlank();
    }

    private HttpStatus resolveStatus(Exception ex) {
        return (ex instanceof IllegalArgumentException || ex instanceof IllegalStateException)
                ? HttpStatus.BAD_REQUEST
                : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}
