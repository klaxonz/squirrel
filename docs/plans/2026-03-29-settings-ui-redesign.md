# Design Document: Settings Page UI/UX Redesign

## Overview
Redesign the settings page to match the project's "pro" and "minimalist" aesthetic, focusing on clarity, ease of use, and visual refinement.

## Aesthetic Direction: Refined Minimalist
- **Tone**: Clean, professional, and efficient.
- **Color Palette**: 
    - Background: `#050505` (Project standard)
    - Primary: `24 100% 50%` (Bright orange)
    - Borders: Subtle `border-border/10` or `border-muted/20`.
- **Typography**: 
    - Sans-serif (`IBM Plex Sans` and `Noto Sans SC`).
    - High-quality font weights and sizes for clear hierarchy.
- **Layout**: 
    - Sidebar navigation with active state indicators.
    - Grouped settings into logical sections with subtle separators.

## Proposed Changes

### 1. Sidebar Navigation
- **Active State**: A vertical primary-colored bar on the left and primary-colored text/icon.
- **Hover State**: Very subtle background highlight (`bg-muted/5`).
- **Icons**: Consistent use of `lucide-vue-next` icons.

### 2. Main Content Area
- **Header**: Use a more prominent title with a secondary description.
- **Sections**: Group settings into blocks with a subtle background (`bg-muted/2`) and border.
- **Setting Items**:
    - Left-aligned label (bold) and description (muted).
    - Right-aligned controls (Switch, Select, etc.).
    - Subtle hover effect for the entire row.

### 3. Appearance Tab
- **Theme Selection**: Redesigned cards with better icons and a clear active state.
- **Spacing**: Improved grid layout for theme options.

### 4. Site Config Section
- **Site Cards**: More compact, cleaner layout.
- **Status Indicators**: Refined dots with subtle glows for enabled sites.
- **Grid**: Improved responsiveness for the site grid.

## Motion & Interaction
- **Tab Transitions**: Smooth "slide-up" animation for content sections.
- **Hover Effects**: Subtle transitions for all interactive elements.
- **Optimistic UI**: Immediate feedback for toggle changes.

## Success Criteria
- The settings page feels more "pro" and integrated with the rest of the application.
- Settings are easier to scan and understand.
- Interactions feel fast and responsive.
