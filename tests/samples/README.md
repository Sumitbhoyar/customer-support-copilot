# Sample payloads for manual testing

- `ticket_happy_path.json`: valid payload for `POST /tickets`. Use with `curl -X POST -H "Content-Type: application/json" -d @tests/samples/ticket_happy_path.json https://<ApiEndpoint>/tickets`.
- `ticket_bad_payload.json`: invalid payload that should return HTTP 400 from `POST /tickets`.
- `context_request.http`: example HTTP request for `GET /tickets/{id}/context` (or with `?customer_external_id=...`).

Notes:
- Replace `<ApiEndpoint>` with the value from your deployment outputs.
- `created_at` should stay in ISO-8601 format with timezone (Z).
- `customer_external_id` must match an ID that exists in your Postgres/DynamoDB data; otherwise `/tickets` will still return 200 but without KB suggestions if context is missing. `GET /tickets/{id}/context` will return 404 for unknown customers.
