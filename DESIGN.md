---
name: Flying Pig
description: A supervised customer-service cockpit for delegating live support chats.
colors:
  warm-paper: "oklch(96.5% 0.014 78)"
  warm-paper-low: "oklch(93.5% 0.018 82)"
  surface: "oklch(98.5% 0.009 82)"
  surface-raised: "oklch(94.5% 0.014 82)"
  surface-pressed: "oklch(90.5% 0.019 78)"
  ink: "oklch(25% 0.034 74)"
  text: "oklch(31% 0.03 74)"
  muted: "oklch(50% 0.026 82)"
  subtle: "oklch(64% 0.026 82)"
  border: "oklch(84% 0.024 82)"
  border-strong: "oklch(72% 0.034 82)"
  action-green: "oklch(52% 0.13 157)"
  action-green-strong: "oklch(42% 0.12 157)"
  action-green-soft: "oklch(92% 0.05 157)"
  work-blue: "oklch(53% 0.11 246)"
  work-blue-soft: "oklch(92% 0.045 246)"
  danger-red: "oklch(55% 0.16 28)"
  danger-red-soft: "oklch(93% 0.05 28)"
  patience-amber: "oklch(64% 0.12 76)"
  patience-amber-soft: "oklch(93% 0.06 76)"
  field: "oklch(99% 0.006 82)"
  field-disabled: "oklch(94% 0.012 82)"
  cockpit-ink: "oklch(24% 0.04 155)"
  cockpit-ink-alt: "oklch(29% 0.035 204)"
  cockpit-text: "oklch(96% 0.018 122)"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "32px"
    fontWeight: 780
    lineHeight: 1.12
    letterSpacing: "0"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "24px"
    fontWeight: 780
    lineHeight: 1.08
    letterSpacing: "0"
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 760
    lineHeight: 1.25
    letterSpacing: "0"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0"
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "11px"
    fontWeight: 780
    lineHeight: 1.2
    letterSpacing: "0"
rounded:
  field: "7px"
  panel: "8px"
  icon: "12px"
  app-icon: "16px"
  pill: "999px"
spacing:
  xs: "5px"
  sm: "8px"
  md: "10px"
  lg: "14px"
  xl: "16px"
  page-x: "24px"
  page-y: "20px"
components:
  button-primary:
    backgroundColor: "{colors.action-green}"
    textColor: "{colors.cockpit-text}"
    rounded: "{rounded.field}"
    padding: "9px 14px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.action-green-strong}"
    textColor: "{colors.cockpit-text}"
    rounded: "{rounded.field}"
    padding: "9px 14px"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "9px 14px"
    height: "40px"
  button-danger:
    backgroundColor: "{colors.danger-red-soft}"
    textColor: "{colors.danger-red}"
    rounded: "{rounded.field}"
    padding: "9px 14px"
    height: "40px"
  input-field:
    backgroundColor: "{colors.field}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "10px 11px"
    height: "40px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "16px"
  status-pill-ready:
    backgroundColor: "{colors.action-green-soft}"
    textColor: "{colors.action-green-strong}"
    rounded: "{rounded.pill}"
    padding: "5px 10px"
    height: "28px"
---

# Design System: Flying Pig

## 1. Overview

**Creative North Star: "The Calm Operations Desk"**

Flying Pig is a supervised product cockpit, not a marketing surface. The visual system should feel like a clean desk beside a live browser window: warm paper, precise controls, clear run state, and no visual drama competing with the customer-service conversation.

The default scene is a user watching the Flying Pig desktop app and a Controlled Chrome Window side by side during a live support chat. The interface is light because the user may be reading, approving, and typing for several minutes in normal room light. The warm neutral palette avoids generic blue-gray SaaS and keeps status color meaningful.

The system rejects raw localhost/debug aesthetics, decorative AI dashboards, glassmorphism, dark neon control rooms, and large button grids that make the user feel they are choosing a mode instead of editing the task brief. The app should look trustworthy to someone familiar with Linear, Stripe, Notion, and native macOS utility windows.

**Key Characteristics:**
- Warm operational surfaces with restrained state color.
- Dense but calm form layouts for repeated supervised work.
- One cockpit, one source of truth: the desktop dashboard owns user attention.
- Standard controls, predictable grids, and explicit disabled states.
- Motion only for state feedback, never decoration.

## 2. Colors

The palette is restrained: warm neutral paper carries the screen, action green is rare and functional, and blue, amber, and red are reserved for specific operational states.

### Primary
- **Action Green** (`action-green`): Primary actions, ready states, selected/success borders, and focus rings. Use it sparingly. Its value comes from being rare.
- **Action Green Strong** (`action-green-strong`): Hover and stronger text for green states. Never use it for decorative headings.
- **Action Green Soft** (`action-green-soft`): Ready chips and soft status backgrounds.

