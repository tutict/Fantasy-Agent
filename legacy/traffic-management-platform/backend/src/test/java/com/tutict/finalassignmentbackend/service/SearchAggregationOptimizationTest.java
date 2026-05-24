package com.tutict.finalassignmentbackend.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.entity.DriverInformation;
import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.entity.elastic.DriverInformationDocument;
import com.tutict.finalassignmentbackend.entity.elastic.VehicleInformationDocument;
import com.tutict.finalassignmentbackend.mapper.DeductionRecordMapper;
import com.tutict.finalassignmentbackend.mapper.DriverInformationMapper;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.VehicleInformationMapper;
import com.tutict.finalassignmentbackend.repository.DriverInformationSearchRepository;
import com.tutict.finalassignmentbackend.repository.VehicleInformationSearchRepository;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.kafka.core.KafkaTemplate;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class SearchAggregationOptimizationTest {

    @Test
    void driverSearchShouldPreferAggregatedIndexQuery() {
        DriverInformationMapper driverInformationMapper = Mockito.mock(DriverInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        DeductionRecordMapper deductionRecordMapper = Mockito.mock(DeductionRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        DriverInformationSearchRepository searchRepository = Mockito.mock(DriverInformationSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        DriverInformation driver = new DriverInformation();
        driver.setDriverId(7L);
        driver.setName("Alice");
        SearchHits<DriverInformationDocument> aggregatedHits = driverHits(driver);
        when(searchRepository.searchBroadly("alice", PageRequest.of(0, 20)))
                .thenReturn(aggregatedHits);

        DriverInformationService service = new DriverInformationService(
                driverInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                deductionRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository,
                new ObjectMapper());

        List<DriverInformation> result = service.searchDrivers("alice", 1, 20);

        assertEquals(1, result.size());
        assertEquals(7L, result.get(0).getDriverId());
        verify(searchRepository).searchBroadly("alice", PageRequest.of(0, 20));
        verify(searchRepository, never()).searchByContactNumber(any(), any());
        verify(searchRepository, never()).searchByIdCardNumber(any(), any());
        verify(searchRepository, never()).searchByDriverLicenseNumber(any(), any());
        verify(searchRepository, never()).searchByNamePrefix(any(), any());
        verify(driverInformationMapper, never()).selectPage(any(Page.class), any());
    }

    @Test
    void vehicleSearchShouldPreferAggregatedIndexQuery() {
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        VehicleInformationSearchRepository searchRepository = Mockito.mock(VehicleInformationSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, VehicleInformation> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        VehicleInformation first = new VehicleInformation();
        first.setVehicleId(1L);
        first.setLicensePlate("沪A10001");
        first.setUpdatedAt(LocalDateTime.of(2026, 4, 1, 12, 0));
        VehicleInformation second = new VehicleInformation();
        second.setVehicleId(2L);
        second.setLicensePlate("沪A10002");
        second.setUpdatedAt(LocalDateTime.of(2026, 4, 2, 12, 0));
        SearchHits<VehicleInformationDocument> aggregatedHits = vehicleHits(first, second);
        when(searchRepository.searchBroadly("沪A", PageRequest.of(0, 20)))
                .thenReturn(aggregatedHits);

        VehicleInformationService service = new VehicleInformationService(
                vehicleInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository);

        List<VehicleInformation> result = service.searchVehicles("沪A", 1, 20);

        assertEquals(2, result.size());
        assertEquals(2L, result.get(0).getVehicleId());
        assertEquals(1L, result.get(1).getVehicleId());
        verify(searchRepository).searchBroadly("沪A", PageRequest.of(0, 20));
        verify(vehicleInformationMapper, never()).selectPage(any(Page.class), any());
    }

    @SuppressWarnings("unchecked")
    private SearchHits<DriverInformationDocument> driverHits(DriverInformation driver) {
        SearchHits<DriverInformationDocument> hits = Mockito.mock(SearchHits.class);
        SearchHit<DriverInformationDocument> hit = Mockito.mock(SearchHit.class);
        when(hit.getContent()).thenReturn(DriverInformationDocument.fromEntity(driver));
        when(hits.hasSearchHits()).thenReturn(true);
        when(hits.getSearchHits()).thenReturn(List.of(hit));
        return hits;
    }

    @SuppressWarnings("unchecked")
    private SearchHits<VehicleInformationDocument> vehicleHits(VehicleInformation... vehicles) {
        SearchHits<VehicleInformationDocument> hits = Mockito.mock(SearchHits.class);
        List<SearchHit<VehicleInformationDocument>> searchHits = java.util.Arrays.stream(vehicles)
                .map(VehicleInformationDocument::fromEntity)
                .map(document -> {
                    SearchHit<VehicleInformationDocument> hit = Mockito.mock(SearchHit.class);
                    when(hit.getContent()).thenReturn(document);
                    return hit;
                })
                .toList();
        when(hits.hasSearchHits()).thenReturn(!searchHits.isEmpty());
        when(hits.getSearchHits()).thenReturn(searchHits);
        return hits;
    }
}
