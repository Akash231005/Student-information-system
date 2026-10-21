# Cross-Domain Innovation Research

Research snapshot: 2026-10-19. The goal is to borrow mechanisms from other disciplines, not decorate SIS with unrelated technology.

## Signals from student reports
- Reddit reports describe repeated registration attempts, confusing reserved seats, waitlist states that appear wrong, and required courses being unavailable.
- Examples: https://www.reddit.com/r/yorku/comments/1upgql5/why_do_they_make_course_enrollment_as/
- https://www.reddit.com/r/ucr/comments/1fcx1lq
- https://www.reddit.com/r/umanitoba/comments/1mbop3w
- https://www.reddit.com/r/UBC/comments/1lelgqb
- https://www.reddit.com/r/OntarioUniversities/comments/1u1q3vu
- These are qualitative reports, not prevalence estimates. Repeated patterns justify hypotheses, not universal claims.

## Cross-domain mechanisms
### 1. Aviation disruption management → academic plan recovery
Airline recovery research treats disruption as a network of interdependent constraints and reallocates resources after an event. A course is a constrained resource; prerequisites, timetable, degree requirements and graduation plans are linked.
Source: https://www.sciencedirect.com/science/article/pii/S0305054809000914
Adaptation: when a required course becomes unavailable, compute feasible alternatives and show downstream impact. Start with graph traversal and rules; do not claim an optimal plan unless an optimizer is implemented.

### 2. Healthcare checklists → academic transaction guardrails
WHO surgical safety checklists use short, repeatable checks at consequential transition points; success depends on local adaptation, team engagement and feedback.
Sources: https://www.who.int/teams/integrated-health-services/quality-of-care-and-patient-safety/patient-safety-guidance-and-tools/safe-surgery/tool-and-resources
https://www.who.int/publications/i/item/9789241598590
Adaptation: a pre-enrollment safety check confirms prerequisites, timetable, credit limit, reserved-seat eligibility and degree relevance before committing. It must use current authoritative rules and still revalidate transactionally at commit time.

### 3. Toyota jidoka/andon → stop unsafe academic state changes
Toyota describes stopping a process when an abnormality is detected and making the issue visible.
Source: https://global.toyota/en/company/plant-tours/production-system/
Adaptation: if enrollment invariants fail, freeze further writes for the affected course, surface an incident, and preserve diagnostic evidence rather than silently continuing. For a lab, simulate the tripwire and recovery.

### 4. Resilience engineering → protect critical work from noisy neighbors
Bulkheads limit concurrency/queues so one overloaded operation cannot consume every resource.
Source: https://resilience4j.readme.io/docs/bulkhead
Adaptation: isolate login, search, and enrollment capacity; keep slow crawler/resource indexing from exhausting registration workers. Measure whether critical enrollment requests remain responsive.

### 5. Event sourcing/audit concepts → explain changes over time
Adaptation: record grade/attendance changes as immutable audit events (actor, timestamp, reason, old/new value or safe reference) while retaining a conventional current-state table. Avoid adopting full event sourcing unless it earns its complexity.

### 6. Jobs-to-be-Done → discover the actual outcome
Users do not want “a registration API”; they want to progress through their degree without administrative uncertainty.
Source: https://online.hbs.edu/blog/post/jobs-to-be-done-examples
Adaptation: define user jobs and failure outcomes before selecting technology.

## Important caution
Many universities already provide degree audits, waitlists, and what-if planning. Penn State and Vanderbilt document degree-audit/what-if functions:
- https://www.registrar.psu.edu/degree-planning/degree-audit.cfm
- https://registrar.vanderbilt.edu/registration/yes-help/degree-audit-undergrad/
Therefore, do not claim the individual feature is novel. Investigate the gap in our particular combination: explainable course-unavailability recovery, safe enrollment, and experimentally measured overload behavior.

## Innovation validation protocol
1. State the user pain as a falsifiable hypothesis.
2. Find evidence in multiple independent reports or institutional documentation.
3. Search for existing systems/features before claiming novelty.
4. Prototype the smallest useful mechanism.
5. Define a baseline and measurable outcome.
6. Test adverse cases and failure modes.
7. Document what is genuinely new in our integration and what is established prior art.
