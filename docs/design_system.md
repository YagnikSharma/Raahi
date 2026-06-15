# Raahi Safety Platform - Design System Specification

Welcome to the **Raahi Design System** documentation. This document specifies the visual identity, typography system, HSL color space parameters, component blueprints, and micro-interaction specifications that govern the Raahi user experience.

---

## 🎨 Color Palette & Theme tokens

Raahi uses a refined, HSL-tailored color architecture that balances safety classification indicators with obsidian-glass aesthetics. All colors transition smoothly over `0.5s` using a `cubic-bezier(0.4, 0, 0.2, 1)` easing curve.

### HSL Color Parameters

| Token Name | Dark Obsidian (Default) | Light Slate Mode | Description |
| :--- | :--- | :--- | :--- |
| `--bg-main` | `#07080b` | `#f8fafc` | Global viewport body background |
| `--bg-card` | `rgba(15, 17, 23, 0.7)` | `rgba(255, 255, 255, 0.85)` | Glassmorphic panel base |
| `--bg-navbar` | `rgba(10, 11, 15, 0.85)` | `rgba(255, 255, 255, 0.9)` | Sticky navigation header backdrop |
| `--primary` | `#4f46e5` (Indigo-600) | `#4f46e5` (Indigo-600) | Main brand identity |
| `--accent` | `#06b6d4` (Cyan-500) | `#0284c7` (Sky-600) | Highlight states, secondary branding |
| `--text-main` | `#f3f4f6` (Gray-100) | `#0f172a` (Slate-900) | Core readable text |
| `--text-muted` | `#9ca3af` (Gray-400) | `#475569` (Slate-600) | Subheadings, caption texts |
| `--border-light`| `rgba(255, 255, 255, 0.08)`| `rgba(0, 0, 0, 0.08)` | Standard panel borders |
| `--border-hover`| `rgba(255, 255, 255, 0.16)`| `rgba(0, 0, 0, 0.16)` | Active hover borders |

### Safety Classification Gradients

The map indicators and routing pathways represent safety classifications using distinct severity palettes:

- 🟢 **Safe Zone (Level 0)**: `--safety-green` (`#10b981` / `#059669`) | Green glow aura
- 🟡 **Caution Zone (Level 1)**: `--safety-yellow` (`#f59e0b` / `#d97706`) | Yellow glow aura
- 🟠 **High Caution (Level 2)**: `--safety-orange` (`#f97316` / `#ea580c`) | Orange glow aura
- 🔴 **Danger Zone (Level 3)**: `--safety-red` (`#ef4444` / `#dc2626`) | Red glow aura

---

## 🔤 Typography Hierarchy

We use a modern dual-font layout from Google Fonts to maintain distinct readability for headings and paragraph contents.

- **Display Typeface**: `Outfit` — Used for headings (`h1` through `h6`), buttons, brand indicators, and card headers. Characterized by wide geometric tracking and a tight, modern kerning.
- **Sans-Serif Body Typeface**: `Plus Jakarta Sans` — Used for body copy, alerts, form fields, and map tooltips. Offers excellent reading legibility at small viewport scales.

### Typographic Scales

```
h1 / .display-4: font-size: 2.75rem | line-height: 1.2  | letter-spacing: -0.03em
h2:             font-size: 2.0rem   | line-height: 1.25 | letter-spacing: -0.02em
h3:             font-size: 1.5rem   | line-height: 1.3  | letter-spacing: -0.01em
Body Text:       font-size: 1.0rem   | line-height: 1.6  | letter-spacing: 0
Small Label:     font-size: 0.85rem  | line-height: 1.5  | letter-spacing: 0.02em
```

---

## ✨ Glassmorphism & Depth System

To create a natural and premium user experience, UI widgets behave like glass layers floating above ambient background lighting.

### Glass Panel Specifications
```css
.glass-panel {
  background: var(--bg-card);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid var(--border-light);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
}
```

### Depth & Hover Interactions
When users interact with elements, they smoothly lift and glow:
1. **Scale Transition**: Cards scale up by `1.015` on hover.
2. **Border Glow**: Borders brighten from `--border-light` to `--border-hover`.
3. **Shadow Drop**: Shadow strength increases in intensity, reflecting depth.

---

## ♿ Accessibility Compliance (WCAG)

Raahi is engineered for inclusivity, meeting **WCAG 2.1 AA** requirements:

- **Contrast Ratios**: Body text maintains a minimum contrast ratio of `4.5:1` against the solid backgrounds in both dark and light modes.
- **Keyboard Navigation**: Standard focus outlines are styled with high-visibility offsets (`*:focus-visible`) to guide keyboard-only users.
- **Aria Attributes**: Icon-only inputs (like the theme toggler, modal closing buttons, and dashboard actions) carry descriptive `aria-label` tags.
