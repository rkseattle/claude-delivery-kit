# Rule-book review checks — one definition for every author and reviewer

Rule book R3, R4, R5 and R8 as checks on a change, defined here once. The files that apply
them name each check, but this is the definition they defer to. A reviewer reports each hit
as at least MAJOR, naming every site.

Checks 1–3 count the change and the repo together: a duplicate is no less real because its
other half was already committed. Checks 4–6 apply to the code the change adds or alters.

## Duplication — R5

1. **Existing helper re-implemented.** Logic an existing helper already provides, written
   again. Call the helper. A finding at any count.
2. **Second definition.** A second definition of a business rule, constant, or schema. One
   authoritative definition, at any count.
3. **Third occurrence.** A block of logic with no existing helper that now appears three or
   more times — within a file, across files, or between the change and the repo. Extract a
   shared helper. Exactly two occurrences is not a finding; do not report it. The rule of
   three: a helper shaped by three callers fits them, one guessed from two rarely does.

## Errors and input — R8

4. **Swallowed exception.** A caught exception neither rethrown nor logged, including one
   replaced by a fallback value.
5. **Unvalidated input.** Input from outside the process that crosses a trust boundary —
   from a user, the network, or a file or payload another party controls — used before it
   is validated, or a query built from it without parameters.

## Module boundaries — R3, R4

6. **Reached-into internals.** A read or write of another module's internal state or data
   store that bypasses its public interface. Name the interface it should have gone
   through, or report that the module has none.
