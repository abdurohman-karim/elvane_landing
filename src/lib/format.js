// Numbers as the app writes them (Packages/Core): 3 309 м, −6°, 8,1 км.
const NNBSP = ' ';

export function num(value) {
  return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, NNBSP);
}

export function deg(value) {
  const r = Math.round(value);
  return (r < 0 ? '−' + Math.abs(r) : r > 0 ? '+' + r : '0') + '°';
}

export function dec(value, lang, digits = 1) {
  const s = value.toFixed(digits);
  return lang === 'ru' ? s.replace('.', ',') : s;
}

export function clamp(v, a = 0, b = 1) {
  return Math.min(b, Math.max(a, v));
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

/** Colour = height: the palette as a hypsometric scale (Palette.altitudeBand). */
export function band(metres) {
  if (metres < 1500) return '#1FBFB8';
  if (metres < 3000) return '#05716C';
  if (metres < 4500) return '#1978A5';
  return '#031163';
}
