# printbot

Telegram front-end that turns chat messages into physical prints on a Brother
QL label printer, via the `qlapi` service. This context owns the chat UX:
what a user can send, how it's turned into a printable image, and how they
confirm before anything physical happens.

## Language

**Label**:
One printable unit sent to `qlapi` — either an uploaded photo/PDF/image, or
text rendered by the `/label` command. All labels print on 62mm continuous
tape.
_Avoid_: Print, job (a "job" is qlapi's tracking record for a submitted
label, not the label itself)

**Orientation**:
Which of a label's two dimensions is pinned to the tape's fixed 62mm width;
the other dimension grows to fit the content. **Width-fixed** (the default)
pins the tape-width dimension and lets length grow — best for longer,
wrapped text. **Height-fixed** pins the other dimension instead — best for
short, single-line nameplate-style labels.
_Avoid_: Rotation (that's the mechanism `qlapi` uses to achieve it, not the
user-facing choice)

**Preview**:
The draft state of a `/label` label between the user typing `/label <text>`
and confirming it: rendered image, chosen orientation, and font size, shown
with buttons to adjust and either print or cancel. Nothing is sent to
`qlapi` until the preview is confirmed.
_Avoid_: Draft, pending job

## Example dialogue

> **Dev**: Should `/label`'s orientation toggle button live on the label
> itself, or is it a separate setting?
> **Domain expert**: It's part of the label's Preview — every Preview has an
> Orientation and a font size attached to it, and changing either just
> re-renders the same Preview in place. There's no standalone orientation
> setting.
>
> **Dev**: And once they hit Print?
> **Domain expert**: The Preview's image is submitted as a Label, same as if
> they'd sent a photo. The Preview stops existing at that point — it was
> only ever a staging area before something becomes a real Label.
