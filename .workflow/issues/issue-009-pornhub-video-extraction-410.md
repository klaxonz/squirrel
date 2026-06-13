---
title: Pornhub video extraction returns HTTP 410 for normal videos
status: fixed
severity: high
category: runtime
locations:
  - squirrel-site-runtimes/pornhub/src/squirrel_pornhub/extractor.py
source: manual
fixed_by: designs/des-fix-issue-009-pornhub-video-extraction-410.md
---

# Pornhub video extraction returns HTTP 410 for normal videos

## Phenomenon

Backend collection for Pornhub videos now fails with HTTP 410 across videos.

## Reproduction Evidence

User report: Pornhub video parsing in backend collection has become 410.

## Current Findings

- Backend collection uses the Pornhub site runtime extractor, which delegates video extraction to yt-dlp.
- The extractor sends normal headers and age-gate cookies, but does not enable yt-dlp browser request impersonation.
- Current Pornhub request behavior can return 410 to non-browser-like requests, so treating all 410 responses as deleted videos is incorrect for this failure mode.

## Impact

Pornhub collection cannot ingest normal videos and may incorrectly classify reachable videos as failed extraction records.

## Fix Attempts

- Enabled yt-dlp browser request impersonation for Pornhub extraction.
- Mapped explicit HTTP 410 yt-dlp failures to network/access failures.
- Added focused extractor regression tests.
- Verified with Pornhub extractor tests and ruff.
- Verified the reported `cn.pornhub.com` URL in the backend pipenv extractor path.
