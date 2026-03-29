# Design: Neon Pulse Sidebar Optimization (2026-03-29)

## Overview
Optimize the sidebar UI and UX with a "Neon Pulse" aesthetic, enhancing the current cyberpunk-inspired look with more depth, better typography, and refined micro-interactions.

## Visual Design & Typography
- **Background:** Deep charcoal (`#050505`) with a subtle glassmorphism effect on the border.
- **Icons:** Integrate `Heroicons` (from `@heroicons/vue/24/outline`) into each menu item. Active icons will have a soft neon glow (`drop-shadow`).
- **Typography:** Refine the menu label with `letter-spacing: 0.15em` and a slightly bolder weight for better readability.
- **Group Headers:** Add subtle text headers (e.g., "CONTENT", "OPERATIONS", "SYSTEM") to separate navigation sections visually.

## Interactions & Animations
- **Hover State:** A "slide-in" background highlight (`rgba(255, 255, 255, 0.03)`) and the icon shifting slightly to the right.
- **Active Indicator:** The "active line" will transform into a vertical pill shape with a `box-shadow` glow. It will use a `cubic-bezier(0.19, 1, 0.22, 1)` transition for an "elastic" feel.
- **Pulse Effect:** The active icon will have a very subtle, slow breathing animation (opacity 0.8 to 1.0).

## Component Changes
### `Sidebar.vue`
- Update layout to include section headers.
- Refine spacing between groups.

### `SidebarMenuItem.vue`
- Add icon support (passing from `NAV_ITEMS`).
- Implement the "Neon Pulse" effect in CSS.
- Add hover/active transitions.

## Success Criteria
- The sidebar feels more "premium" and interactive.
- Navigation sections are clearly demarcated.
- Active items are instantly recognizable through both the indicator and the icon glow.
