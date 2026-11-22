# Error message conventions

<!-- Keep ## headings stable: the setup skill merges by heading. -->

These rules govern every error a user encounters:

- CLI diagnostics.
- Library and SDK errors.
- HTTP API error responses.
- UI validation, alerts, and inline errors.

Out of scope: log formats, stack-trace formats, metrics, warnings, empty states, and success messages. This standard covers the user-facing message text and the behavior and presentation around it: placement, accessibility, status and exit codes, input preservation, and what the message may reveal about internal errors.

These rules apply to English source strings. For another source language, keep the anatomy, security, error-code, and localization rules, and apply the surface profiles using that language's conventions.

Follow this standard for new and changed messages. When a message you are changing disagrees with existing code, fix the message rather than preserving the inconsistency; if a constraint prevents the fix, record the exception under [Project conventions](#project-conventions).

## Project conventions

- **Surfaces:** CLI: `<path or none detected>`; library/SDK: `<path or none detected>`; HTTP API: `<path or none detected>`; UI: `<path or none detected>`. Use `none detected` for the whole field only when no surface exists.
- **Message sources:** `<paths>` or `none detected`.
- **Error codes:** `<format; registry path>` or `none detected`.
- **Localization:** `<system; source locale; placeholder syntax>` or `none detected`.
- **Severity prefix:** `<prefix>` or `none detected`.
- **Exceptions:** `<approved deviations>` or `none detected`.
- **Owner:** `<team or none detected>`; **last reviewed:** `<YYYY-MM-DD>`.

## Prevent the error first

Before writing message text, remove the failure if the product can:

- Validate before submit and show constraints next to the input.
- Offer valid choices instead of accepting free text and rejecting it later.
- Keep the user's work; never make them re-enter data to recover.

If the failure cannot be prevented, it needs a message that meets the rest of this standard.

## Anatomy

Build the prose from these slots, in order:

1. **What happened** — the specific condition. Not "an error occurred".
2. **Context** — the field, object, value, limit, or operation that caused it. Required when it makes the fix possible.
3. **Cause** — only when known and safe to disclose. Never guess.
4. **Action or help** — what to do next, or where to get help. Required for user-facing errors.

Keep a stable machine-readable code in a separate field, never in the prose; see [Error codes](#error-codes).

One message per known cause. If several causes are possible and cannot be distinguished, say what the user can do rather than inventing a cause. A message must be true for every case that can produce it.

One problem per message. Do not combine unrelated failures into one sentence.

The shortest acceptable message names the failed operation and the next step:

> Couldn't save the invoice. Try again.

The fuller form adds safe context and a known cause:

> Couldn't save invoice INV-1042: the customer record was deleted. Restore the customer or choose another one.

## Two registers

Match the register to how the string is displayed. The same sentence is not correct in both places.

| Attribute | Composed | Standalone |
| --- | --- | --- |
| Used by | library/SDK errors, CLI diagnostic lines | UI text, HTTP API human text |
| Capitalization | lowercase, except proper nouns and identifiers | sentence case |
| Terminal punctuation | none | period for full sentences; none for fragments or titles |
| Severity prefix | added by the renderer, never embedded in the string | none; a UI may add a visually hidden `Error:` for screen readers |

Composed strings are fragments: they are printed after a command name, path, or other context. Standalone strings are complete sentences shown on their own.

Examples:

- Composed: `failed to parse config.toml: expected a table at line 12`
- Standalone: `Couldn't save your changes because the file is read-only. Save a copy and try again.`

## Language and tone

- **Be specific.** Name the field, value, operation, and limit. "The image is 12 MB; the limit is 5 MB." beats "The image is too large."
- **Describe the condition, not the person.** Avoid "you entered", "you failed", "invalid", "illegal", and "incorrect" in user prose. Those words are acceptable in developer-facing codes and diagnostics.
- **Prefer the imperative for missing input.** "Enter a name." beats "You didn't enter a name."
- **For a violated rule, state the rule and the offending value, then the fix.** "The postal code must be five or nine digits; 4872953 has seven." beats "Invalid postal code."
- **Stay neutral.** No blame, no anthropomorphism ("the server is confused"), no humour, no exclamation marks, no all-caps, no "oops" or "whoops".
- **No filler.** Drop "please", "sorry", "an error occurred", "something went wrong", and "unexpected error". A narrow exception: one apology is allowed for data loss, an outage, or a fault the product owns; record it under Project conventions.
- **Use plain words.** Expand abbreviations unless the audience uses them. Prefer the project's glossary term over a synonym.
- **Use active voice and present tense.** Contractions are fine. "Can't connect to the database" beats "A connection to the database could not be established."
- **Do not claim what you cannot know.** "The file may be open in another program" only if that is a verified, plausible cause. Otherwise state the failed operation and the next step.

## CLI

- Write diagnostics to `stderr`; write primary output to `stdout`.
- Exit non-zero on failure. Map exit codes to failure modes when callers need to distinguish them.
- Prefix with the program name: `program: message`, or `program:file:line: message` when location matters. A severity prefix such as `error:` belongs to the renderer, not the message string.
- Use the composed register from [Two registers](#two-registers).
- Include the offending path the user supplied, flag, or value, and a next command or `hint:` line.
- Do not print stack traces by default. Show them only for unexpected faults under `--verbose` or `--debug`, or write them to a debug log.
- Group repeated errors under one header instead of repeating the same explanation.
- Offer `--json` when callers need machine-readable errors.
- Keep timestamps, log levels, and debug context out of normal diagnostics; those belong in logs.

## Library and SDK

- Return a typed error, sentinel, or error enum so callers can branch without parsing text.
- Use the composed register from [Two registers](#two-registers) for `Display`/`Error()`/exception text; keep it concise and do not add an `Error:` prefix.
- Wrap an error with the operation that was attempted: `failed to read config.toml: permission denied`. Preserve the cause chain; do not flatten it.
- Wrap only when exposing the wrapped error is acceptable API surface. Do not expose an internal dependency's error type just to add context.
- Include the offending value when it is safe and useful.

## HTTP API

- Return the correct status code, and add a stable problem type or code when the status alone cannot distinguish the error. Keep it separate from occurrence-specific detail; see [Error codes](#error-codes).
- If the project uses RFC 9457, use `type` for the problem class, `title` for the stable summary, `detail` for this occurrence, and `instance` for the request.
- Make `title` stable across occurrences; localize it only. Put changing values in `detail`.
- Add field-level errors as a machine-readable pointer or parameter, not only in prose.
- Be specific for 4xx: the client can act. For 5xx, return a generic sentence, a correlation ID, and a support path; keep the detail in logs.
- Apply [Security](#security) to every response.
- Check permission before not-found, so an access-control error does not reveal whether the resource exists.
- Return a documentation URL when one exists.

## UI and forms

- Put the message next to the field and, for forms, in an error summary that links to each field.
- Associate the message programmatically with the input (on the web, `aria-describedby` and `aria-invalid`) and move focus to the summary or the first invalid field after submission.
- Reuse the field label's language. If the label asks "How many hours do you work a week?", the error says "Enter how many hours you work a week."
- One message per field. If a field has multiple problems, show the first fixable one and revalidate, or combine related constraints into one complete sentence.
- Preserve every value the user entered; never clear the form.
- Use the standalone register from [Two registers](#two-registers).
- Do not rely on colour or an icon alone; state the error in text.
- For messages inserted after page load, use a live region (on the web, `role="alert"` or `aria-live`) that exists at load.
- For codes and correlation IDs, follow [Error codes](#error-codes); prefer a details affordance, otherwise label the reference plainly.

## Error codes

- Define a code when a caller can branch on the error or support must correlate it. Not every message needs one.
- Use a stable, namespaced, machine-readable format, typically `UPPER_SNAKE_CASE` (`AUTH_TOKEN_EXPIRED`). Keep codes short; follow the project's registry limit when one exists.
- Treat codes as API: document them, never reuse a code for a different condition, and deprecate rather than rename when possible.
- Keep the human message out of the contract; clients must not parse it.
- Map codes to HTTP status and CLI exit codes where those surfaces exist.
- Show a code to an end user only as a support reference, not as the explanation. In a UI, prefer a details affordance; otherwise label the reference plainly.

## Placeholders and localization

- Write one complete message per error. Do not build a sentence by concatenating fragments; word order, gender, and agreement differ by language.
- Use named, reorderable placeholders (`{fileName}`, `{limit}`), not bare `%s` or `%d`. If the platform requires positional placeholders, number them.
- Do not fake plurals with `(s)`. Use the platform's plural rules with the language's categories.
- Quote or delimit inserted values so the reader can see where a value starts and ends. Truncate long values and say when a value is empty.
- Format numbers, dates, and currency with the user's locale.
- Do not assume English punctuation or spacing; the platform's message formatter owns sentence assembly.
- Do not reuse one string across different contexts (button, menu, error); translators need the context.
- Give translators the message context, placeholder meaning, and a screenshot or location.

## Security

These rules are mandatory.

- Never include secrets, tokens, credentials, PII, internal hostnames, internal filesystem paths, SQL, or dependency versions in user-facing text.
- A stack trace may appear only behind an explicit debug flag or in a debug log, never in an HTTP response.
- Disclose only values the user supplied or is allowed to see. When in doubt, omit the value and keep it in logs.
- Keep internal detail in logs; user-facing text carries the safe summary.
- Escape interpolated values for the output medium; do not render raw user input as HTML or terminal control sequences.
- Do not let an error reveal whether a protected resource exists.
- Review new messages for leakage before merging. A helpful message that exposes internals is a vulnerability, not a UX improvement.

## Examples

Use this table as a reference, not as text to copy verbatim. A message can fail more than one rule.

| Surface | Avoid | Prefer | Rule |
| --- | --- | --- | --- |
| UI | You didn't enter a name. | Enter a name. | Imperative, no blame. |
| UI | Invalid postal code. | The postal code must be five or nine digits; 4872953 has seven. | State the rule and the value. |
| UI | An error occurred. | Couldn't save the invoice. Try again, or contact support with reference 8f3c2a1. | Specific failure, next step, safe reference. |
| UI | Is the server running? Better go catch it :D. | The server is temporarily unavailable. Try again in a few minutes. | No humour; state the condition and recovery. |
| UI | Password is invalid. | Enter a password with at least 12 characters. | Rule and fix, no "invalid". |
| CLI | `Error: could not open file` | `mytool: cannot open 'config.toml': no such file or directory` | Composed register; name the path and cause. |
| CLI | `mytool: Disk quota exceeded.` | `mytool: disk quota exceeded: 12 GB used; limit is 10 GB` | Lowercase fragment, no terminal period, include the limit. |
| Library | `fmt.Errorf("Failed to open config.toml.")` | `fmt.Errorf("failed to open config.toml")` | Composed register; lowercase, no terminal period. |
| Library | `failed to save` | `failed to save invoice INV-1042: permission denied` | Operation, context, cause. |
| HTTP | `{"error":"Invalid input"}` | `{"type":"https://example.com/problems/postal-code-format","title":"Postal code format","status":422,"detail":"The postal code must be five or nine digits; 4872953 has seven.","instance":"/requests/abc123"}` | Stable type and title; occurrence detail; status. |
| HTTP 5xx | `NullPointerException at com.example...` | `{"type":"https://example.com/problems/internal-error","title":"Request failed","status":500,"detail":"Couldn't complete the request. Try again in a few minutes.","instance":"/requests/abc123","code":"INTERNAL_ERROR","traceId":"8f3c2a1","support":"https://example.com/support"}` | No internals; generic message plus correlation ID and support path. |
| UI with code | Error 500: Internal Server Error | Couldn't load your invoices. Try again. Reference: 4d9e1b7 | Human explanation; code as support reference. |

## Review checklist

- [ ] Names the specific object, field, value, or limit.
- [ ] States the failed operation or violated rule, not just "invalid" or "error".
- [ ] Says what to do next, or where to get help.
- [ ] Is true for every case that can produce it.
- [ ] Uses the correct register from [Two registers](#two-registers).
- [ ] Does not blame the user or use "please"; "sorry" only for the recorded exception; no humour or exclamation marks.
- [ ] Does not expose secrets, PII, SQL, internal paths, or internal versions; no stack traces in normal user-facing output.
- [ ] Can be translated: complete message, named placeholders, plural rules, no concatenation.
- [ ] Preserves the user's input and identifies the field in text.
- [ ] Uses a documented, stable code when a caller can branch or support must correlate.
- [ ] Is one message for one problem.
- [ ] Has the right placement and accessibility wiring for its surface.
