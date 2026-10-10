import { hotkeyAction, isTextField } from './hotkeys';

function key(init: KeyboardEventInit): KeyboardEvent {
  return new KeyboardEvent('keydown', init);
}

describe('hotkeyAction', () => {
  it('maps Ctrl shortcuts off macOS', () => {
    expect(hotkeyAction(key({ key: 'z', code: 'KeyZ', ctrlKey: true }), false)).toBe('undo');
    expect(hotkeyAction(key({ key: 'Z', code: 'KeyZ', ctrlKey: true, shiftKey: true }), false)).toBe('redo');
    expect(hotkeyAction(key({ key: 'y', code: 'KeyY', ctrlKey: true }), false)).toBe('redo');
    expect(hotkeyAction(key({ key: 's', code: 'KeyS', ctrlKey: true }), false)).toBe('save');
    expect(hotkeyAction(key({ key: 'o', code: 'KeyO', ctrlKey: true }), false)).toBe('open');
    expect(hotkeyAction(key({ key: 'n', code: 'KeyN', ctrlKey: true }), false)).toBe('new');
  });

  it('maps ⌘ shortcuts on macOS', () => {
    expect(hotkeyAction(key({ key: 'z', code: 'KeyZ', metaKey: true }), true)).toBe('undo');
    expect(hotkeyAction(key({ key: 'z', code: 'KeyZ', metaKey: true, shiftKey: true }), true)).toBe('redo');
    expect(hotkeyAction(key({ key: 's', code: 'KeyS', metaKey: true }), true)).toBe('save');
    expect(hotkeyAction(key({ key: 'y', code: 'KeyY', metaKey: true }), true)).toBeNull();
    expect(hotkeyAction(key({ key: 'z', code: 'KeyZ', ctrlKey: true }), true)).toBeNull();
  });

  it('ignores other modifiers and keys', () => {
    expect(hotkeyAction(key({ key: 'z', code: 'KeyZ' }), false)).toBeNull();
    expect(hotkeyAction(key({ key: 'z', code: 'KeyZ', metaKey: true }), false)).toBeNull();
    expect(hotkeyAction(key({ key: 'z', code: 'KeyZ', ctrlKey: true, altKey: true }), false)).toBeNull();
    expect(hotkeyAction(key({ key: 'S', code: 'KeyS', ctrlKey: true, shiftKey: true }), false)).toBeNull();
    expect(hotkeyAction(key({ key: 'c', code: 'KeyC', ctrlKey: true }), false)).toBeNull();
  });

  it('uses the physical key with a non-latin layout', () => {
    expect(hotkeyAction(key({ key: 'я', code: 'KeyZ', ctrlKey: true }), false)).toBe('undo');
    expect(hotkeyAction(key({ key: 'ы', code: 'KeyS', metaKey: true }), true)).toBe('save');
  });
});

describe('isTextField', () => {
  it('tells text fields from other controls', () => {
    const input = document.createElement('input');
    expect(isTextField(input)).toBeTrue();
    input.type = 'number';
    expect(isTextField(input)).toBeTrue();
    input.type = 'checkbox';
    expect(isTextField(input)).toBeFalse();
    expect(isTextField(document.createElement('textarea'))).toBeTrue();
    expect(isTextField(document.createElement('button'))).toBeFalse();
    expect(isTextField(null)).toBeFalse();
  });
});