### Secondary
- **Work Blue** (`work-blue`): Permission boundaries, setup panels, questions, and helper/work-window information. It indicates the work surface or user attention, not decoration.
- **Patience Amber** (`patience-amber`): Waiting, HUCA, checkpoint, and caution states. Use it for moments where the user should slow down and choose.
- **Danger Red** (`danger-red`): Offline, blocked, destructive, or failed states. Keep it explicit and localized.

### Neutral
- **Warm Paper** (`warm-paper`): Main app background.
- **Warm Paper Low** (`warm-paper-low`): Page depth and lower background gradient stop.
- **Surface** (`surface`): Panels, cards, metrics, and stable containers.
- **Surface Raised** (`surface-raised`): Secondary buttons and alternate control surfaces.
- **Surface Pressed** (`surface-pressed`): Hover for secondary controls.
- **Ink** (`ink`): Headings, important values, and strong labels.
- **Text** (`text`): Body text.
- **Muted** (`muted`): Labels, helper copy, timestamps, inactive metadata.
- **Subtle** (`subtle`): Placeholder copy and low-priority readiness labels.
- **Border** (`border`): Standard panel and divider border.
- **Border Strong** (`border-strong`): Form-field and secondary-button borders.
- **Cockpit Ink** (`cockpit-ink`): Hero/status band start color.
- **Cockpit Ink Alt** (`cockpit-ink-alt`): Hero/status band end color.
- **Cockpit Text** (`cockpit-text`): Text on the dark hero/status band and primary green buttons.

### Named Rules

**The Scarcity Rule.** Green is for action, readiness, selection, and focus. If a screen starts to look green, the accent has failed.

**The State Means State Rule.** Blue means work context, amber means patience or checkpoint, red means blocked or destructive. Do not use semantic colors as decoration.

**The Warm Utility Rule.** Neutral surfaces stay warm and paper-like. Do not drift into slate, charcoal, or cold blue-gray control-room palettes.

## 3. Typography

**Display Font:** Inter with system UI fallbacks.
**Body Font:** Inter with system UI fallbacks.
**Label/Mono Font:** System mono only for diagnostics and endpoint-like values.

**Character:** Typography is native, compact, and utilitarian. It should feel like a serious desktop tool, not a launch page.

### Hierarchy
- **Display** (780, 32px, 1.12): Electron startup screen title only. Keep it out of dense dashboard panels.
- **Headline** (780, 24px, 1.08): Dashboard app title and top-level run status.
- **Title** (760, 16px, 1.25): Panel titles, section headings, and compact form headings.
- **Body** (400, 14px, 1.45): Form copy, run messages, explanations, and list bodies. Prose should stay under 75ch when it is not a data table or URL.
- **Metric** (760, 15px, 1.45): Compact status values in metrics and readiness summaries.
- **Label** (780, 11px, 1.2, uppercase): Form labels, eyebrows, metric labels, and readiness labels.
- **Diagnostic Mono** (400, 12px, inherited line-height): Localhost URLs, log paths, endpoints, and file paths only.

### Named Rules

**The Utility Type Rule.** Use one sans family for the product UI. Do not introduce display fonts, decorative type, or fluid type scales.

**The Label Discipline Rule.** Uppercase labels are for scaffolding and metadata only. Do not write body copy in uppercase.

## 4. Elevation

Flying Pig uses a hybrid of tonal layering, borders, and two soft shadows. Depth should help the user separate the cockpit, panels, and temporary attention states. It must not create a glossy or floating marketing feel.

### Shadow Vocabulary
- **Panel Soft** (`0 8px 24px oklch(26% 0.03 74 / 0.08)`): Default panel, card, app icon, and hover elevation.
- **Panel Strong** (`0 18px 48px oklch(26% 0.03 74 / 0.11)`): Hero/status band and Electron startup card.
- **Icon Soft** (`0 10px 24px oklch(26% 0.03 74 / 0.14)`): Large app icon on the Electron startup screen.

### Named Rules

**The Border First Rule.** Use borders and tonal surfaces before shadows. Shadows support hierarchy; they do not create drama.

**The No Glass Rule.** Blur, frosted glass, transparent panels, and decorative glow effects are prohibited.

## 5. Components

### Buttons
- **Shape:** Gently curved utility controls (7px radius).
- **Primary:** Action Green background with Cockpit Text, 40px minimum height, 9px vertical and 14px horizontal padding. Use for Start, Save, setup, and user-answer send actions.
- **Hover / Focus:** Hover darkens to Action Green Strong, lifts by 1px, and may use Panel Soft shadow. Focus uses a 3px Action Green ring at low alpha.
- **Secondary:** Surface Raised background, Ink text, Border Strong stroke. Use for reconnect, refresh, work-window launch, and non-destructive settings actions.
- **Danger:** Danger Red Soft background, Danger Red text, explicit border. Use only for cancel, clear key, and destructive actions.
- **HUCA / Patience:** Patience Amber Soft background, amber text, explicit border. Use for recovery or wait-sensitive actions.
- **Link Button:** Transparent background, Action Green Strong text, no box shadow. Use only for low-risk inline actions such as clearing the timeline.

