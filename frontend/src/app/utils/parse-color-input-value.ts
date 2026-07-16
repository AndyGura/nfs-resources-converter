// Parses the value returned by the <input type="color" alpha> element into a 0xRRGGBBAA integer.
// Depending on the browser/OS the value is either a hex string (#RRGGBB / #RRGGBBAA) or a CSS
// color() function (e.g. macOS returns "color(srgb 1 0.984314 0)" or "color(srgb 1 0 0 / 0.5)").
export const parseColorInputValue = (raw: string | null, existingAlpha: number = 0xff): number | null => {
  if (!raw) return null;
  const value = raw.trim();
  if (value.startsWith('#')) {
    const digits = value.substring(1);
    if (digits.length >= 8) {
      // 8-digit #RRGGBBAA value (alpha attribute supported)
      return parseInt(digits.substring(0, 8), 16) >>> 0;
    }
    // 6-digit #RRGGBB value, keep the existing alpha
    return (((parseInt(digits || '0', 16) & 0xffffff) << 8) | existingAlpha) >>> 0;
  }
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
  const match = value.match(/color\(\s*srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\s*\)/i);
  if (match) {
    const r = clamp(parseFloat(match[1]) * 255);
    const g = clamp(parseFloat(match[2]) * 255);
    const b = clamp(parseFloat(match[3]) * 255);
    const a = match[4] !== undefined ? clamp(parseFloat(match[4]) * 255) : existingAlpha;
    return ((r << 24) | (g << 16) | (b << 8) | a) >>> 0;
  }
  return null;
};
