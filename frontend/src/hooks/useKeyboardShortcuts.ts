import { useEffect } from "react";

interface ShortcutHandlers {
  onFocusSearch: () => void;
  onEscape: () => void;
  onAddCard: () => void;
}

export function useKeyboardShortcuts({ onFocusSearch, onEscape, onAddCard }: ShortcutHandlers) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Skip if focus is inside an input/textarea/contenteditable
      const tag = (e.target as HTMLElement).tagName;
      const isEditing =
        tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement).isContentEditable;

      if (e.key === "Escape") {
        onEscape();
        return;
      }

      if (isEditing) return;

      if (e.key === "/" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        onFocusSearch();
      }

      if (e.key === "n" && !e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey) {
        e.preventDefault();
        onAddCard();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onFocusSearch, onEscape, onAddCard]);
}