### Chips
- **Status Pill:** Pill radius, 28px minimum height, 5px by 10px padding, 12px bold label. Ready chips use green soft fill and strong green text. Offline chips use red soft fill and red text.
- **Readiness Item:** 8px radius, Surface background, Border stroke, 10px by 11px padding. Ready state changes border and value color, not the whole card.

### Cards / Containers
- **Corner Style:** Panels and repeated items use 8px radius. Do not exceed this unless using app icons.
- **Background:** Surface for main panels, Surface Raised for model-setting subgroups and secondary controls.
- **Shadow Strategy:** Default panels use Panel Soft. Nested content should use borders and tonal fills, not nested card shadows.
- **Border:** Standard Border for panels, Border Strong for fields and action-like containers.
- **Internal Padding:** 16px for panels, 10px to 11px for compact readiness and list items, 32px for Electron startup card.

### Inputs / Fields
- **Style:** Field background, Border Strong stroke, 7px radius, Ink text, 40px minimum height, 10px by 11px padding.
- **Focus:** Action Green border and 3px low-alpha focus ring. Do not replace focus with color-only changes.
- **Disabled / Readonly:** Field Disabled background and Muted text.
- **Text Areas:** Same field style, 116px minimum height, vertical resize.
- **Diagnostics:** Use Diagnostic Mono only for setup diagnostics, URLs, log paths, and endpoint-like values.

### Navigation
- **Topbar:** Brand lockup on the left, status pills on the right, single bottom border, no sidebar.
- **Settings Access:** A compact Settings button reopens model configuration. Model setup collapses automatically after a valid provider is configured.
- **Advanced Controls:** Use native details/summary. Advanced settings stay inline and progressive, not modal.
- **Mobile Treatment:** At 920px the topbar and hero stack. At 620px readiness, metrics, and action groups collapse to one column.

### Configured Workflow
- **First-use onboarding:** Three sequential screens for Configure, Open website, and Start. Only one step is visible at a time. Step labels disappear after the first run starts.
- **Request:** One prompt, one editable request, one Start action.
- **Preparation:** Replace the request form with one instruction to log in and expose the support chat.
- **Running:** Show one current-status sentence. Raw activity is opt-in.
- **Decision:** Give the pending question or checkpoint the full content focus.
- **Result:** Lead with outcome, confirmation evidence, and required follow-up. Keep diagnostics secondary.

### Signature Component: Cockpit Status Band

The hero/status band is the only dark surface. It uses Cockpit Ink to Cockpit Ink Alt as a diagonal gradient, Cockpit Text for values, and a soft strong shadow. It announces the current run state and the next user-facing instruction. Do not add metrics or decorative stats inside it.

### Signature Component: Trust Boundary

The trust boundary is an inline permission summary inside the task panel. It uses top and bottom borders, blue emphasis for the permission mode, and small blue dot markers. It is not a callout card and must not use a colored side stripe.

## 6. Do's and Don'ts

### Do:
- **Do** keep the dashboard as the Single Cockpit: the Flying Pig control UI appears in the desktop app, while the Controlled Chrome Window is only the work area.
- **Do** make the editable problem brief the source of truth. Starters and automatic agent approach support the textarea; they do not replace it.
- **Do** expose Work Window Offline with an immediate Open Work Window action beside the status when the helper is online.
- **Do** use Action Green only for primary actions, ready states, selection, and focus.
- **Do** preserve explicit disabled, hover, focus, active, danger, warning, and loading states on every interactive control.
- **Do** use inline progressive disclosure for Advanced settings and model keys.
- **Do** make repeat use task-first: starter, editable problem brief, current status, and one primary Start action. Keep success criteria, authorization, browser selection, and diagnostics under Run options.
- **Do** replace the surface as workflow state changes instead of keeping setup, readiness, metrics, timing, and activity visible together.
- **Do** recover configuration failures by reopening setup with plain corrective language.
- **Do** keep user-attention moments, Decision Checkpoints, and irreversible actions visually distinct with amber or blue state treatment.
- **Do** verify mobile breakpoints for no horizontal overflow at 390px wide.

### Don't:
- **Don't** show a second Flying Pig control surface in the Controlled Chrome Window.
- **Don't** present `flyingpig-helper`, raw localhost URLs, old React frontend, Chrome extension, or CLI runs as equivalent user paths.
- **Don't** use large task-template button grids that imply the starter choice is final while the problem brief remains editable.
- **Don't** surface raw WebSocket or localhost failures as the main user experience; show setup, reconnect, and small diagnostics.
- **Don't** use side-stripe borders, gradient text, glassmorphism, decorative orbs, dark neon AI dashboards, or hero-metric templates.
- **Don't** use modals for ordinary setup, model settings, or task configuration. Exhaust inline and progressive alternatives first.
- **Don't** use semantic colors as decoration. Blue, amber, red, and green must carry state.
- **Don't** make one-off panels or buttons with unique shapes. Component vocabulary must stay consistent across dashboard and Electron startup screens.
