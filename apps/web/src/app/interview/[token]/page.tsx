"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, SendHorizonal, ShieldCheck } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, publicInterviewApi } from "@/lib/api-client";

function PortalShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-2xl items-center gap-2 px-6 py-4">
          <span className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ShieldCheck className="size-3.5" aria-hidden />
          </span>
          <span className="font-semibold tracking-tight">Recruit</span>
          <span className="text-xs text-muted-foreground">· Interview</span>
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">{children}</main>
      <footer className="mx-auto w-full max-w-2xl px-6 pb-8">
        <p className="text-xs text-muted-foreground">
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
        <Skeleton className="h-64 rounded-xl" />
      </PortalShell>
    );
  }

  if (stateQuery.isError) {
    const err = stateQuery.error as ApiError;
    const message =
      err.status === 410
        ? "This interview link has expired. Please contact the recruiter for a new one."
        : err.status === 404
          ? "We couldn't find this interview. Double-check the link you were sent."
          : "Something went wrong loading this interview.";
    return (
      <PortalShell>
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">{message}</CardContent>
        </Card>
      </PortalShell>
    );
  }

  const state = stateQuery.data!;

  if (state.is_complete) {
    return (
      <PortalShell>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
              <CheckCircle2 className="size-10 text-verdict-verified" aria-hidden />
              <p className="text-lg font-medium">Thanks — you&apos;re done.</p>
              <p className="max-w-sm text-sm text-muted-foreground">
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
      <div className="mb-6 flex items-center justify-between text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Question {(state.current_question?.ordinal ?? 0) + 1}</span>
        <span>{state.questions_answered} answered so far</span>
      </div>
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestionId ?? "empty"}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2 }}
        >
          <Card>
            <CardContent className="space-y-5 py-6">
              <p className="text-lg leading-relaxed">{state.current_question?.question_text}</p>
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
              />
              {submitAnswer.isError && <p className="text-sm text-destructive">{(submitAnswer.error as Error).message}</p>}
              <div className="flex items-center justify-between">
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
