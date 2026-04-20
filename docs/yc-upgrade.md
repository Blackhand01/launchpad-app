You are a senior staff engineer working on a startup idea validation platform.

Your goal is to upgrade the existing validator system into a YC-grade decision engine.

The current system:
- Takes a product blueprint
- Runs an LLM validator
- Outputs vision_score, feasibility_score, sandwich_report, pivot

PROBLEM:
The current validator is too optimistic and linear.
It confuses:
- “technology exists” with “product is buildable”
- does not penalize dependency on external infrastructure
- uses naive scoring (vision + feasibility)

We need to transform it into a decision system, not a description system.

---

## TASK 1 — ADD NEW INTERNAL SCORE

Introduce a new internal score:

dependency_score (0–100)

Definition:
0 = fully independent product
100 = fully dependent on third parties

Dependency includes:
- physical infrastructure not controlled by team
- private APIs / entitlements
- required commercial agreements
- hardware owned by others
- platform gatekeepers (Apple, Google, etc.)

---

## TASK 2 — UPDATE FINAL SCORING LOGIC

Replace naive scoring with:

real_feasibility = feasibility_score - (dependency_score * 0.5)

final_score = vision_score * (real_feasibility / 100)

Add also:

if real_feasibility < 40:
    yc_verdict = "NOT NOW"
elif real_feasibility < 60:
    yc_verdict = "ITERATE"
else:
    yc_verdict = "BUILD"

---

## TASK 3 — MODIFY VALIDATOR OUTPUT FORMAT

Update LLM output schema to:

{
  "vision_score": int,
  "feasibility_score": int,
  "dependency_score": int,
  "yc_verdict": "BUILD" | "ITERATE" | "NOT NOW",
  "reasoning": string,
  "pivot_suggestion": string
}

---

## TASK 4 — ENFORCE HARD CONSTRAINTS IN PROMPT

Modify validator system prompt to enforce:

- If infrastructure is required → dependency_score ≥ 70
- If commercial agreements required → dependency_score ≥ 80
- If cannot launch standalone → feasibility_score ≤ 40

Also enforce:

“Do NOT treat existing solutions as proof of feasibility unless the team can build them without permission.”

---

## TASK 5 — ADD SPEED-TO-LEARNING CHECK

Extend reasoning with a new mandatory section:

## Speed Check

Must evaluate:
- Can product be tested in < 7 days?
- Can first user get value immediately?
- Does it require deployment/integration?

If slow → reduce feasibility_score by at least 20

---

## TASK 6 — FRONTEND CHANGE

Update UI:

Instead of showing:
Vision / Feasibility

Show:

- Vision (long-term potential)
- Real Feasibility (after dependency penalty)
- YC Verdict (BIG label)

Add color logic:

BUILD → green
ITERATE → yellow
NOT NOW → red

---

## TASK 7 — LOGGING FOR LEARNING

Store:

- blueprint
- raw scores
- adjusted scores
- verdict

So we can later analyze:
- false positives
- false negatives

---

## TASK 8 — BACKWARD COMPATIBILITY

If old ideas don’t have dependency_score:
- set dependency_score = 50 default
- recompute real_feasibility

---

## TASK 9 — TEST CASES (MANDATORY)

Add unit tests:

Case 1: Social app (no infra)
→ dependency < 20
→ verdict BUILD

Case 2: Skipass BLE system
→ dependency > 70
→ verdict NOT NOW

Case 3: AI analytics app (webcam + meteo)
→ dependency ~30
→ verdict BUILD

---

## TASK 10 — KEEP SYSTEM FAST

- Do not add extra API calls
- Only modify prompt + scoring logic
- No latency increase >10%

---

## OUTPUT

Return:
1. Updated validator prompt
2. Updated scoring function
3. Updated schema
4. Example outputs for 2 ideas

Do NOT explain. Just implement.