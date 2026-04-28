# API Error Codes

## 429 quota exceeded

`429 quota_exceeded` means the request could not be served because account quota or rate-limit policy blocked the call. Support must distinguish between balance quota, QPS rate limit, and delayed quota synchronization.

Required checks:

- Inspect the `request_id` in the API request log.
- If the request maps to `quota_exceeded`, check account quota and recent recharge orders.
- If the request maps to `rate_limited`, explain the QPS limit and suggest retry/backoff.
- Do not promise quota restoration until order payment and quota synchronization status are confirmed.

## 401 authentication failed

`401 authentication_failed` usually means an invalid API key, expired key, or project-level permission mismatch. Ask for project id and request id, but never ask the customer to send the full secret key.

## 503 service unavailable

`503 service_unavailable` usually indicates a platform incident, overloaded model endpoint, or deployment-side failure. Check active incidents and model serving status before sending a resolution.
