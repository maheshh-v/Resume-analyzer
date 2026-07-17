"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Class-based dark mode toggle. The initial class is set pre-paint by the inline script in
 * the root layout; this component only reads it after mount (so SSR markup stays stable). */
export function ThemeToggle({ className }: { className?: string }) {
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      // Private browsing may block storage — the toggle still works for this session.
    }
    setDark(next);
  }

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      className={cn("text-muted-foreground hover:text-foreground", className)}
    >
      {dark === null ? (
        <span className="size-4" aria-hidden />
      ) : dark ? (
        <Sun className="size-4 transition-transform duration-300 hover:rotate-45" aria-hidden />
      ) : (
        <Moon className="size-4 transition-transform duration-300 hover:-rotate-12" aria-hidden />
      )}
    </Button>
  );
}
