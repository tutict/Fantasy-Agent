ALTER TABLE payment_record
    ADD COLUMN active_pending_self_service_key VARCHAR(512)
        GENERATED ALWAYS AS (
            CASE
                WHEN deleted_at IS NULL
                    AND LOWER(payment_status) = 'unpaid'
                    AND UPPER(payment_channel) IN ('APP', 'USER_SELF_SERVICE')
                THEN CONCAT(COALESCE(tenant_id, '__platform__'), '|', fine_id, '|', payer_id_card)
                ELSE NULL
            END
        ) STORED,
    ADD UNIQUE KEY uk_payment_record_transaction_id (transaction_id),
    ADD UNIQUE KEY uk_payment_record_active_pending_self_service (active_pending_self_service_key);
