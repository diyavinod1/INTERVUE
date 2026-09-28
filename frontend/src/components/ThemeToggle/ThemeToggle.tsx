import { useTheme } from "../../hooks/useTheme";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border-light dark:border-border-dark text-sm text-ink-muted dark:text-paper/60 hover:text-ink dark:hover:text-paper transition-colors"
    >
      {theme === "dark" ? "☼" : "☾"}
    </button>
  );
}
