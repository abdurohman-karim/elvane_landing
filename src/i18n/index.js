// Two languages, like the app: Russian for ru and the languages of the CIS, English for everyone else.
// The language is fixed for a page load — switching reloads, so no animation has to re-measure its text.
import en from './en.js';
import ru from './ru.js';

const CIS = ['ru', 'uz', 'kk', 'ky', 'tg', 'be', 'uk', 'hy', 'az', 'tk'];
const messages = { ru, en };

function pick() {
  const param = new URLSearchParams(location.search).get('lang');
  if (param === 'ru' || param === 'en') return param;
  try {
    const saved = localStorage.getItem('elvane.lang');
    if (saved === 'ru' || saved === 'en') return saved;
  } catch {
    // private mode: fall through to the browser's language
  }
  return CIS.includes((navigator.language || 'ru').slice(0, 2).toLowerCase()) ? 'ru' : 'en';
}

export const lang = pick();
export const other = lang === 'ru' ? 'en' : 'ru';

/** A string (with {placeholders}) or, for lists and groups, the value as it is. */
export function t(key, vars) {
  let value = messages[lang][key] ?? key;
  if (vars && typeof value === 'string') for (const name in vars) value = value.replace(`{${name}}`, vars[name]);
  return value;
}

export function applyDocumentLanguage() {
  document.documentElement.lang = lang;
  document.title = t('meta.title');
  document.querySelector('meta[name="description"]')?.setAttribute('content', t('meta.description'));
}

export function switchLanguage() {
  try {
    localStorage.setItem('elvane.lang', other);
  } catch {
    // nothing to remember it in: the address carries it instead
  }
  const url = new URL(location.href);
  url.searchParams.set('lang', other);
  url.hash = '';
  location.replace(url);
}
