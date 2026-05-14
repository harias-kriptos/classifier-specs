# Skill 02: Spec + Threat Model

Use this skill once the brainstorm (Skill 01) is done and the user is ready to write the formal spec.

**Recommended model:** Opus 4.7 (this is the contract the rest of the pipeline depends on; depth beats speed).

**Role:** Architect — see `roles/architect.md`

---

## Context loading

Before starting, read:

1. `roles/architect.md`
2. `templates/SPEC_TEMPLATE.md` — the structure the spec must follow
3. The brainstorm summary the user pastes (output of Skill 01)
4. `context/classifier-v2/ecosystem.md`
5. `context/classifier-v2/current-decisions.md` — stack and pattern decisions already taken
6. `stacks/python-lambda/rules.md` — if the spec is for a Python Lambda

---

## Objective

Produce two artifacts:

1. **`specs/NNN-<slug>.md`** — the formal spec following `SPEC_TEMPLATE.md`. Lives in the product repository.
2. **`docs/security/<slug>-threat-model.md`** — threat model, ONLY if the brainstorm identified a threat surface.

Both are markdown the user copies into the product repo on a feature branch.

---

## Minimal invocation

> "Genera la spec para [feature]" (after Skill 01 has produced a summary)
> "Spec para Ticket 1 con este brainstorm: [paste]"

If no brainstorm summary is provided, refuse and route back to Skill 01.

---

## Procedure

1. Read the brainstorm summary. If sections are missing (no AC, no edge cases), refuse and ask the user to complete Skill 01 first.
2. Pick the next spec number. Convention: `specs/NNN-<slug>.md`. Start at `001` if the repo is empty.
3. Draft the spec following every section of `SPEC_TEMPLATE.md` — do NOT skip sections. If a section doesn't apply, mark it explicitly ("No user-visible behavior change" / "No new ports introduced" / etc.).
4. **Test plan section is mandatory.** For each acceptance criterion from the brainstorm, write at least one test name describing the behavior it asserts. Tests come BEFORE code — that's the TDD contract.
5. **Threat model is mandatory if Skill 01 identified a surface.** Use STRIDE (Spoofing / Tampering / Repudiation / Information disclosure / DoS / Elevation of privilege). One row per relevant threat, with mitigation cited (line of code, test, or config).
6. Open questions section: if any deferred questions remain from Skill 01, list them here as "Deferred — resolve before phase X".
7. Rollout section: include the conventional commit sequence (`chore: spec for <feature>` → `chore: <behavior> (failing)` → `feat: <behavior> (passing)` → `refactor: <what>`).

---

## Required output structure

1. **Spec markdown** ready to be saved as `specs/NNN-<slug>.md` in the product repo. The full content, not a fragment.
2. **Threat model markdown** (only if applicable) ready to be saved as `docs/security/<slug>-threat-model.md`.
3. **Commit plan** — what to commit in what order so TDD enforcement is satisfied.
4. **Siguiente paso:** Skill 03 — Plan, once the spec is committed and (optionally) merged via a spec-only PR.

---

## Operating rules

- Spec content in Spanish, code identifiers and commit messages in English.
- Do not invent acceptance criteria. If the brainstorm didn't capture an AC, ask the user, do not fabricate.
- Do not propose code in the spec — only behavior, contracts, test plan, and threats.
- The spec must be testable. If you can't write a test name for an AC, the AC is not finished.
- Maximum 5 open questions in the final spec. If there are more, the brainstorm wasn't deep enough — route back to Skill 01.
- The spec is the contract. Once committed, downstream skills (03, 04, 05) read ONLY from it. Make it self-contained.
