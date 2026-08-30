# Human UAT — Landing V2 (Gate 46)

**Technical status: PASS.** That is not the same thing as approval —
only you can decide that. See `docs/AUTHORITY.md` and the Skill's own
Human Approval Gate: tests green ≠ design approved.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html**

## 5 steps

1. Open the Landing V2 (link above).
2. Compare it mentally with the Landing you homologated (in
   FACELIFT-PROTOTYPE-01.2 / the Approved Reference).
3. Navigate through the groupings on the left (Gestão, Novos &
   Seminovos, Score & Salários, Brabus Intelligence, Auditoria).
4. Open a couple of the module blocks in canvas and come back
   (they're honest `NOT MIGRATED` placeholders — that's expected,
   nothing beyond Landing was built this Wave).
5. If you'd like, resize the window or check it on your phone.

You don't need to review any code for this.

## The main question

**"Esta Landing V2 é visualmente a Landing que você homologou?"**

## What happens next

Whatever you decide goes in `config/module-registry.json`'s `landing`
entry (`migrationStatus`) — only you can move it from `UAT_PENDING` to
`HUMAN_APPROVED`. This phase did not do that automatically, and
wouldn't even if every technical test passed with room to spare.
