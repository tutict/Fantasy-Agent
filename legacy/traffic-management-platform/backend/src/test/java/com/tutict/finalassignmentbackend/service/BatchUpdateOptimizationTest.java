package com.tutict.finalassignmentbackend.service;

import com.tutict.finalassignmentbackend.entity.VehicleInformation;
import com.tutict.finalassignmentbackend.entity.elastic.VehicleInformationDocument;
import com.tutict.finalassignmentbackend.mapper.DriverVehicleMapper;
import com.tutict.finalassignmentbackend.mapper.OffenseRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.mapper.VehicleInformationMapper;
import com.tutict.finalassignmentbackend.repository.VehicleInformationSearchRepository;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;
import org.springframework.kafka.core.KafkaTemplate;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class BatchUpdateOptimizationTest {

    @Test
    void reassignOwnerIdCardShouldUseSingleBatchUpdateAndSyncIndex() {
        VehicleInformationMapper vehicleInformationMapper = Mockito.mock(VehicleInformationMapper.class);
        DriverVehicleMapper driverVehicleMapper = Mockito.mock(DriverVehicleMapper.class);
        OffenseRecordMapper offenseRecordMapper = Mockito.mock(OffenseRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        VehicleInformationSearchRepository searchRepository = Mockito.mock(VehicleInformationSearchRepository.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, VehicleInformation> kafkaTemplate = Mockito.mock(KafkaTemplate.class);

        VehicleInformation first = new VehicleInformation();
        first.setVehicleId(1L);
        first.setOwnerIdCard("old-id");
        VehicleInformation second = new VehicleInformation();
        second.setVehicleId(2L);
        second.setOwnerIdCard("old-id");
        when(vehicleInformationMapper.selectList(any())).thenReturn(List.of(first, second));

        VehicleInformationService service = new VehicleInformationService(
                vehicleInformationMapper,
                driverVehicleMapper,
                offenseRecordMapper,
                requestHistoryMapper,
                kafkaTemplate,
                searchRepository);

        service.reassignOwnerIdCard("old-id", "new-id", "Alice", "13900000000");

        verify(vehicleInformationMapper).update(isNull(), any());
        verify(vehicleInformationMapper, never()).updateById(Mockito.<VehicleInformation>any());
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Iterable<VehicleInformationDocument>> documentsCaptor = ArgumentCaptor.forClass(Iterable.class);
        verify(searchRepository).saveAll(documentsCaptor.capture());
        List<VehicleInformation> updatedVehicles = ((List<VehicleInformationDocument>) documentsCaptor.getValue()).stream()
                .map(VehicleInformationDocument::toEntity)
                .toList();
        assertEquals(2, updatedVehicles.size());
        assertEquals("new-id", updatedVehicles.get(0).getOwnerIdCard());
        assertEquals("Alice", updatedVehicles.get(0).getOwnerName());
        assertEquals("13900000000", updatedVehicles.get(0).getOwnerContact());
    }
}
