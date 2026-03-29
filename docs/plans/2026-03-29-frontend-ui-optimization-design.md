# Design: Cyber-Sync Tactical Terminal Frontend Optimization (2026-03-29)

## Overview
This design transforms the Squirrel frontend into a cohesive "Cyber-Sync Tactical Terminal" aesthetic. It builds upon the existing "Neon Pulse" sidebar, extending the high-contrast, cyberpunk-inspired visual language across the Sync Center, Video Feed, and Plugin Manager modules.

## Core Visual Language
- **Color Palette:** Deep Black (`#050505`), Neon Orange (`#ff4d00`), Muted White (`rgba(255, 255, 255, 0.8)`), and Tactical Gray (`rgba(255, 255, 255, 0.05)`).
- **Typography:** `JetBrains Mono` for all technical data (IDs, versions, timestamps, counts). `IBM Plex Sans` for main labels.
- **Textures:** Pixel dot patterns (`radial-gradient`), 1px borders, and "Viewfinder" corner marks.
- **Animations:** 150ms Glitch transitions, pulsing LED status indicators, and "Backlight Glow" hover effects.

---

## Module 1: Sync Center (Cyber-Sync Dashboard)
**Goal:** Transform the sync management area into a real-time signal monitoring station.

### Visual Changes
- **Signal Blocks:** Replace standard stat cards with "Tactical Modules" featuring 1px borders and corner accents.
- **Data Flow Lines:** Add subtle, animated gradient lines connecting the dashboard summary to the history list, simulating data transmission.
- **Matrix Background:** Apply a faint `pixel-dot` overlay to the entire page background.

### Interactions
- **Pulsing Tasks:** Active sync workers will have a breathing orange border.
- **Tactical Buttons:** All action buttons will use the `[ ACTION ]` bracketed text format with high-contrast hover states.

---

## Module 2: Video Feed (Backlight Focus)
**Goal:** Enhance content discovery with immersive micro-interactions and refined transitions.

### Visual Changes
- **Backlight Glow:** Hovering over a `VideoItem` triggers a soft orange radial glow behind the card (`box-shadow: 0 0 30px rgba(255, 77, 0, 0.15)`).
- **Minimalist Action Overlay:** A 20% height translucent bar at the bottom of thumbnails containing `[LIKE]`, `[LATER]`, and `[LINK]` text buttons.
- **Scanline Intensity:** Increase scanline opacity slightly on hover to emphasize the "active monitor" feel.

### Interactions
- **Glitch Transition:** Implement a 150ms "Signal Lock" jitter effect when navigating from the feed to the `VideoPlay` view.

---

## Module 3: Plugin Manager (Hardware Rack)
**Goal:** Re-imagine plugin management as a physical hardware rack.

### Visual Changes
- **Rack Units:** Replace the `<table>` with a vertical stack of "Rack Mount" cards. Each card features "Handle" decorations on the left and "Ventilation" dot patterns on the right.
- **LED Indicators:**
    - **Running:** Pulsing Green LED.
    - **Degraded/Warning:** Steady Yellow LED.
    - **Failed/Critical:** Rapidly Flashing Red LED.
    - **Disabled:** Dim Gray LED.
- **Tactical Typography:** All metadata (Plugin ID, Version, Runtime Endpoint) forced to `JetBrains Mono` with increased letter spacing.

---

## Success Criteria
- The entire application feels like a single, integrated "Tactical System."
- Information hierarchy is improved through high-contrast technical typography.
- Micro-interactions (glows, pulses, glitches) provide immediate, thematic feedback.
