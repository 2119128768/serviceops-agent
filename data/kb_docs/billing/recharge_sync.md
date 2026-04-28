# Recharge And Quota Synchronization

Recharge payment and quota synchronization are separate steps. A paid order can fail to synchronize quota when the billing event queue is delayed or when the account has a plan binding mismatch.

Support workflow:

1. Verify the order payment status.
2. Verify `quota_sync_status`.
3. If payment is paid and quota sync is failed or pending for more than 15 minutes, escalate to the billing system group.
4. If payment is unpaid, ask the customer to confirm payment channel status.
5. Any manual quota modification requires human approval.
