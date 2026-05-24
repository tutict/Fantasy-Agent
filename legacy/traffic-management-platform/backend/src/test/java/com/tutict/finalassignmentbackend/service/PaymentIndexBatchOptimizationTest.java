package com.tutict.finalassignmentbackend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tutict.finalassignmentbackend.config.statemachine.states.PaymentState;
import com.tutict.finalassignmentbackend.entity.FineRecord;
import com.tutict.finalassignmentbackend.entity.PaymentRecord;
import com.tutict.finalassignmentbackend.mapper.PaymentRecordMapper;
import com.tutict.finalassignmentbackend.mapper.SysRequestHistoryMapper;
import com.tutict.finalassignmentbackend.repository.PaymentRecordSearchRepository;
import com.tutict.finalassignmentbackend.service.statemachine.StateMachineService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.transaction.PlatformTransactionManager;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class PaymentIndexBatchOptimizationTest {

    @Test
    void refundPaymentsByFineIdShouldBatchIndexSync() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(100));
        fineRecord.setPaidAmount(BigDecimal.valueOf(100));
        fineRecord.setUnpaidAmount(BigDecimal.ZERO);
        fineRecord.setPaymentStatus(PaymentState.PAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);
        when(fineRecordService.updateFineRecordSystemManaged(any(FineRecord.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
        when(paymentRecordMapper.updateById(any(PaymentRecord.class))).thenReturn(1);
        when(paymentRecordMapper.selectList(any())).thenReturn(List.of(
                buildPaidPaymentRecord(1L, 901L, BigDecimal.valueOf(60)),
                buildPaidPaymentRecord(2L, 901L, BigDecimal.valueOf(40))
        ));

        service.refundPaymentsByFineId(901L, BigDecimal.valueOf(80), "partial refund");

        verify(paymentRecordMapper, times(2)).updateById(any(PaymentRecord.class));
        verify(searchRepository, times(1)).saveAll(any());
        verify(searchRepository, never()).save(any());
    }

    @Test
    void waiveAndRefundPaymentsByFineIdShouldBatchIndexSyncPerDatabaseBatch() {
        PaymentRecordMapper paymentRecordMapper = Mockito.mock(PaymentRecordMapper.class);
        SysRequestHistoryMapper requestHistoryMapper = Mockito.mock(SysRequestHistoryMapper.class);
        PaymentRecordSearchRepository searchRepository = Mockito.mock(PaymentRecordSearchRepository.class);
        FineRecordService fineRecordService = Mockito.mock(FineRecordService.class);
        SysUserService sysUserService = Mockito.mock(SysUserService.class);
        @SuppressWarnings("unchecked")
        KafkaTemplate<String, String> kafkaTemplate = Mockito.mock(KafkaTemplate.class);
        PlatformTransactionManager transactionManager = Mockito.mock(PlatformTransactionManager.class);
        StateMachineService stateMachineService = Mockito.mock(StateMachineService.class);

        PaymentRecordService service = new PaymentRecordService(
                paymentRecordMapper,
                requestHistoryMapper,
                searchRepository,
                fineRecordService,
                sysUserService,
                kafkaTemplate,
                new ObjectMapper(),
                transactionManager,
                stateMachineService);

        FineRecord fineRecord = new FineRecord();
        fineRecord.setFineId(901L);
        fineRecord.setTotalAmount(BigDecimal.valueOf(501));
        fineRecord.setPaidAmount(BigDecimal.valueOf(501));
        fineRecord.setUnpaidAmount(BigDecimal.ZERO);
        fineRecord.setPaymentStatus(PaymentState.PAID.getCode());
        when(fineRecordService.findById(901L)).thenReturn(fineRecord);
        when(fineRecordService.updateFineRecordSystemManaged(any(FineRecord.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
        when(paymentRecordMapper.updateById(any(PaymentRecord.class))).thenReturn(1);
        List<PaymentRecord> firstBatch = new java.util.ArrayList<>();
        for (long paymentId = 1L; paymentId <= 500L; paymentId++) {
            firstBatch.add(buildPaidPaymentRecord(paymentId, 901L, BigDecimal.ONE));
        }
        PaymentRecord secondBatchRecord = buildPaidPaymentRecord(501L, 901L, BigDecimal.ONE);
        List<PaymentRecord> summaryRecords = new java.util.ArrayList<>(firstBatch);
        summaryRecords.add(secondBatchRecord);
        when(paymentRecordMapper.selectPage(any(), any())).thenAnswer(invocation -> {
            com.baomidou.mybatisplus.extension.plugins.pagination.Page<PaymentRecord> page = invocation.getArgument(0);
            if (page.getCurrent() == 1L) {
                page.setRecords(firstBatch);
            } else if (page.getCurrent() == 2L) {
                page.setRecords(List.of(secondBatchRecord));
            } else {
                page.setRecords(List.of());
            }
            return page;
        });
        when(paymentRecordMapper.selectList(any())).thenReturn(summaryRecords);

        service.waiveAndRefundPaymentsByFineId(901L, "waive all");

        verify(paymentRecordMapper, times(501)).updateById(any(PaymentRecord.class));
        verify(searchRepository, times(2)).saveAll(any());
        verify(searchRepository, never()).save(any());
    }

    private PaymentRecord buildPaidPaymentRecord(Long paymentId, Long fineId, BigDecimal amount) {
        PaymentRecord paymentRecord = new PaymentRecord();
        paymentRecord.setPaymentId(paymentId);
        paymentRecord.setFineId(fineId);
        paymentRecord.setPaymentAmount(amount);
        paymentRecord.setRefundAmount(BigDecimal.ZERO);
        paymentRecord.setPaymentStatus(PaymentState.PAID.getCode());
        return paymentRecord;
    }
}
