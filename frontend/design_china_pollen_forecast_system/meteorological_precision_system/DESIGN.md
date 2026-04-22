---
name: Meteorological Precision System
colors:
  surface: '#121414'
  surface-dim: '#121414'
  surface-bright: '#383939'
  surface-container-lowest: '#0d0e0f'
  surface-container-low: '#1b1c1c'
  surface-container: '#1f2020'
  surface-container-high: '#292a2a'
  surface-container-highest: '#343535'
  on-surface: '#e3e2e2'
  on-surface-variant: '#c2c6d8'
  inverse-surface: '#e3e2e2'
  inverse-on-surface: '#2f3031'
  outline: '#8c90a1'
  outline-variant: '#424656'
  surface-tint: '#b3c5ff'
  primary: '#b3c5ff'
  on-primary: '#002b75'
  primary-container: '#0066ff'
  on-primary-container: '#f8f7ff'
  inverse-primary: '#0054d6'
  secondary: '#ddfcff'
  on-secondary: '#00363a'
  secondary-container: '#00f1fe'
  on-secondary-container: '#006a70'
  tertiary: '#50e167'
  on-tertiary: '#00390e'
  tertiary-container: '#00842c'
  on-tertiary-container: '#e5ffdf'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dae1ff'
  primary-fixed-dim: '#b3c5ff'
  on-primary-fixed: '#001849'
  on-primary-fixed-variant: '#003fa4'
  secondary-fixed: '#74f5ff'
  secondary-fixed-dim: '#00dbe7'
  on-secondary-fixed: '#002022'
  on-secondary-fixed-variant: '#004f54'
  tertiary-fixed: '#6fff80'
  tertiary-fixed-dim: '#50e167'
  on-tertiary-fixed: '#002106'
  on-tertiary-fixed-variant: '#005319'
  background: '#121414'
  on-background: '#e3e2e2'
  surface-variant: '#343535'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: '0'
  label-caps:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.1em
  data-mono:
    fontFamily: Space Grotesk
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin: 24px
---

## Brand & Style

The design system is engineered for high-stakes environmental monitoring, drawing direct inspiration from aerospace telemetry and scientific laboratory interfaces. The brand personality is authoritative, analytical, and hyper-precise. It prioritizes data integrity and rapid cognitive processing for specialists tracking pollen dispersal patterns across diverse geographical regions.

The visual style is a fusion of **Modern Corporate** and **Technical Minimalism**. It utilizes a "Dark Mode First" philosophy to reduce eye strain during prolonged monitoring sessions and to allow vibrant status indicators to pop against the void-like background. Visual interest is achieved through technical line art—such as latitude/longitude grids and topographic contours—rather than decorative imagery. The emotional response is one of absolute reliability and scientific rigor.

## Colors

The palette is anchored in a spectrum of deep oceanics. **Midnight Blue** serves as the primary canvas, providing a high-contrast base for the **Science Blue** primary actions. **Glow Cyan** is reserved for active states, data highlights, and "on" signals, mimicking the luminosity of cockpit instrumentation.

Functional colors are critical for meteorological safety: **Success Green** indicates low pollen counts and safe air quality, while **Alert Red** signifies critical allergen thresholds. **Neutral Grey** is utilized for secondary metadata and inactive UI elements. All interactive elements should maintain a high contrast ratio against the **Deep Navy** surfaces to ensure accessibility in low-light environments.

## Typography

This design system utilizes **Inter** as the primary typeface for its exceptional legibility in data-dense layouts. Its neutral character allows the complex meteorological data to remain the focal point. To enhance the "high-tech" scientific feel, **Space Grotesk** is introduced for labels and tabular data, offering a more geometric, technical aesthetic that aids in distinguishing between descriptive text and live telemetry.

Standardized typographic scales ensure hierarchy in dashboard views. Headlines use tighter tracking for a compact look, while labels utilize uppercase styling and increased letter spacing to define small-scale boundaries without requiring heavy dividers.

## Layout & Spacing

The layout utilizes a **12-column fluid grid system** designed for maximum information density. In this design system, white space is treated as a functional separator rather than an aesthetic luxury. A 4px baseline rhythm governs all vertical and horizontal spacing, ensuring mathematical consistency.

Dashboard layouts prioritize "above the fold" visibility, using card-based modules that can span 3, 4, 6, or 12 columns. Gutters are kept narrow (16px) to maximize the real estate available for maps and time-series charts. Margins are fixed at 24px on the desktop to frame the content within the viewport rigorously.

## Elevation & Depth

Depth is conveyed through **Tonal Layering** and **Subtle Outlines** rather than traditional shadows. The base layer is the darkest (Midnight Blue), with interactive cards and panels sitting on a slightly lighter surface (Deep Navy).

To simulate the look of illuminated glass, elements use 1px borders in Science Blue at low opacity (15-20%). Active or critical states utilize a **Subtle Glow** effect—a soft outer bloom using the Glow Cyan color with a 10px-15px blur—to simulate an emissive hardware display. Background blurs (10px) are applied to floating modals or dropdowns to maintain context without sacrificing legibility.

## Shapes

The design system adopts a **Soft-Square** geometry. A universal corner radius of 4px to 8px is applied to all primary containers, buttons, and input fields. This slight rounding softens the technical edge just enough to improve user comfort while maintaining a professional, engineered appearance.

Buttons use the 4px radius for a sharper, more precise look, while larger dashboard cards use the 8px radius to clearly define the boundaries of data clusters. Decorative elements, such as data point markers on maps, may use circular shapes to distinguish them from structural UI components.

## Components

- **Buttons:** High-density with 8px vertical padding. Primary buttons feature a solid Science Blue fill. Ghost buttons use the 1px Science Blue border. All hover states trigger a subtle Glow Cyan border-light.
- **Data Cards:** Defined by a 1px border (#ffffff10). Headers in cards use a subtle background tint and the `label-caps` typography style.
- **Chips/Status Badges:** Compact, pill-shaped markers for pollen levels. They use the Success, Alert, or Neutral colors with a 10% opacity background fill and a 100% opacity text color for maximum legibility.
- **Input Fields:** Flat, Deep Navy backgrounds with 1px Neutral Grey borders. Upon focus, the border transitions to Glow Cyan with a soft outer glow.
- **Icons:** Professional-grade, thin-stroke (1.5px) weather icons. Icons should be monochrome except when indicating active weather warnings.
- **Charts & Graphs:** Use technical line art. Grid lines in charts should be Science Blue at 5% opacity. Data lines utilize Glow Cyan for primary metrics and Neutral Grey for historical baselines.
- **Progress Indicators:** Linear bars with a Glow Cyan "pulse" animation to indicate real-time data streaming or background processing.