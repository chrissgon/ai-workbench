# Decision tree: what a topic needs decided

Walk the branches in order; later branches depend on earlier ones. Mark each item `known (source)`, `answerable by exploring`, or `must ask`. Skip a branch only when the topic clearly does not have it (a bug fix has no pricing branch), and say so.

## 1. Goal
- What must be true when this is done? Stated as an outcome, not an activity.
- For whom? Which user, customer or system benefits.
- How will we know? The observable signal of success.

## 2. Scope
- What is in, at minimum, for this to count?
- What is explicitly out, or "not now"?
- What existing behaviour must not change?

## 3. Users and context
- Who uses or is affected; what do they do today.
- Where does this run or live (environment, platform, channel).
- Frequency and volume, when they change the design.

## 4. Constraints
- Technical: stack, compatibility, performance, security, accessibility.
- Time and budget, including model or infrastructure cost when AI is involved.
- Brand, legal, privacy, compliance.
- Dependencies on other teams, systems or decisions not yet made.

## 5. Approach
- Which options were considered; why this one. (If none were, that is a `must ask` or a `core-critique` candidate.)
- What would make us change the approach.

## 6. Risks and failure
- What is most likely to go wrong; what happens to the user when it does.
- What is irreversible or public (data loss, external publication, money).

## 7. Done and after
- Acceptance: what a reviewer checks.
- Who owns it after delivery; how it is monitored or measured.

## Ordering rule

Within `must ask`, ask first the decision that the largest number of other items depend on. Goal and scope almost always come first; approach never comes before constraints.
