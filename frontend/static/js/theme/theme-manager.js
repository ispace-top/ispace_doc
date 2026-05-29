/**
 * iSpaceDoc Theme Manager
 * Single source of truth for theme state.
 *
 * localStorage key: "ispace-theme"  (values: null | "light" | "dark" | "auto")
 * HTML attribute:  data-ispace-theme (values: "light" | "dark")
 * System detection: matchMedia('(prefers-color-scheme: dark)')
 */
const ThemeManager = (() => {
  const STORAGE_KEY = 'ispace-theme';
  const ATTR = 'data-ispace-theme';
  const DARK_MQ = window.matchMedia('(prefers-color-scheme: dark)');

  let currentTheme = 'light';

  function getStored() {
    return localStorage.getItem(STORAGE_KEY);
  }

  function setStored(value) {
    if (value === 'auto') {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, value);
    }
  }

  function resolveTheme(stored) {
    if (stored === 'light' || stored === 'dark') return stored;
    return DARK_MQ.matches ? 'dark' : 'light';
  }

  function apply(theme) {
    document.documentElement.setAttribute(ATTR, theme);
    currentTheme = theme;
    updateToggleIcon(theme);
    updateMetaThemeColor(theme);
    window.dispatchEvent(new CustomEvent('ispace:themechange', { detail: { theme } }));
  }

  function updateToggleIcon(theme) {
    const toggles = document.querySelectorAll('[data-ispace-theme-toggle]');
    toggles.forEach(toggle => {
      const sunIcon = toggle.querySelector('.ispace-icon-sun');
      const moonIcon = toggle.querySelector('.ispace-icon-moon');
      if (sunIcon) sunIcon.style.display = theme === 'dark' ? 'none' : '';
      if (moonIcon) moonIcon.style.display = theme === 'dark' ? '' : 'none';
    });
  }

  function updateMetaThemeColor(theme) {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.content = theme === 'dark' ? '#0f172a' : '#3b82f6';
    }
  }

  function init() {
    const stored = getStored();
    const theme = resolveTheme(stored);

    if (stored && stored !== document.documentElement.getAttribute(ATTR)) {
      apply(theme);
    } else {
      currentTheme = theme;
      updateToggleIcon(theme);
    }

    DARK_MQ.addEventListener('change', (e) => {
      if (!getStored()) {
        apply(e.matches ? 'dark' : 'light');
      }
    });
  }

  function toggle() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    apply(newTheme);
    setStored(newTheme);
  }

  function set(value) {
    setStored(value);
    apply(resolveTheme(value));
  }

  function get() {
    return currentTheme;
  }

  return { init, toggle, set, get };
})();

document.addEventListener('DOMContentLoaded', () => ThemeManager.init());

document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
    e.preventDefault();
    ThemeManager.toggle();
  }
});

window.ThemeManager = ThemeManager;
window.toggleTheme = () => ThemeManager.toggle();
