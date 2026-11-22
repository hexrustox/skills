# Logging conventions

These conventions govern the log records this project writes. They cover the record's shape, its message, its severity, and its safety. Logger configuration, destinations, retention, dashboards, and alerting are out of scope; user-facing error messages are a separate artifact.

## Project profile

The values below are this project's choices. The setup skill fills and confirms them with the project owner; change them deliberately, not per call.

| Choice | Value |
| --- | --- |
| Record format | Structured JSON |
| Field naming | Namespaced fields use dots (`service.name`, `error.type`); scalar and application fields use flat `snake_case` (`timestamp`, `order_id`) |
| Timestamp | `timestamp`, RFC 3339 in UTC (`2026-11-22T14:03:05.123Z`) |
| Message style | Capitalized first word, no terminal period |
| Language | English (US) |
| Event names | `event.name`, dotted lowercase (`order.placed`), when an event is monitored or queried |
| Levels | Native names mapped to `TRACE`–`FATAL`; omit levels the logger lacks |

Examples show records; emit them with the project's logger API and the profile's field names.

## One event, one record

A log call records one event. Keep the message constant for that event and pass variable data as fields. A constant message can be searched, counted, and alerted on; fields carry the specifics. Pass values as parameters or fields; do not interpolate them into the message, concatenate strings, or format the message yourself.

Write one record per line. Put a stack trace in one structured field; do not emit one record per line of a stack trace.

```text
Good: {"message": "Order placed", "event.name": "order.placed", "order_id": "o-123", "total_cents": 4200}
Bad:  {"message": "Order o-123 placed for 4200; email queued; invoice created"}
```

When an event is monitored, alerted on, or queried across services, give it a stable event name in the profile's event field. Use dotted lowercase by default. The event name identifies the event; the message may change without changing the name.

## Record format

Use the profile's record format. Structured means a stable schema, not merely JSON: the same fields with the same meanings on every record. Do not hand-build a serialized record; let the logger encode it. Plain text is acceptable only for local development or a CLI whose output is the product; production services use a structured format.

## Fields

Every record carries the timestamp, level, message, and service identity. Let the logger add them, including source location; do not write them into the message. When handling a request, attach trace and span IDs from the context; never invent them or create a new trace ID for a log line.

Use the profile's field naming, and reuse the same name for the same concept across services. Namespaced fields keep their dotted names; scalar and application fields stay flat in `snake_case`. Do not let one service use `orderId`, another `orderID`, and another `oid`. Put high-cardinality values (request IDs, user IDs, order IDs, raw URLs) in ordinary fields, not in index labels or metric dimensions.

Do not repeat a value in both the message and a field. The message names the operation and the object type; fields carry the identity and the data.

## Message language

Write for an operator who did not read the code. Use the profile's language and message style. Write in the active voice. Omit the actor when it is the program itself; name the actor when it is not. Use a past-tense verb for completed events and failed attempts, the present tense for states and invariants.

Name the object type; never log a bare identifier. Start messages with the capitalization and punctuation in the profile. No first person, exclamation marks, or emotional language. Spell out abbreviations, and use the project's glossary term rather than a synonym.

```text
Good: {"message": "Deleted pod", "pod_name": "api-7f9c"}
Bad:  {"message": "deleted api-7f9c."}

Good: {"message": "Could not publish message", "message_id": "m-42"}
Bad:  {"message": "Publish failed"}
```

## Errors

A failure message names the operation and the object type; it does not carry the cause. Put the cause in the structured error fields, for example `error.type`, `error.message`, and `exception.stacktrace`. Preserve the cause chain; do not replace a specific error with `unknown error` or discard the underlying error.

Log the failure once, where it is handled or at the process boundary. Library code returns errors; it does not log them. Do not log the same failure in the repository, service, and handler.

Expected, handled failures are `WARN` when the operation degraded or a person may need to act, and `INFO` when the outcome is routine. Do not log expected validation failures, 404s, or handled retries at `ERROR`.

Keep operator logs and user-facing errors separate. Operator logs carry technical detail and correlation; user-facing messages are short, actionable, localized, and free of internal causes. Do not log the user-facing string as the event message.

```text
Good: {"message": "Could not publish message", "message_id": "m-42", "error.type": "BrokerUnavailable", "error.message": "connection refused"}
Bad:  {"message": "Publish failed: connection refused"}
```

## Severity

Use the levels the logger provides, mapped to these meanings. Do not invent levels such as `NOTICE2` or `VERBOSE` or expose new level names to consumers. If the logger has fewer levels, map its names to the closest meaning; if it has more, map them at the adapter.

| Level | Use for | Not for |
| --- | --- | --- |
| `TRACE` | Step-level detail for tracing one execution | Normal operation; production by default |
| `DEBUG` | Diagnostic detail used while developing or investigating | Production by default |
| `INFO` | Significant normal events and state changes: startup, shutdown, configuration loaded, order placed | Per-request chatter, loop iterations |
| `WARN` | Degraded but handled, or a condition that should not happen but does not stop the operation: a retry succeeded, a deprecated option was used | Normal successful events |
| `ERROR` | An operation failed and a person may need to act | Expected validation failures, 404s, handled retries |
| `FATAL` | The process cannot continue | Libraries, recoverable errors |

Libraries never emit `FATAL` or exit the process.

## Safety

Never log secrets: passwords, tokens, API keys, session IDs, authentication headers, connection strings, or private keys. Do not log PII or request/response bodies by default. Redact, hash, or truncate sensitive values at the logging boundary; do not rely on the backend to remove them later.

Treat every logged value as untrusted. Use the logger's structured encoding, which escapes CR/LF and control characters, and cap the length of free-form values. Do not log per item in a hot loop; aggregate or sample. Sample `DEBUG` and `TRACE`, not `ERROR`.

## Tests

Use the logger's parameterized form; do not pre-format the message with f-strings, concatenation, or string formatting. In tests, assert on structured fields and event names, not on rendered text. Keep event names and field meanings stable; version the schema when a field is renamed or retyped.

## Review checklist

- [ ] One event per record; the message is constant and variable data is in fields.
- [ ] Monitored events have a stable event name; the message can change without it.
- [ ] The message names the operation and object type; no secrets or PII.
- [ ] The severity matches the definitions; a failure is logged once at the boundary.
- [ ] Errors use structured error fields and preserve the cause chain.
- [ ] Field names and format match the project profile.
- [ ] Values are passed as parameters, not interpolated into the message.
- [ ] Tests assert on fields and event names, not rendered text.
