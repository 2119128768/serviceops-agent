# Quota Policy

Quota is calculated from the active plan, recharge orders, promotional credits, and enterprise contract limits.

Risk controls:

- Do not expose internal fraud or risk scoring to customers.
- Do not modify quota without approval.
- Do not claim an order is paid unless `query_order_status` confirms it.
- Include account id and order id in internal escalation notes.
