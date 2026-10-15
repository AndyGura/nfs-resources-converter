import { sortedPosition } from './font.block-ui.component';

describe('sortedPosition', () => {
  const glyphs = [{ code: 32 }, { code: 48 }, { code: 65 }, { code: 65 }, { code: 97 }];

  it('moves an item forward after the items with a smaller or equal key', () => {
    expect(sortedPosition(glyphs, 'code', 66, 1)).toBe(3);
    expect(sortedPosition(glyphs, 'code', 65, 0)).toBe(3);
  });

  it('moves an item back before the first item with a bigger key', () => {
    expect(sortedPosition(glyphs, 'code', 40, 4)).toBe(1);
    expect(sortedPosition(glyphs, 'code', 0, 2)).toBe(0);
  });

  it('keeps the index when the item stays in order', () => {
    expect(sortedPosition(glyphs, 'code', 50, 1)).toBe(1);
    expect(sortedPosition(glyphs, 'code', 200, 4)).toBe(4);
  });
});
