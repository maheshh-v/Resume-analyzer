"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, SendHorizonal, ShieldCheck, Unlink } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { InlineError } from "@/components/states";
import { ThemeToggle } from "@/components/theme-toggle";
import { ApiError, publicInterviewApi } from "@/lib/api-client";
import { friendlyError } from "@/lib/errors";

function PortalShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="ambient flex min-h-screen flex-col bg-background">
      <header className="border-b border-border/70 bg-background/75 backdrop-blur-md">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
              <ShieldCheck className="size-4" aria-hidden />
            </span>
            <span className="font-semibold tracking-tight">Recruit</span>
            <span className="text-xs text-muted-foreground">· Interview</span>
          </div>
          <ThemeToggle />
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">{children}</main>
      <footer className="mx-auto w-full max-w-2xl px-6 pb-8">
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          Your answers go to a human reviewer alongside the rest of your application. There is no automated pass/fail.
        </p>
      </footer>
    </div>
  );
}

export default function InterviewPortalPage() {
  const { token } = useParams<{ token: string }>();
  const queryClient = useQueryClient();
  const [answerText, setAnswerText] = useState("");
  const pasteCountRef = useRef(0);
  const questionStartRef = useRef<number | null>(null);
  const firstKeystrokeRef = useRef<number | null>(null);

  const stateQuery = useQuery({
    queryKey: ["interview", token],
    queryFn: () => publicInterviewApi.getState(token),
    retry: false,
  });

  const currentQuestionId = stateQuery.data?.current_question?.id ?? null;

  useEffect(() => {
    if (!currentQuestionId) return;
    setAnswerText("");
    pasteCountRef.current = 0;
    firstKeystrokeRef.current = null;
    questionStartRef.current = Date.now();
  }, [currentQuestionId]);

  const submitAnswer = useMutation({
    mutationFn: () => {
      if (!currentQuestionId) throw new Error("No active question");
      const totalTimeMs = questionStartRef.current ? Date.now() - questionStartRef.current : undefined;
      const firstKeystrokeMs =
        firstKeystrokeRef.current && questionStartRef.current
          ? firstKeystrokeRef.current - questionStartRef.current
          : undefined;
      return publicInterviewApi.submitAnswer(token, currentQuestionId, {
        answer_text: answerText,
        total_time_ms: totalTimeMs,
        time_to_first_keystroke_ms: firstKeystrokeMs,
        paste_event_count: pasteCountRef.current,
      });
    },
    onSuccess: (nextState) => {
      queryClient.setQueryData(["interview", token], nextState);
    },
  });

  if (stateQuery.isLoading) {
    return (
      <PortalShell>
        <div className="space-y-4">
          <Skeleton className="h-5 w-40 rounded-md" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </PortalShell>
    );
  }

  if (stateQuery.isError) {
    const err = stateQuery.error as ApiError;
    const message =
      err instanceof ApiError && err.status === 410
        ? "This interview link has expired. Please contact the recruiter for a new one."
        : err instanceof ApiError && err.status === 404
          ? "We couldn't find this interview. Double-check the link you were sent."
          : friendlyError(err, "Something went wrong loading this interview.");
    return (
      <PortalShell>
        <Card className="fade-up">
          <CardContent className="flex flex-col items-center gap-4 py-14 text-center">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-muted">
              <Unlink className="size-5 text-muted-foreground" aria-hidden />
            </span>
            <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">{message}</p>
          </CardContent>
        </Card>
      </PortalShell>
    );
  }

  const state = stateQuery.data!;

  if (state.is_complete) {
    return (
      <PortalShell>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: "easeOut" }}>
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
              <motion.span
                initial={{ scale: 0.6, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.15, type: "spring", stiffness: 260, damping: 18 }}
                className="flex size-14 items-center justify-center rounded-full bg-verdict-verified-bg"
              >
                <CheckCircle2 className="size-7 text-verdict-verified" aria-hidden />
              </motion.span>
              <p className="text-lg font-semibold tracking-tight">Thanks — you&apos;re done.</p>
              <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
                The recruiting team will review your answers alongside the rest of your application. There&apos;s no
                automated pass/fail here.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </PortalShell>
    );
  }

  return (
    <PortalShell>
      <div className="mb-6 space-y-2.5">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Question {(state.current_question?.ordinal ?? 0) + 1}</span>
          <span className="tabular">{state.questions_answered} answered so far</span>
        </div>
        <div className="h-1 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
          <div
            className="h-full rounded-full bg-primary/70 transition-all duration-500 ease-out"
            style={{ width: `${Math.min(100, (state.questions_answered / Math.max(1, (state.current_question?.ordinal ?? 0) + 1)) * 100)}%` }}
          />
        </div>
      </div>
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestionId ?? "empty"}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        >
          <Card>
            <CardContent className="space-y-5 py-6">
              <p className="text-lg leading-relaxed font-medium">{state.current_question?.question_text}</p>
              <Textarea
                rows={8}
                value={answerText}
                onChange={(e) => {
                  if (firstKeystrokeRef.current === null) firstKeystrokeRef.current = Date.now();
                  setAnswerText(e.target.value);
                }}
                onPaste={() => {
                  pasteCountRef.current += 1;
                }}
                placeholder="Be specific — numbers, tools, tradeoffs. There's no wrong length."
                className="text-base"
                autoFocus
                disabled={submitAnswer.isPending}
              />
              {submitAnswer.isError && (
                <InlineError message={friendlyError(submitAnswer.error, "Couldn't submit your answer. Please try again — nothing was lost.")} />
              )}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-muted-foreground">Specific beats polished. Write like you&apos;d talk.</p>
                <Button onClick={() => submitAnswer.mutate()} disabled={!answerText.trim() || submitAnswer.isPending}>
                  {submitAnswer.isPending ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <SendHorizonal className="size-4" aria-hidden />
                  )}
                  {submitAnswer.isPending ? "Submitting..." : "Submit answer"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>
    </PortalShell>
  );
}
