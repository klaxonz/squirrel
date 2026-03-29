# Settings UI Redesign V2 - The Precision Console Design Document

**Date:** 2026-03-29
**Status:** Approved
**Theme:** Minimalist, Typography-driven, Non-card layout.

## 1. Vision & Core Principles
The "Precision Console" design moves away from standard card-based UI containers. It emphasizes pure typography, negative space, and kinetic feedback through ultra-thin lines. The interface should feel like a high-end creative tool (e.g., Linear, Raycast) rather than a generic web app.

- **No Cards:** Absolute removal of background containers or "blocks".
- **Precision Lines:** Use of 1px borders as the primary structural element.
- **Kinetic Feedback:** Micro-interactions that respond to mouse movement with high precision.
- **Staggered Motion:** Content reveals in an ordered, rhythmic sequence.

## 2. Visual Specification

### 2.1 Sidebar (Navigation)
- **Layout:** Clean vertical list of text labels.
- **Typography:** `text-[13px] font-bold tracking-tight`.
- **Active State:** Text transitions to `primary` (orange). A 1px vertical line appears on the left, growing from `scaleY(0)` to `scaleY(1)`.
- **Hover State:** Text color shifts slightly towards white/black (depending on theme). No background highlight.

### 2.2 Main Content (Settings)
- **Header:** Large, bold typography (`text-4xl font-black`). Followed by a full-width ultra-thin horizontal line (`border-border/10`).
- **Setting Rows:**
    - **Separation:** Separated by 1px horizontal lines (`border-border/5`).
    - **Layout:** `Label + Description` on the left, `Control` (Switch/Select) on the right.
    - **Spacing:** Generous vertical padding (`py-10`) to create "air" without containers.
- **Site Config Section:**
    - **Grid:** A clean, non-card grid where each site is separated by thin vertical/horizontal lines (like a drafting table).
    - **Icons:** Minimalist site icons with subtle 1px borders.

## 3. Interaction & Animation

### 3.1 Kinetic Feedback (Hover)
- **Line Growth:** When hovering a setting row, the 1px line above and below "grows" from the center (`scaleX` transition) and brightens to `primary/30`.
- **Text Shift:** The title of the hovered item shifts `4px` to the right with a smooth `cubic-bezier` transition.

### 3.2 Motion System
- **Staggered Reveal:** On tab switch, items enter one by one with a `40ms` delay per row.
- **Shutter Effect:** A subtle 3D reveal effect (`rotateX(5deg)` to `0deg`) and `translateY(10px)` to `0px`.
- **Timing:** Use `cubic-bezier(0.16, 1, 0.3, 1)` for all transitions to ensure a "snappy yet smooth" feel.

## 4. Implementation Strategy
- **Vue TransitionGroup:** Use for the staggered list animations.
- **Tailwind Groups:** Extensive use of `group-hover` for synchronized line and text animations.
- **CSS Variables:** Drive the dynamic line scaling and opacity.
