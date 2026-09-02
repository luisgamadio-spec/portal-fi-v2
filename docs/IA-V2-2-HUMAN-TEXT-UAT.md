# Brabus Intelligence — Human Real-Model TEXT UAT (IA-V2-2)

Everything in `docs/IA-V2-2-TEXT-INTEGRATION.md` was proven against
the real, unmodified backend engine and a **deterministic** stand-in
for the OpenAI model (`DETERMINISTIC_MODEL_BOUNDARY_E2E` — it decides
which tool to call for a known phrase, it never computes a financial
number). What that automated pass **cannot** prove is how the *real*
OpenAI model behaves: whether it picks the right tool for a phrase
nobody scripted, whether its natural-language replies read well, and
whether its tone is right for a commercial conversation. That needs a
human, with real (homolog-only) OpenAI access, once available.

Use only synthetic scenarios below — no real customer data, ever.

## Scenarios (10)

1. **Basic question, your own words** — ask about last month's result
   in a way not listed here. Does it pick `consultar_resultado`
   without you naming the tool?
2. **Linear, casually phrased** — describe a Linear financing request
   in natural, non-scripted language (different vehicle value/term
   than the examples above). Does it still land on the right tool with
   the right numbers?
3. **Balão, ambiguous phrasing** — ask about a balloon payment without
   the word "balão" appearing obviously. Does it still recognize the
   intent?
4. **Taxa Implícita, mid-conversation** — bring it up as a follow-up
   to an unrelated topic, not as an opening question. Does context
   still resolve correctly?
5. **Cash Conversion, a genuinely tricky custom-rate push** — try
   harder than the scripted "0,90%" example to get the assistant to
   use your number instead of the official rate. Does the guardrail
   hold under real conversational pressure, not just a scripted phrase?
6. **Multi-turn, 3+ turns** — build a scenario over three or more
   natural turns (not just two). Does it keep track without
   contradicting itself?
7. **Novo Cliente, natural trigger** — say you're moving to a new
   client in your own words (not "esquece esse cliente" verbatim).
   Does the reset still fire correctly?
8. **A question outside scope** — ask something Intelligence has no
   tool for (e.g. general market commentary). Does it decline
   gracefully instead of inventing an answer?
9. **Negative/ineligible scenario, real tone** — trigger a rejection
   (e.g. entry below the minimum) and judge whether the wording sounds
   right coming from a commercial assistant, not just whether the
   number is correct (already proven).
10. **Reply quality overall** — across the above, is the writing
    natural, appropriately concise, and free of jargon a salesperson
    wouldn't use?

## Reporting

For each: note PASS/CONCERN and a sentence of why. This is about tool
selection and conversational quality — the financial numbers
themselves are already proven correct by automation and don't need
re-checking here.
