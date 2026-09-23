# Lenses: where proposals fail, by domain

Take the lens set for the proposal's domain plus "Any proposal". For every category, ask "how does this fail?" and keep only failures with a concrete trigger and an observable impact.

## Any proposal

| Category | Ask |
|----------|-----|
| Goal alignment | Does it achieve the stated goal, or a symptom of it? What part of the goal does it leave untouched? |
| Unstated assumptions | What must be true for this to work that the proposal never says? Who verified it? |
| Contradictions | Which recorded decision, artifact or code does it disagree with? |
| Reversibility | What is irreversible, public or costly if wrong? How would we roll back? |
| Dependencies | What must exist or be decided first? Who owns it? |
| Measurement | How would we know it worked? What would we see if it failed silently? |

## Engineering

| Category | Ask |
|----------|-----|
| Data | Null, empty, invalid format, special characters, boundary values, missing fields, encoding. |
| Timing | Races, timeouts, out-of-order events, duplicates, retries, stale reads. |
| State | Missing or already-existing resource, unauthorized, expired session, invalid transition, partial update. |
| Integration | Dependency down, unexpected response, contract change, partial failure, auth failure. |
| Scale | Large inputs, concurrency, batch limits, rate limits, storage, N+1, memory. |
| Consumers | Who calls or reads what changes? Which contract, schema, event or monitor breaks? |
| Security | New input surface, authorization gap, secrets, injection, validation only on the client. |
| Root cause | Does it fix the cause named in the root-cause document, or the symptom? |

## Business

| Category | Ask |
|----------|-----|
| Problem evidence | Who said this is a problem, in their words? How many? Or is it inferred? |
| Market | Bottom-up sizing exists? Alternatives and substitutes named, including "do nothing"? |
| Customer | Who pays versus who uses? Can they be reached? What do they do today? |
| Model | Unit economics with real costs? Willingness to pay evidenced or assumed? |
| Distribution | Which channel, why it works for this customer, what it costs to acquire one? |
| Risk | Regulation, platform dependence, single customer, single channel, key person. |
| Kill criteria | What result would make us stop? Is it written down? |

## Product

| Category | Ask |
|----------|-----|
| User and job | Which user, which job, which trigger? Is there evidence or a persona invented for the document? |
| Scope | What is explicitly out? What happens at the edges of "in"? |
| Acceptance | Can a reviewer check each criterion without asking the author? |
| Failure states | What does the user see when it fails, is empty, is slow, is unauthorized? |
| Metrics | Which number moves? Which number must not move? |
| Sequencing | What must ship first? What is blocked by a decision not made? |

## Design

| Category | Ask |
|----------|-----|
| Flow | Where does the user get lost, go back, or abandon? Is every state (empty, loading, error, success) drawn? |
| Accessibility | Keyboard, contrast, screen reader, motion, target size. |
| Consistency | Which existing pattern or token does it break? Why? |
| Content | Is the copy real or placeholder? Does it fit at the longest realistic length and in other locales? |
| Responsiveness | Which breakpoint or input method was not considered? |
| Handoff | Can engineering build it without asking? What is left to judgment? |

## Marketing

| Category | Ask |
|----------|-----|
| Audience | Is the message for the customer defined in business artifacts, or for everyone? |
| Claim | Is every claim true and demonstrable? What would a skeptical reader check? |
| Channel | Why this channel for this audience? What is the evidence they are there? |
| Timing | What else happens that day or week? What depends on something not ready? |
| Measurement | Which metric, measured how, compared to what baseline? |
| Brand | Does it match the recorded voice and identity? Where does it drift? |
| Irreversibility | Once published, what cannot be undone? Who approved the exact payload? |

## AI features

| Category | Ask |
|----------|-----|
| Quality bar | What counts as a good output, written down? How is it measured, on what set, how often? |
| Hallucination | What happens when the model is confidently wrong? Does the user see uncertainty? |
| Grounding | Where does the model get facts? What happens when retrieval returns nothing or the wrong thing? |
| Cost | Cost per request and per user per month at the expected volume? What is the ceiling and what happens at it? |
| Latency | Acceptable wait? Streaming, fallback, timeout behaviour? |
| Safety and privacy | Prompt injection through user or retrieved content? Personal data in prompts, logs or training? |
| Fallback | What does the feature do when the model or provider is unavailable? |
| Evaluation drift | Is the eval set from the same distribution as real use? Who updates it? |
