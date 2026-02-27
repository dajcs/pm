# Frontend: Kanban Studio

Next.js 16 single-page Kanban board demo. Pure client-side state (no backend yet).

## Stack

- Next.js 16.1.6, React 19.2.3, TypeScript 5
- Tailwind CSS v4 via `@tailwindcss/postcss`
- `@dnd-kit` for drag-and-drop (core 6.3.1, sortable 10.0.0, utilities 3.2.2)
- `clsx` for conditional class names
- Fonts: Space Grotesk (headings, `.font-display`) + Manrope (body) via `next/font/google`

## Data Model (lib/kanban.ts)

```
Card    = { id: string, title: string, details: string }
Column  = { id: string, title: string, cardIds: string[] }
BoardData = { columns: Column[], cards: Record<string, Card> }
```

Cards stored in a flat map. Columns reference cards by ID. Initial data has 5 columns (Backlog, Discovery, In Progress, Review, Done) with 8 sample cards.

Helper functions: `moveCard(columns, activeId, overId)` for drag reorder/cross-column moves, `createId(prefix)` for ID generation.

## Component Tree

```
RootLayout (layout.tsx)
  Home (page.tsx)
    KanbanBoard          -- owns all state via useState<BoardData>
      KanbanColumn (x5)  -- useDroppable, editable title input, card count badge
        KanbanCard (xN)  -- useSortable, shows title/details, Remove button
        NewCardForm      -- toggleable form: title (required) + details (optional)
      DragOverlay
        KanbanCardPreview -- stateless card clone shown while dragging
```

## State Management

Single `useState<BoardData>` in `KanbanBoard`. All mutations (rename column, add/delete card, drag-and-drop) call `setBoard` with immutable updates. No Context, no external state library.

## Styling

Tailwind utility classes in JSX. CSS custom properties in globals.css:
- `--accent-yellow: #ecad0a`
- `--primary-blue: #209dd7`
- `--secondary-purple: #753991`
- `--navy-dark: #032147`
- `--gray-text: #888888`
- `--surface: #f7f8fb`
- `--stroke: rgba(3,33,71,0.08)`

Decorative radial gradients (blue top-left, purple bottom-right) as background accents.

## Tests

**Unit (Vitest + jsdom + Testing Library):**
- `lib/kanban.test.ts` -- moveCard logic (same-column reorder, cross-column move, drop on column)
- `components/KanbanBoard.test.tsx` -- renders 5 columns, rename column, add + delete card

**E2E (Playwright):**
- `tests/kanban.spec.ts` -- board loads with heading + 5 columns, add card via form, drag card between columns

## Scripts

- `dev` / `build` / `start` -- standard Next.js
- `test` / `test:unit` -- vitest run
- `test:e2e` -- playwright test
- `test:all` -- unit then e2e
