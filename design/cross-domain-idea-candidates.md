# Cross-Domain Idea Candidates

These are hypotheses to evaluate, not claims that no university has built them. Scores are preliminary: user value, differentiation potential, feasibility for a student lab, and evidence potential.

## A. Degree Path Recovery Engine
**Borrowed from:** airline disruption recovery and graph planning.
**User pain:** a required course fills or a timetable conflict blocks enrollment; the student doesn't know the downstream impact.
**Mechanism:** model prerequisites and degree requirements as a graph. When a course becomes unavailable, list feasible alternatives, courses unlocked/blocked, and estimated term impact. Include why each suggestion is valid.
**Distinctive angle:** “If this course is unavailable, what is the least disruptive valid path to graduation?”
**MVP:** synthetic degree rules + graph traversal + deterministic ranked alternatives.
**Evaluation:** valid alternatives, constraint violations, time to produce suggestions, cases with no feasible alternative.
**Risks:** degree rules vary; never present hypothetical plans as official approval.
## B. Registration Preflight / Academic Safety Case
**Borrowed from:** aviation pre-flight checks and healthcare safety checklists.
**User pain:** students discover prerequisite, timetable, reserved-seat, or credit-limit problems only after trying to register.
**Mechanism:** before submission, run a concise preflight checklist and explain blockers; revalidate every rule inside the database transaction before committing.
**Distinctive angle:** convert hidden institutional rules into a transparent, auditable decision.
**MVP:** rules engine that returns pass/warn/block with rule IDs and evidence.
**Evaluation:** blocked-invalid-attempt rate, false warnings, false accepts, explanation completeness.
**Risks:** preflight is not a reservation; capacity can change between preview and commit.
## C. Academic Andon: Stop the Line on Integrity Failure
**Borrowed from:** Toyota jidoka/andon.
**User pain:** a data inconsistency or failed invariant may silently corrupt enrollment/grades.
**Mechanism:** invariant monitors detect impossible states (active enrollments > capacity, duplicate student-course enrollment, grade change without actor). Pause writes for the affected scope, preserve an incident record, and expose a recovery workflow.
**Distinctive angle:** treat academic data integrity as an operational safety signal, not just a log entry.
**MVP:** controlled fault injection + invariant monitor + incident panel + admin resolution.
**Evaluation:** detection time, blast radius, recovery time, false alarms.
**Risks:** automatic stop must be scoped; don't bring down all registration for a harmless anomaly.
## D. Critical-Path Capacity Isolation
**Borrowed from:** aircraft/industrial resource allocation and resilience bulkheads.
**User pain:** slow search, crawler tasks, or notification bursts compete with registration for shared workers and connections.
**Mechanism:** separate bounded concurrency pools and budgets for enrollment, search, and background jobs. Under overload, degrade noncritical work before the authoritative enrollment path.
**Distinctive angle:** prove that the most consequential operation survives noisy neighbors.
**MVP:** one service with separate semaphores/queues and synthetic background load.
**Evaluation:** enrollment p95/error rate with and without isolation, unused capacity, rejected background tasks.
**Risks:** too much isolation wastes resources; define priorities transparently.
## E. Waitlist as a Constraint-Aware Exchange
**Borrowed from:** matching markets and constraint scheduling.
**User pain:** a student wants Course B but holds Course A; a seat opening may cause a timetable conflict or leave capacity unused.
**Mechanism:** support a declared “swap A for B if eligible and conflict-free” intent. Evaluate both sides and commit atomically so a student is not left with neither course.
**Distinctive angle:** optimize a real academic outcome, not just queue position.
**MVP:** two-course swap with strict transaction and capacity invariants.
**Evaluation:** successful valid swaps, stranded students, seat utilization, fairness policy.
**Risks:** complex matching and policy questions. Start with a deterministic queue and explicit opt-in; do not claim globally optimal allocation.
## F. Explainable Academic Decision Ledger
**Borrowed from:** event logs, audit trails, and explainable decision systems.
**User pain:** “Why was I rejected?” or “Who changed my grade?” is hard to answer from current state alone.
**Mechanism:** attach stable rule codes, timestamps, actor and relevant version to outcomes; keep a safe, append-only change history for grades/attendance.
**Distinctive angle:** reconstruct not only the current state but the reason for the decision at that time.
**MVP:** registration decision record plus grade-change audit.
**Evaluation:** can an auditor reconstruct a test case; audit completeness; extra write latency.
**Risks:** minimize personal data and never leak private information through explanation messages.
## G. Registration Demand Radar
**Borrowed from:** capacity planning and queueing theory.
**User pain:** administrators learn about bottleneck courses only after students complain.
**Mechanism:** aggregate anonymous demand signals: waitlist length, failed eligible attempts, search-to-enrollment conversion and repeated timetable conflicts. Flag course offerings where demand exceeds capacity.
**Distinctive angle:** turn operational telemetry into planning evidence for future section capacity.
**MVP:** synthetic aggregate dashboard; no individual profiling.
**Evaluation:** forecast error against a generated demand scenario, false alerts, lead time before capacity breach.
**Risks:** clicks are not guaranteed intent; never infer student need from search alone.
## H. “What Changed?” Semester Diff
**Borrowed from:** version control and infrastructure-as-code plans.
**User pain:** timetable, seat limits, prerequisites, and room assignments change, but students cannot tell what changed or what it means for them.
**Mechanism:** version semester catalogues; compute a diff and identify affected enrolled students, timetable conflicts, and degree-path consequences.
**Distinctive angle:** academic schedule changes become reviewable change sets, not silent overwrites.
**MVP:** compare two synthetic timetable versions and produce impact summaries.
**Evaluation:** affected-student recall, false positives, processing time, ability to reverse a change.
**Risks:** notification fatigue and privacy; send only relevant changes.
