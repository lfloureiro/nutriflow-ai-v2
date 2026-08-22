# Compact visual polish

The v2 interface should remain operationally light: more focused screens are preferred to dense screens containing many unrelated controls.

The shared visual layer in `apps/web/src/visual-polish.css` applies the same presentation rules without changing screen behavior.

## Rules

- normal inputs and selects stay compact instead of becoming large horizontal blocks;
- checkbox and radio controls have their own small dimensions and are never affected by full-width text-input rules;
- secondary navigation uses pill-style controls;
- people selection uses compact selectable chips/cards;
- recommendation source choices keep enough room for their explanatory text but use softer rounded cards and reduced vertical height;
- panels, catalogue rows, meal-plan rows, pantry rows and shopping rows share a consistent radius vocabulary;
- excessive vertical padding is reduced while keeping touch targets usable;
- empty states and nested rows use softer surfaces so the screen does not look like a stack of hard rectangles;
- responsive layouts continue to stack on small screens.

The visual layer is imported last from `main.tsx` so it can normalize existing screens without duplicating product logic or requiring component-specific visual forks.
