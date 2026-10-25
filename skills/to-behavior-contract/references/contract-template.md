# Contract template

Use this skeleton when `docs/behavior/` has no established shape; follow the existing contracts' shape when it does. Keep only the sections the feature uses, and delete the rest.

## Skeleton

```markdown
# <Feature>

<One paragraph: what the feature does, its boundary, and the behavior it owns.>

## Inputs

<What reaches the feature: fields, events, calls, their ranges, and required combinations.>

## Rules

<The exact rules, numbered or tabulated. Use pseudocode or a schema when it pins behavior more precisely than prose.>

## States

| From | Trigger | To |
| --- | --- | --- |
| <state> | <event with its condition> | <state> |

<Omit when the feature has no state.>

## Outputs and effects

<Return values, records written, messages sent, and user-visible effects.>

## Errors

| Condition | Outcome |
| --- | --- |
| <failure the caller can observe> | <error and what follows> |

<The error taxonomy: every observable failure and its outcome.>

## Composition

<How this behavior combines with other features, as references to their contracts.>

## References

- `docs/behavior/<path>.md` § <Heading>
- `docs/adr/<file>.md`

<Link shared behavior and the reasoning. Each meaning appears once in the tree.>
```

## Worked example

```markdown
# Refund window

A refund may be issued against a paid invoice within 30 days of payment. The refund window belongs to refunds; invoice states belong to `docs/behavior/invoices.md` § Invoice states.

## Inputs

- `invoice`: a paid invoice.
- `requested_at`: the time the refund is requested, in UTC.

## Rules

1. A refund is allowed when `requested_at` is at most 30 days after the invoice's payment time.
2. The refund amount is the invoice's remaining refundable amount (`docs/behavior/invoices.md` § Invoice states).
3. A refund never exceeds the remaining refundable amount.

## Outputs and effects

A successful refund writes one refund record and returns its amount; the invoice's resulting state is defined in `docs/behavior/invoices.md` § Invoice states.

## Errors

| Condition | Outcome |
| --- | --- |
| `requested_at` is past the window | Reject with `refund_window_closed`; no state change |
| The amount exceeds the remaining refundable amount | Reject with `refund_exceeds_remaining`; no state change |

## Composition

Refunds change invoice state as defined in `docs/behavior/invoices.md` § Invoice states.

## References

- `docs/behavior/invoices.md` § Invoice states
- `docs/adr/0012-refund-window.md`
```
