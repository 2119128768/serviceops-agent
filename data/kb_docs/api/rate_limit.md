# Rate Limit Policy

Model API plans define QPS, TPM, and concurrent request limits. A `429` can be returned even when the account still has balance if the request exceeds QPS or concurrency limits.

Support workflow:

1. Query the API request status by `request_id`.
2. Query the customer profile and plan limits by `account_id`.
3. If the request is QPS-limited, return the limit policy, retry-after guidance, and upgrade path.
4. If the request is quota-limited, check recharge and quota synchronization.
