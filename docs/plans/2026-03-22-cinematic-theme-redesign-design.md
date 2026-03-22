# Cinematic Theme Redesign Design

**Date:** 2026-03-22

**Problem**

The current `squirrel-frontend` theme is technically wired correctly, but visually it is still close to stock `shadcn-vue neutral`. Most semantic tokens are near grayscale extremes, so the product reads as plain white or plain black. A second problem is fragmentation: common application surfaces use global shadcn tokens, while dialogs and the video player still rely on hard-coded black and white values.

For a video product, this is the wrong balance. The UI should frame content, not flatten it.

**Design Direction**

The redesign will use a `cinematic editorial` direction:

- Light theme: warm canvas, slightly tinted paper-like surfaces, low glare, strong but not harsh contrast.
- Dark theme: ink slate, deep charcoal surfaces with subtle blue-gray undertones instead of pure black.
- Accent: amber-copper, used sparingly for selected actions, focus, active states, and media-adjacent emphasis.

This keeps the UI restrained enough for thumbnails and playback surfaces while making the interface feel deliberate rather than generic.

**Goals**

- Deliver a complete light and dark theme.
- Replace grayscale-heavy semantic tokens with a cohesive dual-theme system.
- Remove hard-coded black and white from common UI surfaces where it is not structurally required.
- Add a real app theme mode with `light`, `dark`, and `system`.
- Bring the video player into the same visual family without making it lose immersion.

**Non-Goals**

- Pixel-perfect redesign of every view.
- Introducing a design-system abstraction layer on top of shadcn tokens.
- Preserving old visual behavior for compatibility.

**Architecture**

The redesign keeps `shadcn-vue` and Tailwind semantic classes as the source of truth. The work is centered around four layers:

1. Global theme tokens in `src/styles/index.css`
2. Runtime theme mode management for the app root
3. High-frequency app chrome and shadcn component calibration
4. Video player theme consolidation

Theme switching will use a single root contract: `html.dark` toggles the dark token set. The mode source will be:

1. persisted user preference in `localStorage`
2. system theme via `prefers-color-scheme`
3. fallback to light

This avoids compatibility shims and keeps the DOM contract simple.

**Token Strategy**

The semantic tokens will be re-authored rather than incrementally tweaked.

- `background`: warm canvas in light, ink slate in dark
- `card`: visibly separated from background in both themes
- `popover`: more elevated than card, with stronger edge definition
- `muted`: low-emphasis surface and typography channel
- `accent`: hover and active support color, not the brand CTA
- `primary`: amber-copper action color with accessible foreground pairing
- `secondary`: subdued but distinct alternative action surface
- `border` and `input`: quieter than today, but still visible on dense screens
- `ring`: clear focus signal tied to the accent family
- `chart-*`: remapped to the same palette family instead of random defaults

The design explicitly avoids pure `#000` and `#fff` for application surfaces.

**Theme Behavior**

The app will expose three theme modes:

- `light`
- `dark`
- `system`

The selected mode will be stored locally and applied at startup before the app mounts. Settings will include a dedicated appearance control, placed alongside existing user-facing preferences rather than hidden in system configuration.

**Component Strategy**

Base shadcn components will continue to use semantic classes, but the new tokens will change how they render. In addition, several hard-coded overlays and local backgrounds will be replaced with semantic values.

Priority areas:

- buttons
- cards
- inputs
- dialogs and sheets
- dropdowns and selects
- sidebar and top search
- tables and data surfaces
- settings view

The redesign will not introduce ad hoc per-page color fixes unless a page is still visually broken after the token reset.

**Video Player Strategy**

The player remains a separate runtime theme system, but its variables will be rewritten to match the global visual language.

- Dark player: immersive charcoal overlay with restrained highlights
- Light player: bright studio surface without stark white glare
- Shared accent: amber-copper for emphasis and focus moments

Hard-coded white and black values in player theme variables and common chrome will be removed wherever media rendering does not depend on them. Truly media-bound fallback black is allowed only where video or poster areas need it.

**Verification**

The redesign is successful when:

- the app supports manual `light`, `dark`, and `system` mode switching
- the UI no longer looks like stock neutral shadcn
- cards, popovers, sidebars, and tables have visible depth in both themes
- dialogs and overlays no longer default to blunt `bg-black/*` styling
- the video player feels related to the app instead of using a different visual language
- the frontend builds and type-checks cleanly

**Risks**

- Dense data pages may expose weak borders or insufficient contrast after retokening.
- The player theme may need a second pass if subtitle or control readability drops.
- Existing pages that relied on black/white contrast shortcuts may look flat until their local styles are adjusted.

**Decision**

Proceed with a full token rewrite and runtime theme implementation. Do not preserve the old grayscale theme as a fallback.
