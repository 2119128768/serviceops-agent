# Request ID Troubleshooting

Every model API response includes a `request_id`. It is the primary key for support investigation.

The request log can identify:

- account id
- model name
- status code
- error type
- latency
- serving region
- created time

If a ticket contains a request id, support should call `check_api_status` before asking the customer for repeated screenshots.
