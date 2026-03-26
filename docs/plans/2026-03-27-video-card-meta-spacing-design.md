# Video Card Meta Spacing Design

## Goal

Reduce the vertical gap between the video title and channel metadata across all shared video cards.

## Scope

- Modify `squirrel-frontend/src/styles/components/video-card.css`

## Approach

- Keep title typography, metadata typography, and card height strategy unchanged.
- Only reduce the spacing between the title block and the metadata row.
- Apply the change in the shared video card stylesheet so all pages using the shared card get the same update.

## Verification

- Run `npm run build:check` in `squirrel-frontend`.
- Confirm the title-to-channel gap is visibly tighter across feed pages.
