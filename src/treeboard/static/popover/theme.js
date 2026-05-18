const STORAGE_KEY = "treeboard:theme";

export function getTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function setTheme(theme) {
  if (theme !== "light" && theme !== "dark") return;
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
}

export function initTheme() {
  setTheme(getTheme());
}

export function mountThemeToggle(parent) {
  const btn = document.createElement("button");
  btn.className = "theme-toggle";
  btn.type = "button";
  btn.setAttribute("aria-label", "Toggle theme");
  const render = () => {
    const t = getTheme();
    btn.textContent = t === "dark" ? "☾" : "☀";
    btn.title = `Switch to ${t === "dark" ? "light" : "dark"} mode`;
  };
  btn.addEventListener("click", () => {
    setTheme(getTheme() === "dark" ? "light" : "dark");
    render();
  });
  render();
  parent.appendChild(btn);
  return btn;
}
