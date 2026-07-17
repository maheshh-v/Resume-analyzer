"use client";

import { AlertTriangle, RotateCw, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Shared empty/error surfaces so every screen fails and idles the same way. */

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  body?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-card/50 px-6 py-16 text-center",
        className,
      )}
    >
      <span className="flex size-14 items-center justify-center rounded-2xl bg-primary/[0.07] ring-1 ring-primary/10">
        <Icon className="size-6 text-primary/70" aria-hidden />
      </span>
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        {body && <p className="mx-auto max-w-sm text-sm leading-relaxed text-muted-foreground">{body}</p>}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  retrying = false,
  className,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-4 rounded-2xl border border-destructive/20 bg-destructive/[0.04] px-6 py-14 text-center",
        className,
      )}
    >
      <span className="flex size-12 items-center justify-center rounded-2xl bg-destructive/10">
        <AlertTriangle className="size-5 text-destructive" aria-hidden />
      </span>
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        <p className="mx-auto max-w-sm text-sm leading-relaxed text-muted-foreground">{message}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} disabled={retrying}>
          <RotateCw className={cn("size-3.5", retrying && "animate-spin")} aria-hidden />
          {retrying ? "Retrying..." : "Try again"}
        </Button>
      )}
    </div>
  );
}

/** Inline (non-blocking) error line for forms and dialogs. */
export function InlineError({ message, className }: { message: string; className?: string }) {
  return (
    <p role="alert" className={cn("flex items-start gap-1.5 text-sm text-destructive", className)}>
      <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      <span>{message}</span>
    </p>
  );
}
