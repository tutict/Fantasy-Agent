package com.tutict.finalassignmentbackend.service.agent;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.tutict.finalassignmentbackend.entity.AppealRecord;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.DriverVehicle;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.OffenseRecord;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.mapper.AppealRecordMapper;
import com.tutict.finalassignmentbackend.mapper.DriverInformationMapper;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.FineRecordMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.VehicleInformationMapper;
import com.tutict.finalassignmentbackend.model.ai.ChatAction;
import com.tutict.finalassignmentbackend.service.AppealRecordService;
import com.tutict.finalassignmentbackend.service.FineRecordService;
import com.tutict.finalassignmentbackend.service.OffenseRecordService;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class TrafficCaseLookupSkill implements AgentSkill {

    private static final int ACCESS_SCOPE_LOOKUP_LIMIT = 200;
    private static final int DRIVER_LOOKUP_LIMIT = 20;

    private static final List<String> MANAGER_KEYWORDS = List.of(
            "管理员", "管理端", "后台", "审核", "审计", "复核员", "处理员", "执法", "窗口"
    );

    private final OffenseRecordService offenseRecordService;
    private final FineRecordService fineRecordService;
    private final AppealRecordService appealRecordService;
    private final OffenseRecordMapper offenseRecordMapper;
    private final FineRecordMapper fineRecordMapper;
    private final AppealRecordMapper appealRecordMapper;
    private final VehicleInformationMapper vehicleInformationMapper;
    private final DriverInformationMapper driverInformationMapper;
    private final DriverVehicleMapper driverVehicleMapper;

    public TrafficCaseLookupSkill(
            OffenseRecordService offenseRecordService,
            FineRecordService fineRecordService,
            AppealRecordService appealRecordService,
            OffenseRecordMapper offenseRecordMapper,
            FineRecordMapper fineRecordMapper,
            AppealRecordMapper appealRecordMapper,
            VehicleInformationMapper vehicleInformationMapper,
            DriverInformationMapper driverInformationMapper,
            DriverVehicleMapper driverVehicleMapper
    ) {
        this.offenseRecordService = offenseRecordService;
        this.fineRecordService = fineRecordService;
        this.appealRecordService = appealRecordService;
        this.offenseRecordMapper = offenseRecordMapper;
        this.fineRecordMapper = fineRecordMapper;
        this.appealRecordMapper = appealRecordMapper;
        this.vehicleInformationMapper = vehicleInformationMapper;
        this.driverInformationMapper = driverInformationMapper;
        this.driverVehicleMapper = driverVehicleMapper;
    }

    @Override
    public String id() {
        return "traffic-case-lookup";
    }

    @Override
    public String displayName() {
        return "业务数据核验";
    }

    @Override
    public String description() {
        return "根据编号、车牌号、驾驶证号和状态核验违法、罚款、申诉数据，并按当前登录用户范围返回可访问记录。";
    }

    @Override
    public boolean supports(AgentSkillContext context) {
        return Scenario.match(context) != null && hasLookupSignal(context.message());
    }

    @Override
    public AgentSkillResult execute(AgentSkillContext context) {
        Scenario scenario = Scenario.match(context);
        if (scenario == null) {
            return AgentSkillResult.empty(id());
        }

        boolean managerIntent = context.isPrivilegedOperator() || isManagerIntent(context);
        if (!context.isAuthenticated()) {
            return buildResult(context, AccessScope.empty(), scenario, managerIntent,
                    "要核验真实业务数据，请先登录后再提供业务编号、车牌号或驾驶证号。",
                    List.of("当前未检测到登录身份，Agent 不会返回真实违法处理数据。"),
                    false);
        }

        AccessScope scope = resolveAccessScope(context);
        if (!context.isPrivilegedOperator() && !scope.isUsable()) {
            return buildResult(context, scope, scenario, managerIntent,
                    "当前账号缺少可识别的本人关联档案，暂时无法安全核验真实案件。",
                    List.of("请先补全身份证号关联信息，或直接提供本人车牌号、驾驶证号后再查询。"),
                    false);
        }

        LookupResult lookup = switch (scenario) {
            case OFFENSE -> lookupOffenses(context, scope);
            case FINE -> lookupFines(context, scope);
            case APPEAL -> lookupAppeals(context, scope);
        };
        return buildResult(context, scope, scenario, managerIntent, lookup.summary(), lookup.highlights(), lookup.recordsFound());
    }

    private AgentSkillResult buildResult(AgentSkillContext context, AccessScope scope, Scenario scenario,
                                         boolean managerIntent, String summary, List<String> detailHighlights,
                                         boolean recordsFound) {
        List<String> highlights = new ArrayList<>(detailHighlights);
        highlights.add(0, "访问范围：" + accessScopeMessage(context, scope));
        highlights.add(0, "当前身份：" + context.operatorLabel());
        if (recordsFound) {
            highlights.add("建议继续进入“" + scenario.navigateAction(managerIntent).getLabel() + "”核对完整详情。");
        } else {
            highlights.add("普通用户仅支持查询本人相关记录；可继续提供车牌号、驾驶证号或精确业务编号。");
        }
        return new AgentSkillResult(id(), summary, highlights, List.of(),
                List.of(scenario.navigateAction(managerIntent)), false);
    }

    private boolean isManagerIntent(AgentSkillContext context) {
        return MANAGER_KEYWORDS.stream().anyMatch(context::containsAny);
    }

    private LookupResult lookupOffenses(AgentSkillContext context, AccessScope scope) {
        String message = raw(context.message());
        Long offenseId = extractLongAfterKeywords(message, "违法id", "违法记录id", "offense id", "offenseid", "案件id");
        if (offenseId != null) {
            OffenseRecord record = offenseRecordService.findById(offenseId);
            return record == null || !canAccessOffense(context, scope, record)
                    ? notFound("未查询到当前账号可访问的违法记录。")
                    : found("已查询到 1 条违法记录。", List.of(formatOffense(record)));
        }

        String offenseNumber = extractCodeAfterKeywords(message, "违法编号", "违法单号", "offense number", "案件编号");
        if (offenseNumber != null) {
            List<OffenseRecord> records = filterOffenses(context, scope, exactOffensesByNumber(offenseNumber));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该违法编号记录。")
                    : found("已按违法编号命中 " + records.size() + " 条记录。", records.stream().map(this::formatOffense).toList());
        }

        String plate = extractLicensePlate(message);
        if (plate != null) {
            LookupSeed seed = offenseSeedByPlate(context, scope, plate);
            return seed.records().isEmpty()
                    ? notFound("未查询到当前账号可访问的该车牌违法记录。")
                    : found("已按车牌号命中 " + seed.records().size() + " 条违法记录。", seed.records().stream().map(this::formatOffense).toList());
        }

        String driverLicenseNumber = extractDriverLicenseNumber(message);
        if (driverLicenseNumber != null) {
            LookupSeed seed = offenseSeedByDriverLicense(context, scope, driverLicenseNumber);
            return seed.records().isEmpty()
                    ? notFound("未查询到当前账号可访问的该驾驶证关联违法记录。")
                    : found("已按驾驶证号命中 " + seed.records().size() + " 条违法记录。", seed.records().stream().map(this::formatOffense).toList());
        }

        List<String> statuses = offenseStatuses(context.normalizedMessage());
        if (!statuses.isEmpty() && context.isPrivilegedOperator()) {
            for (String status : statuses) {
                List<OffenseRecord> records = offenseRecordService.searchByProcessStatus(status, 1, 3);
                if (!records.isEmpty()) {
                    return found("已按违法处理状态命中 " + records.size() + " 条记录。", records.stream().map(this::formatOffense).toList());
                }
            }
        }
        return limitedScopeHint(context, scope);
    }

    private LookupResult lookupFines(AgentSkillContext context, AccessScope scope) {
        String message = raw(context.message());
        Long fineId = extractLongAfterKeywords(message, "罚款id", "罚单id", "fine id", "fineid");
        if (fineId != null) {
            FineRecord record = fineRecordService.findById(fineId);
            return record == null || !canAccessFine(context, scope, record)
                    ? notFound("未查询到当前账号可访问的罚款记录。")
                    : found("已查询到 1 条罚款记录。", List.of(formatFine(record)));
        }

        String fineNumber = extractCodeAfterKeywords(message, "罚款编号", "罚单编号", "决定书编号", "fine number");
        if (fineNumber != null) {
            List<FineRecord> records = filterFines(context, scope, exactFinesByNumber(fineNumber));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该罚款编号记录。")
                    : found("已按罚款编号命中 " + records.size() + " 条记录。", records.stream().map(this::formatFine).toList());
        }

        Long offenseId = extractLongAfterKeywords(message, "违法id", "违法记录id", "offense id", "offenseid");
        if (offenseId != null) {
            List<FineRecord> records = filterFines(context, scope, fineRecordService.findByOffenseId(offenseId, 1, 3));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该违法关联罚款记录。")
                    : found("已按违法记录命中 " + records.size() + " 条罚款记录。", records.stream().map(this::formatFine).toList());
        }

        String plate = extractLicensePlate(message);
        if (plate != null) {
            LookupSeed seed = offenseSeedByPlate(context, scope, plate);
            List<FineRecord> records = filterFines(context, scope, finesByOffenseIds(seed.offenseIds()));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该车牌罚款记录。")
                    : found("已按车牌号命中 " + records.size() + " 条罚款记录。", records.stream().map(this::formatFine).toList());
        }

        String driverLicenseNumber = extractDriverLicenseNumber(message);
        if (driverLicenseNumber != null) {
            LookupSeed seed = offenseSeedByDriverLicense(context, scope, driverLicenseNumber);
            List<FineRecord> records = filterFines(context, scope, finesByOffenseIds(seed.offenseIds()));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该驾驶证罚款记录。")
                    : found("已按驾驶证号命中 " + records.size() + " 条罚款记录。", records.stream().map(this::formatFine).toList());
        }

        List<String> statuses = fineStatuses(context.normalizedMessage());
        if (!statuses.isEmpty() && context.isPrivilegedOperator()) {
            for (String status : statuses) {
                List<FineRecord> records = fineRecordService.searchByPaymentStatus(status, 1, 3);
                if (!records.isEmpty()) {
                    return found("已按缴费状态命中 " + records.size() + " 条罚款记录。", records.stream().map(this::formatFine).toList());
                }
            }
        }
        return limitedScopeHint(context, scope);
    }

    private LookupResult lookupAppeals(AgentSkillContext context, AccessScope scope) {
        String message = raw(context.message());
        Long appealId = extractLongAfterKeywords(message, "申诉id", "申诉记录id", "appeal id", "appealid");
        if (appealId != null) {
            AppealRecord record = appealRecordService.getAppealById(appealId);
            return record == null || !canAccessAppeal(context, scope, record)
                    ? notFound("未查询到当前账号可访问的申诉记录。")
                    : found("已查询到 1 条申诉记录。", List.of(formatAppeal(record)));
        }

        String appealNumber = extractCodeAfterKeywords(message, "申诉编号", "appeal number", "复核编号");
        if (appealNumber != null) {
            List<AppealRecord> records = filterAppeals(context, scope, exactAppealsByNumber(appealNumber));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该申诉编号记录。")
                    : found("已按申诉编号命中 " + records.size() + " 条记录。", records.stream().map(this::formatAppeal).toList());
        }

        Long offenseId = extractLongAfterKeywords(message, "违法id", "违法记录id", "offense id", "offenseid");
        if (offenseId != null) {
            List<AppealRecord> records = filterAppeals(context, scope, appealRecordService.findByOffenseId(offenseId, 1, 3));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该违法关联申诉记录。")
                    : found("已按违法记录命中 " + records.size() + " 条申诉记录。", records.stream().map(this::formatAppeal).toList());
        }

        String plate = extractLicensePlate(message);
        if (plate != null) {
            LookupSeed seed = offenseSeedByPlate(context, scope, plate);
            List<AppealRecord> records = filterAppeals(context, scope, appealsByOffenseIds(seed.offenseIds()));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该车牌申诉记录。")
                    : found("已按车牌号命中 " + records.size() + " 条申诉记录。", records.stream().map(this::formatAppeal).toList());
        }

        String driverLicenseNumber = extractDriverLicenseNumber(message);
        if (driverLicenseNumber != null) {
            LookupSeed seed = offenseSeedByDriverLicense(context, scope, driverLicenseNumber);
            List<AppealRecord> records = filterAppeals(context, scope, appealsByOffenseIds(seed.offenseIds()));
            return records.isEmpty()
                    ? notFound("未查询到当前账号可访问的该驾驶证申诉记录。")
                    : found("已按驾驶证号命中 " + records.size() + " 条申诉记录。", records.stream().map(this::formatAppeal).toList());
        }

        List<String> acceptStatuses = context.containsAny("受理", "acceptance")
                ? appealAcceptanceStatuses(context.normalizedMessage()) : List.of();
        if (!acceptStatuses.isEmpty() && context.isPrivilegedOperator()) {
            for (String status : acceptStatuses) {
                List<AppealRecord> records = appealRecordService.searchByAcceptanceStatus(status, 1, 3);
                if (!records.isEmpty()) {
                    return found("已按申诉受理状态命中 " + records.size() + " 条记录。", records.stream().map(this::formatAppeal).toList());
                }
            }
        }

        List<String> processStatuses = appealProcessStatuses(context.normalizedMessage());
        if (!processStatuses.isEmpty() && context.isPrivilegedOperator()) {
            for (String status : processStatuses) {
                List<AppealRecord> records = appealRecordService.searchByProcessStatus(status, 1, 3);
                if (!records.isEmpty()) {
                    return found("已按申诉处理状态命中 " + records.size() + " 条记录。", records.stream().map(this::formatAppeal).toList());
                }
            }
        }
        return limitedScopeHint(context, scope);
    }

    private LookupResult limitedScopeHint() {
        return notFound("请提供精确的违法编号、罚单编号、申诉编号、本人车牌号或驾驶证号后再查询。");
    }

    private LookupResult limitedScopeHint(AgentSkillContext context, AccessScope scope) {
        if (context.isPrivilegedOperator() || scope.privileged()) {
            return notFound("未查询到符合当前条件的案件记录，可继续补充更精确的业务编号或状态。");
        }
        return notFound("当前身份下不能直接按全局状态枚举案件，请提供精确违法编号、罚单编号、申诉编号、本人车牌号或驾驶证号后再查询。");
    }

    private AccessScope resolveAccessScope(AgentSkillContext context) {
        if (context.isPrivilegedOperator()) {
            return AccessScope.privileged(context.idCardNumber());
        }
        if (blank(context.idCardNumber())) {
            return AccessScope.empty();
        }
        Set<Long> vehicleIds = new LinkedHashSet<>();
        Set<Long> driverIds = new LinkedHashSet<>();

        vehicleInformationMapper.selectList(new QueryWrapper<VehicleInformation>()
                        .select("vehicle_id")
                        .eq("owner_id_card", context.idCardNumber())
                        .orderByDesc("updated_at")
                        .orderByDesc("vehicle_id")
                        .last("limit " + ACCESS_SCOPE_LOOKUP_LIMIT))
                .stream().map(VehicleInformation::getVehicleId).filter(Objects::nonNull).forEach(vehicleIds::add);

        driverInformationMapper.selectList(new QueryWrapper<DriverInformation>()
                        .select("driver_id")
                        .eq("id_card_number", context.idCardNumber())
                        .orderByDesc("driver_id")
                        .last("limit " + ACCESS_SCOPE_LOOKUP_LIMIT))
                .stream().map(DriverInformation::getDriverId).filter(Objects::nonNull).forEach(driverIds::add);

        if (!driverIds.isEmpty()) {
            driverVehicleMapper.selectList(new QueryWrapper<DriverVehicle>()
                            .select("vehicle_id", "status")
                            .in("driver_id", driverIds)
                            .orderByDesc("id")
                            .last("limit " + ACCESS_SCOPE_LOOKUP_LIMIT))
                    .stream().filter(binding -> !equalsIgnoreCase(binding.getStatus(), "Inactive"))
                    .map(DriverVehicle::getVehicleId).filter(Objects::nonNull).forEach(vehicleIds::add);
        }
        return new AccessScope(false, context.idCardNumber(), driverIds, vehicleIds);
    }

    private LookupSeed offenseSeedByPlate(AgentSkillContext context, AccessScope scope, String plate) {
        VehicleInformation vehicle = vehicleInformationMapper.selectOne(new QueryWrapper<VehicleInformation>().eq("license_plate", plate));
        if (vehicle == null || !canAccessVehicle(context, scope, vehicle.getVehicleId())) {
            return LookupSeed.empty();
        }
        return LookupSeed.of(filterOffenses(context, scope, offenseRecordService.findByVehicleId(vehicle.getVehicleId(), 1, 3)));
    }

    private LookupSeed offenseSeedByDriverLicense(AgentSkillContext context, AccessScope scope, String driverLicenseNumber) {
        List<Long> driverIds = driverInformationMapper.selectList(
                        new QueryWrapper<DriverInformation>()
                                .select("driver_id")
                                .eq("driver_license_number", driverLicenseNumber)
                                .orderByDesc("driver_id")
                                .last("limit " + DRIVER_LOOKUP_LIMIT))
                .stream()
                .map(DriverInformation::getDriverId)
                .filter(Objects::nonNull)
                .filter(driverId -> canAccessDriver(context, scope, driverId))
                .toList();
        List<OffenseRecord> records = offenseRecordService.findByDriverIds(driverIds, 1, 3);
        return LookupSeed.of(filterOffenses(context, scope, records));
    }

    private List<OffenseRecord> exactOffensesByNumber(String offenseNumber) {
        return offenseRecordMapper.selectList(new QueryWrapper<OffenseRecord>()
                .eq("offense_number", offenseNumber).orderByDesc("offense_time").last("limit 3"));
    }

    private List<FineRecord> exactFinesByNumber(String fineNumber) {
        return fineRecordMapper.selectList(new QueryWrapper<FineRecord>()
                .eq("fine_number", fineNumber).orderByDesc("fine_date").last("limit 3"));
    }

    private List<AppealRecord> exactAppealsByNumber(String appealNumber) {
        return appealRecordMapper.selectList(new QueryWrapper<AppealRecord>()
                .eq("appeal_number", appealNumber).orderByDesc("appeal_time").last("limit 3"));
    }

    private List<FineRecord> finesByOffenseIds(Set<Long> offenseIds) {
        if (offenseIds.isEmpty()) {
            return List.of();
        }
        return fineRecordMapper.selectList(new QueryWrapper<FineRecord>()
                .in("offense_id", offenseIds).orderByDesc("fine_date").last("limit 3"));
    }

    private List<AppealRecord> appealsByOffenseIds(Set<Long> offenseIds) {
        if (offenseIds.isEmpty()) {
            return List.of();
        }
        return appealRecordMapper.selectList(new QueryWrapper<AppealRecord>()
                .in("offense_id", offenseIds).orderByDesc("appeal_time").last("limit 3"));
    }

    private List<OffenseRecord> filterOffenses(AgentSkillContext context, AccessScope scope, List<OffenseRecord> records) {
        LinkedHashMap<Long, OffenseRecord> unique = new LinkedHashMap<>();
        for (OffenseRecord record : records) {
            if (record != null && record.getOffenseId() != null && canAccessOffense(context, scope, record)) {
                unique.putIfAbsent(record.getOffenseId(), record);
            }
        }
        return unique.values().stream().limit(3).toList();
    }

    private List<FineRecord> filterFines(AgentSkillContext context, AccessScope scope, List<FineRecord> records) {
        if (context.isPrivilegedOperator() || scope.privileged()) {
            return records.stream().filter(Objects::nonNull).limit(3).toList();
        }
        Map<Long, OffenseRecord> offensesById = loadOffenseAccessMap(records.stream()
                .map(FineRecord::getOffenseId)
                .toList());
        return records.stream()
                .filter(record -> canAccessFine(context, scope, record, offensesById))
                .limit(3)
                .toList();
    }

    private List<AppealRecord> filterAppeals(AgentSkillContext context, AccessScope scope, List<AppealRecord> records) {
        if (context.isPrivilegedOperator() || scope.privileged()) {
            return records.stream().filter(Objects::nonNull).limit(3).toList();
        }
        Map<Long, OffenseRecord> offensesById = loadOffenseAccessMap(records.stream()
                .map(AppealRecord::getOffenseId)
                .toList());
        return records.stream()
                .filter(record -> canAccessAppeal(context, scope, record, offensesById))
                .limit(3)
                .toList();
    }

    private boolean canAccessOffense(AgentSkillContext context, AccessScope scope, OffenseRecord record) {
        return record != null && (context.isPrivilegedOperator() || scope.privileged()
                || canAccessDriver(context, scope, record.getDriverId())
                || canAccessVehicle(context, scope, record.getVehicleId()));
    }

    private boolean canAccessFine(AgentSkillContext context, AccessScope scope, FineRecord record) {
        return canAccessFine(context, scope, record, Map.of());
    }

    private boolean canAccessFine(AgentSkillContext context, AccessScope scope,
                                  FineRecord record, Map<Long, OffenseRecord> offensesById) {
        if (record == null) {
            return false;
        }
        if (context.isPrivilegedOperator() || scope.privileged()) {
            return true;
        }
        OffenseRecord offense = resolveOffenseForAccess(record.getOffenseId(), offensesById);
        return canAccessOffense(context, scope, offense);
    }

    private boolean canAccessAppeal(AgentSkillContext context, AccessScope scope, AppealRecord record) {
        return canAccessAppeal(context, scope, record, Map.of());
    }

    private boolean canAccessAppeal(AgentSkillContext context, AccessScope scope,
                                    AppealRecord record, Map<Long, OffenseRecord> offensesById) {
        if (record == null) {
            return false;
        }
        if (context.isPrivilegedOperator() || scope.privileged()) {
            return true;
        }
        if (equalsIgnoreCase(record.getAppellantIdCard(), scope.idCardNumber())) {
            return true;
        }
        OffenseRecord offense = resolveOffenseForAccess(record.getOffenseId(), offensesById);
        return canAccessOffense(context, scope, offense);
    }

    private Map<Long, OffenseRecord> loadOffenseAccessMap(List<Long> offenseIds) {
        Set<Long> normalizedIds = new LinkedHashSet<>();
        if (offenseIds != null) {
            offenseIds.stream().filter(Objects::nonNull).forEach(normalizedIds::add);
        }
        if (normalizedIds.isEmpty()) {
            return Map.of();
        }
        LinkedHashMap<Long, OffenseRecord> offensesById = new LinkedHashMap<>();
        offenseRecordMapper.selectList(new QueryWrapper<OffenseRecord>()
                        .select("offense_id", "driver_id", "vehicle_id")
                        .in("offense_id", normalizedIds))
                .stream()
                .filter(Objects::nonNull)
                .filter(record -> record.getOffenseId() != null)
                .forEach(record -> offensesById.put(record.getOffenseId(), record));
        return offensesById;
    }

    private OffenseRecord resolveOffenseForAccess(Long offenseId, Map<Long, OffenseRecord> offensesById) {
        if (offenseId == null) {
            return null;
        }
        OffenseRecord offense = offensesById.get(offenseId);
        return offense != null ? offense : offenseRecordService.findById(offenseId);
    }

    private boolean canAccessDriver(AgentSkillContext context, AccessScope scope, Long driverId) {
        return context.isPrivilegedOperator() || scope.privileged()
                || (driverId != null && scope.driverIds().contains(driverId));
    }

    private boolean canAccessVehicle(AgentSkillContext context, AccessScope scope, Long vehicleId) {
        return context.isPrivilegedOperator() || scope.privileged()
                || (vehicleId != null && scope.vehicleIds().contains(vehicleId));
    }

    private String accessScopeMessage(AgentSkillContext context, AccessScope scope) {
        if (!context.isAuthenticated()) {
            return "未登录，不能核验真实业务数据。";
        }
        if (context.isPrivilegedOperator() || scope.privileged()) {
            return "当前具备管理权限，可按业务条件查询全局案件。";
        }
        if (!scope.isUsable()) {
            return "当前账号缺少身份证关联档案或车辆/驾驶人绑定，暂时只能返回受限提示。";
        }
        return "当前仅返回本人名下、本人驾驶或本人申诉关联的案件记录。";
    }

    private LookupResult found(String summary, List<String> highlights) {
        return new LookupResult(summary, highlights, true);
    }

    private LookupResult notFound(String summary) {
        return new LookupResult(summary, List.of(), false);
    }

    private String formatOffense(OffenseRecord record) {
        return "违法单 " + safe(record.getOffenseNumber()) + " | 状态 " + safe(record.getProcessStatus())
                + " | 时间 " + formatDateTime(record.getOffenseTime()) + " | 地点 " + safe(record.getOffenseLocation())
                + " | 罚款 " + formatAmount(record.getFineAmount());
    }

    private String formatFine(FineRecord record) {
        BigDecimal amount = record.getTotalAmount() != null ? record.getTotalAmount() : record.getFineAmount();
        return "罚款单 " + safe(record.getFineNumber()) + " | 状态 " + safe(record.getPaymentStatus())
                + " | 金额 " + formatAmount(amount) + " | 截止 " + formatDate(record.getPaymentDeadline())
                + " | 经办人 " + safe(record.getHandler());
    }

    private String formatAppeal(AppealRecord record) {
        return "申诉单 " + safe(record.getAppealNumber()) + " | 受理状态 " + safe(record.getAcceptanceStatus())
                + " | 处理状态 " + safe(record.getProcessStatus()) + " | 申诉时间 " + formatDateTime(record.getAppealTime())
                + " | 申诉人 " + safe(record.getAppellantName());
    }

    private List<String> offenseStatuses(String text) {
        if (containsAny(text, "申诉中", "appealing")) return List.of("Appealing");
        if (containsAny(text, "申诉通过", "appeal approved")) return List.of("Appeal_Approved");
        if (containsAny(text, "申诉驳回", "appeal rejected")) return List.of("Appeal_Rejected");
        if (containsAny(text, "未处理", "待处理", "unprocessed", "pending")) return List.of("Unprocessed", "Pending");
        if (containsAny(text, "处理中", "processing")) return List.of("Processing");
        if (containsAny(text, "已处理", "processed")) return List.of("Processed");
        return List.of();
    }

    private List<String> fineStatuses(String text) {
        if (containsAny(text, "逾期", "overdue")) return List.of("Overdue");
        if (containsAny(text, "减免", "waived")) return List.of("Waived");
        if (containsAny(text, "部分支付", "partial")) return List.of("Partial");
        if (containsAny(text, "未支付", "待缴", "unpaid")) return List.of("Unpaid");
        if (containsAny(text, "已支付", "paid")) return List.of("Paid");
        return List.of();
    }

    private List<String> appealAcceptanceStatuses(String text) {
        if (containsAny(text, "已受理", "accepted")) return List.of("Accepted");
        if (containsAny(text, "不予受理", "受理驳回", "rejected")) return List.of("Rejected");
        if (containsAny(text, "补充", "need supplement")) return List.of("Need_Supplement");
        if (containsAny(text, "待受理", "pending")) return List.of("Pending");
        return List.of();
    }

    private List<String> appealProcessStatuses(String text) {
        if (containsAny(text, "审核中", "复核中", "under review")) return List.of("Under_Review");
        if (containsAny(text, "已通过", "approved")) return List.of("Approved");
        if (containsAny(text, "已驳回", "rejected")) return List.of("Rejected");
        if (containsAny(text, "已撤回", "withdrawn")) return List.of("Withdrawn");
        if (containsAny(text, "待处理", "未处理", "unprocessed")) return List.of("Unprocessed");
        return List.of();
    }

    private boolean hasLookupSignal(String message) {
        String text = raw(message);
        if (text.isBlank()) {
            return false;
        }
        String normalized = text.toLowerCase(Locale.ROOT);
        return containsAny(normalized, "查询", "检索", "编号", "id", "状态", "详情", "记录", "案件",
                "车牌", "plate", "驾驶证", "driver license", "license number", "case")
                || Pattern.compile("\\d{2,}").matcher(text).find();
    }

    private boolean containsAny(String message, String... candidates) {
        for (String candidate : candidates) {
            if (candidate != null && message.contains(candidate.toLowerCase(Locale.ROOT))) {
                return true;
            }
        }
        return false;
    }

    private Long extractLongAfterKeywords(String message, String... keywords) {
        for (String keyword : keywords) {
            Matcher matcher = Pattern.compile(Pattern.quote(keyword) + "\\s*[:：]?\\s*(\\d{1,18})", Pattern.CASE_INSENSITIVE)
                    .matcher(message);
            if (matcher.find()) {
                return Long.parseLong(matcher.group(1));
            }
        }
        return null;
    }

    private String extractCodeAfterKeywords(String message, String... keywords) {
        for (String keyword : keywords) {
            Matcher matcher = Pattern.compile(Pattern.quote(keyword) + "\\s*[:：]?\\s*([A-Za-z0-9_-]{3,40})", Pattern.CASE_INSENSITIVE)
                    .matcher(message);
            if (matcher.find()) {
                return matcher.group(1);
            }
        }
        return null;
    }

    private String extractLicensePlate(String message) {
        String value = extractCodeAfterKeywords(message, "车牌", "车牌号", "license plate", "plate");
        if (value != null) {
            return value.toUpperCase(Locale.ROOT);
        }
        Matcher matcher = Pattern.compile("([\\p{IsHan}][A-Z][A-Z0-9]{5,6})").matcher(message.toUpperCase(Locale.ROOT));
        return matcher.find() ? matcher.group(1) : null;
    }

    private String extractDriverLicenseNumber(String message) {
        String value = extractCodeAfterKeywords(message, "驾驶证号", "驾照号", "driver license", "license number");
        return value == null ? null : value.toUpperCase(Locale.ROOT);
    }

    private String formatDateTime(LocalDateTime value) {
        return value == null ? "未知" : value.toString();
    }

    private String formatDate(LocalDate value) {
        return value == null ? "未知" : value.toString();
    }

    private String formatAmount(BigDecimal value) {
        return value == null ? "未知" : value.stripTrailingZeros().toPlainString() + " 元";
    }

    private String safe(String value) {
        return blank(value) ? "未知" : value.trim();
    }

    private String raw(String value) {
        return value == null ? "" : value.trim();
    }

    private boolean blank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private boolean equalsIgnoreCase(String left, String right) {
        return Objects.equals(left == null ? null : left.toLowerCase(Locale.ROOT),
                right == null ? null : right.toLowerCase(Locale.ROOT));
    }

    private record LookupResult(String summary, List<String> highlights, boolean recordsFound) {}

    private record LookupSeed(Set<Long> offenseIds, List<OffenseRecord> records) {
        private static LookupSeed empty() {
            return new LookupSeed(Set.of(), List.of());
        }

        private static LookupSeed of(List<OffenseRecord> records) {
            Set<Long> offenseIds = new LinkedHashSet<>();
            records.stream().map(OffenseRecord::getOffenseId).filter(Objects::nonNull).forEach(offenseIds::add);
            return new LookupSeed(offenseIds, records);
        }
    }

    private record AccessScope(boolean privileged, String idCardNumber, Set<Long> driverIds, Set<Long> vehicleIds) {
        private static AccessScope privileged(String idCardNumber) {
            return new AccessScope(true, idCardNumber, Set.of(), Set.of());
        }

        private static AccessScope empty() {
            return new AccessScope(false, null, Set.of(), Set.of());
        }

        private boolean isUsable() {
            return privileged
                    || (idCardNumber != null && !idCardNumber.trim().isEmpty())
                    || !driverIds.isEmpty()
                    || !vehicleIds.isEmpty();
        }
    }

    private enum Scenario {
        OFFENSE(List.of("违法", "违章", "offense", "处罚"), "/userOffenseListPage", "打开违法记录", "/offenseList", "打开违法列表"),
        FINE(List.of("罚款", "罚单", "缴费", "支付", "fine"), "/fineInformation", "打开罚款信息", "/fineList", "打开罚款列表"),
        APPEAL(List.of("申诉", "复核", "异议", "appeal"), "/userAppeal", "打开申诉页面", "/appealManagement", "打开申诉管理");

        private final List<String> keywords;
        private final String userTarget;
        private final String userLabel;
        private final String managerTarget;
        private final String managerLabel;

        Scenario(List<String> keywords, String userTarget, String userLabel, String managerTarget, String managerLabel) {
            this.keywords = keywords;
            this.userTarget = userTarget;
            this.userLabel = userLabel;
            this.managerTarget = managerTarget;
            this.managerLabel = managerLabel;
        }

        static Scenario match(AgentSkillContext context) {
            for (Scenario scenario : List.of(APPEAL, FINE, OFFENSE)) {
                if (scenario.keywords.stream().anyMatch(context::containsAny)) {
                    return scenario;
                }
            }
            return null;
        }

        ChatAction navigateAction(boolean managerIntent) {
            return managerIntent
                    ? new ChatAction("NAVIGATE", managerLabel, managerTarget, "")
                    : new ChatAction("NAVIGATE", userLabel, userTarget, "");
        }
    }
}
