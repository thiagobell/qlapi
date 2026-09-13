# Agent notes

## Tests

```
cd qlapi && uv run pytest
cd printbot && uv run pytest
```

## Looking at the UI

You have a real browser via the Playwright MCP. Use it *while* you work on
anything user-visible, not as a final formality: start the app, drive the
page, see what your change actually does, adjust, look again.

Start the app first (it runs fine without a printer attached):

```
cd qlapi && uv run uvicorn qlapi.app:app --port 8000 &
```

Then navigate to `http://127.0.0.1:8000/` or `/static/editor.html` and
interact. Prefer `browser_snapshot` for reading structure and finding
elements -- it's cheaper and more precise than an image. Take a screenshot
when the question is *visual*: spacing, alignment, contrast, overlap,
clipping, whether the thing looks right.

**Read the screenshots you take.** They're evidence, not decoration. Confirm
the change rendered as intended and check you didn't break something next to
it. If it looks wrong, fix it and look again.

Click into the state your change lives in. A screenshot of a page that
doesn't show your change proves nothing -- open the modal, trigger the error,
resize the viewport, hover the thing.

You decide whether any of this is warranted. Backend, config, or test-only
changes don't need a browser.

Screenshots land in `tmp/screenshots/` and CI uploads them as the
`screenshots` artifact. If you kept any, say in the PR body what you checked
and what you saw, then link:

`[Screenshots](https://github.com/OWNER/REPO/actions/runs/$GITHUB_RUN_ID#artifacts)`

If you didn't take any, say nothing about screenshots.
