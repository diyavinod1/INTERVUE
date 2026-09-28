import { Link } from "react-router-dom";
import { ThemeToggle } from "../ThemeToggle/ThemeToggle";

export function NavBar({ minimal = false }: { minimal?: boolean }) {
  return (
    <header className="sticky top-0 z-30 border-b border-border-light/80 dark:border-border-dark bg-paper/90 dark:bg-ink/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5 font-semibold tracking-[-0.03em]">
          <img src="/favicon.svg" alt="" aria-hidden="true" className="h-7 w-7 rounded-md" />
          <span>INTERVUE</span>
        </Link>
        {!minimal && (
          <nav className="hidden items-center gap-7 text-sm sm:flex">
            <a href="/#how-it-works" className="quiet-link">How it works</a>
            <a href="/#experience" className="quiet-link">The experience</a>
          </nav>
        )}
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {!minimal && <Link to="/setup" className="btn-accent hidden sm:inline-flex">Set up interview</Link>}
        </div>
      </div>
    </header>
  );
}
