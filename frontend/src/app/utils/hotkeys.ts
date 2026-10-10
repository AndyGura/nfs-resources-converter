export type HotkeyAction = 'undo' | 'redo' | 'save' | 'open' | 'new';

export const IS_MAC = /Mac|iPhone|iPad/.test(globalThis.navigator?.platform || globalThis.navigator?.userAgent || '');

// the key as a latin letter: with a non-latin keyboard layout e.key is the layout's letter, then the physical key is used
function keyLetter(e: KeyboardEvent): string {
  if (/^[a-z]$/i.test(e.key)) return e.key.toLowerCase();
  return /^Key[A-Z]$/.test(e.code) ? e.code.substring(3).toLowerCase() : '';
}

// app-level shortcut of a keydown event: Ctrl+<key> (⌘+<key> on macOS)
export function hotkeyAction(e: KeyboardEvent, isMac: boolean = IS_MAC): HotkeyAction | null {
  const primary = isMac ? e.metaKey && !e.ctrlKey : e.ctrlKey && !e.metaKey;
  if (!primary || e.altKey) return null;
  const key = keyLetter(e);
  if (key === 'z') return e.shiftKey ? 'redo' : 'undo';
  if (e.shiftKey) return null;
  if (key === 'y' && !isMac) return 'redo';
  if (key === 's') return 'save';
  if (key === 'o') return 'open';
  if (key === 'n') return 'new';
  return null;
}

export function hotkeyLabels(isMac: boolean = IS_MAC): Record<HotkeyAction, string> {
  return isMac
    ? { undo: '⌘Z', redo: '⇧⌘Z', save: '⌘S', open: '⌘O', new: '⌘N' }
    : { undo: 'Ctrl+Z', redo: 'Ctrl+Y', save: 'Ctrl+S', open: 'Ctrl+O', new: 'Ctrl+N' };
}

// a focused text field keeps its own undo / redo of the text being typed: its value is not a change until it is
// committed (blur / Enter)
export function isTextField(el: Element | null): boolean {
  if (!el) return false;
  if ((el as HTMLElement).isContentEditable || el.tagName === 'TEXTAREA') return true;
  if (el.tagName !== 'INPUT') return false;
  return !['checkbox', 'radio', 'range', 'button', 'submit', 'reset', 'color', 'file'].includes(
    (el as HTMLInputElement).type,
  );
}
