You are grading the output of an AI assistant against a list of assertions.

Rules:
- An assertion passes only when there is concrete evidence in the response or in the produced files. Quote that evidence.
- Do not give the benefit of the doubt. "Probably" is a fail.
- Judge only what the assertion says; do not reward unrelated quality.
- Reply with a JSON array and nothing else: [{"id": 1, "text": "<assertion>", "passed": true, "evidence": "<quote or file:line>"}, ...]

## Task prompt given to the assistant

{prompt}

## Assistant response

{response}

## Files produced by the assistant (path, then content; truncated)

{files}

## Assertions

{assertions}
