---
type: fix
name: issue-009
status: implemented
related_requirement:
related_issue: issues/issue-009-pornhub-video-extraction-410.md
---

# Fix Design: Pornhub extraction uses browser request impersonation

## Root Cause

Pornhub now returns HTTP 410 for requests that do not match browser-level request behavior. The current Pornhub runtime passes headers and age-gate cookies into yt-dlp, but it does not ask yt-dlp to impersonate a browser transport, so yt-dlp can fail before extracting normal video metadata.

## Fix Approach

1. Add the yt-dlp curl-cffi extra to the Pornhub plugin dependency so yt-dlp can perform browser request impersonation.
2. Set the Pornhub yt-dlp option `impersonate` to the Chrome `ImpersonateTarget`.
3. Classify explicit HTTP 410 yt-dlp failures as network/access failures instead of parse failures or deletion, because the current symptom is site request rejection across normal videos.
4. Add focused extractor tests for the new yt-dlp option and 410 error mapping.

## Files

- `squirrel-site-runtimes/pornhub/pyproject.toml`: require yt-dlp with curl-cffi support.
- `squirrel-site-runtimes/pornhub/src/squirrel_pornhub/extractor.py`: enable browser impersonation and map HTTP 410.
- `squirrel-site-runtimes/tests/test_pornhub_extractor.py`: cover impersonation and 410 handling.

## Risks

The change is limited to Pornhub video extraction. Environments must reinstall the Pornhub plugin dependencies so the new yt-dlp extra is available.

## Verification Results

Verification: lint Y  type-check SKIP  test Y  manual SKIP

- Lint: `pipenv run ruff check pornhub/src/squirrel_pornhub/extractor.py tests/test_pornhub_extractor.py` passed.
- Test: `pipenv run pytest tests/test_pornhub_extractor.py` passed with `6 passed`.
- Manual: `squirrel-backend` pipenv with `PYTHONPATH` pointed at the Pornhub runtime and SDK successfully extracted metadata for `https://cn.pornhub.com/view_video.php?viewkey=6702f622604d5`.
