# PLAN.md — Phase 4: Safety & Polish

**Phase:** 4/4 | **ROADMAP.md requirements:** 6 | **Status:** In Progress

## Goal

Ensure safety features work correctly and add email drafting capability.

## Research

From `.planning/research/PITFALLS.md`:
- Vague questions → agent guesses (prevention: clear "not found" instructions)
- Ambiguous client names → wrong client matched (prevention: ask for clarification)

From `.planning/research/FEATURES.md`:
- Table stakes: "not found" responses, source citation
- Differentiators: Email drafting

## Deliverables

| # | Deliverable | Requirements |
|---|------------|----------------|
| 1 | Safety features solid | SAF-02, SAF-03, SAF-05 |
| 2 | Email drafting works | ED-01, ED-02, ED-03 |

## Execution Steps

### Step 1: Test Agent Never Invents

1. Ask: "What's the client revenue?" (unavailable data)
2. Verify: "Not found" response, NOT invented answer
3. Test with 3 different unavailable data requests

### Step 2: Test No Client Mixing

1. Ask about Client A
2. Immediately ask about Client B
3. Verify: No mixing, correct separate responses

### Step 3: Test Source Citation

1. Ask question requiring document reference
2. Verify: Sources/documents cited in response
3. Test with 3 different queries

### Step 4: Test Email Drafting

1. Test: "Generate follow-up email"
2. Verify: Draft generated
3. Verify: References available documents
4. Verify: Professional tone

### Step 5: Test Ambiguous Client Names

1. Test: Ask about "Client Alpha" (if ambiguous name exists)
2. Verify: Agent asks for clarification
3. Verify: Lists matching options if multiple

### Step 6: Final Polish

1. Review all safety mechanisms
2. Refine instructions if needed
3. Document edge cases handled

## Success Criteria

- [ ] Agent never invents information
- [ ] Agent never mixes two clients
- [ ] Agent cites sources in responses
- [ ] Agent generates follow-up email draft
- [ ] Draft references available documents
- [ ] Draft has professional tone

## Blockers

(None identified yet)

---

*Plan created: 2026-04-28*
*Verification: Run /gsd-verify-work after execution*