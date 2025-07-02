# Frontend UX Principles

## Context-Aware Controls

### Core Principle

**Controls should be context-aware and their state should clearly reflect what's possible in the current context.**

The UI should never present actions that can't be performed. This prevents user confusion and makes the interface predictable and learnable.

## Case Study: Kill Button for Running Evaluations

### The Problem

Initial implementation showed a kill button on every running evaluation in a list. This caused:

- Visual clutter with multiple kill buttons
- UI flashing when evaluations completed quickly
- Confusing user experience with buttons appearing/disappearing

### The Solution

Moved to a selection-based model with a single control panel:

```typescript
// Bad: Kill button on every item
<EvaluationItem>
  <Info />
  <KillButton /> {/* Cluttered, flashes on/off */}
</EvaluationItem>

// Good: Single control panel for selected item
<EvaluationsList onSelect={setSelected} />
<ControlPanel selectedId={selected} /> {/* Clean, stable */}
```

### Implementation Patterns

#### 1. Selection-Based Controls

Controls only appear when relevant:

```typescript
{selectedEvalId && (
  <ControlPanel>
    <KillButton disabled={!isRunning} />
  </ControlPanel>
)}
```

#### 2. State-Aware Styling

Visual feedback matches available actions:

```typescript
className={
  isRunning && !isPending
    ? 'bg-red-500 hover:bg-red-600'  // Active
    : 'bg-gray-300 cursor-not-allowed' // Disabled
}
```

#### 3. Clear Disable Reasons

Tooltips explain why actions are unavailable:

```typescript
title={
  selectedEvaluation
    ? 'Kill this evaluation'
    : 'Evaluation no longer running'
}
```

## Scaling Across UI Layouts

### Embedded Controls (Current)

```typescript
<RunningEvaluations>
  <List />
  <ControlPanel /> {/* Appears inline when selected */}
</RunningEvaluations>
```

### Tabbed Interface

```typescript
<Tabs>
  <Tab label="Running">
    {/* Kill button context */}
  </Tab>
  <Tab label="History">
    {/* No kill button - different context */}
  </Tab>
</Tabs>
```

### Persistent Control Panel

```typescript
<Layout>
  <MainContent />
  <Sidebar>
    <ControlPanel
      disabled={!hasValidSelection}
    />
  </Sidebar>
</Layout>
```

## Best Practices

### 1. Disable vs Hide

- **Disable** when the action exists but isn't currently available
- **Hide** when the action doesn't make sense in the current context
- Always prefer disable with explanation over mysterious hiding

### 2. Loading States

Replace enabled controls with loading indicators during operations:

```typescript
{
  isPending ? 'Killing...' : 'Kill Evaluation'
}
```

### 3. Post-Action Behavior

Clear or update selection after destructive actions:

```typescript
await killMutation.mutateAsync(evalId)
onSelectEvaluation(null) // Clear selection
```

### 4. Polling and State Sync

Ensure controls update automatically as state changes:

```typescript
// Control becomes disabled when evaluation completes
// even if user doesn't click away
const isStillRunning = runningEvals.find(e => e.id === selected)
```

## Anti-Patterns to Avoid

### 1. Action Buttons Everywhere

❌ Don't add action buttons to every list item
✅ Use selection + dedicated control area

### 2. Flashing UI Elements

❌ Don't show/hide elements rapidly with polling
✅ Use stable layouts with disabled states

### 3. Actions Without Context

❌ Don't enable buttons without clear selection
✅ Always show what the action will affect

### 4. Hidden State Changes

❌ Don't change what buttons do based on hidden state
✅ Make state visible through selection highlighting

## Testing Checklist

When implementing context-aware controls:

- [ ] Control appears only when relevant
- [ ] Disabled state is visually distinct
- [ ] Tooltips explain disabled reasons
- [ ] Selection state is clearly visible
- [ ] Actions affect only selected items
- [ ] Loading states replace enabled states
- [ ] Post-action behavior is predictable
- [ ] Works with keyboard navigation
- [ ] Mobile touch targets are adequate
- [ ] Screen readers announce state changes

## Related Documentation

- [Component Guidelines](./component-guidelines.md)
- [Accessibility Standards](./accessibility.md)
- [React Query Patterns](./react-query-patterns.md)
