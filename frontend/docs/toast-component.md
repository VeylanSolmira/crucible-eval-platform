A toast component is a UI pattern for showing
temporary notifications that appear and disappear
automatically. Here's what makes them useful:

Key Characteristics:

1. Non-blocking - They don't interrupt the user's
   workflow (unlike modal dialogs)
2. Temporary - They auto-dismiss after a few seconds
3. Positioned - Usually appear in a corner
   (bottom-right is common)
4. Stackable - Multiple toasts can appear if needed

Common Use Cases:

- ✅ Success messages: "Settings saved successfully"
- ❌ Error notifications: "Failed to upload file"
- ℹ️ Info updates: "New version available"
- ⚠️ Warnings: "Your session will expire in 5
  minutes"

Our Implementation Features:

<Toast
message="Evaluation marked as failed"
type="success" // success | error | info
duration={3000} // auto-dismiss after 3 seconds
onClose={() => setToast(null)}
/>

Visual Design:

- Color-coded by type (green/red/blue)
- Icons for quick recognition
- Close button for manual dismissal
- Smooth animations (we could add these)

Alternatives in React:

1. React-Toastify - Popular library with many
   features
2. React Hot Toast - Lightweight and customizable
3. Headless UI - Unstyled, accessible components
4. Radix UI Toast - Highly accessible primitives

Benefits over browser alert():

- Doesn't block JavaScript execution
- Better visual design
- Can show multiple messages
- Preserves user context
- Mobile-friendly
- Accessibility features (ARIA)

Would you like me to enhance our toast component
with features like:

- Multiple toast stacking
- Animation transitions
- Progress bars for duration
- Action buttons (like "Undo")
- Different positions (top-left, center, etc.)
