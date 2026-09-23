# What counts as what

## Functional requirement (REQ)

Something the system does, observable by a user or another system: an action, a data change, a rule enforced, an integration call, an output. Form: `REQ-n: <actor or system> <verb> <object> <condition>`. One behaviour per line; two behaviours are two requirements.

## Non-functional requirement (NFR)

A quality with a number: performance (latency, throughput, size), reliability (availability, recovery, data integrity), security (who may do what, what is protected), accessibility (standard and level), compatibility (browsers, devices, versions), operability (build time, deploy path). Form: `NFR-n: <quality> <number and unit> <condition>`. No number, no NFR: ask or mark OPEN.

## Constraint

A limit on how, not what: stack, hosting, existing architecture, decisions already recorded, budget, dates, licences, regulations. Cite the decision or document.

## Acceptance criterion (AC)

What a reviewer checks. Given a state, When an action, Then an observable result; plus `Covers:` with the REQ and NFR ids it verifies. Binary: it passes or it fails. If it needs judgment ("looks right"), it is not an AC yet; find the observable thing.

## Assumption versus open question

- ASSUMPTION: taken as true without a source, low cost if wrong, with the reason it is safe enough. Listed so it can be challenged.
- OPEN: only the user can decide, or the cost of being wrong is high. Names what it blocks. The skill stops and asks when an OPEN blocks a requirement in scope.

## Words that are not requirements

fast, quick, responsive, easy, simple, intuitive, user-friendly, scalable, robust, reliable, secure, gracefully, seamless, modern, clean. Each one needs a number or an observable behaviour next to it, or it goes.
