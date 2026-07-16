"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, publicInterviewApi } from "@/lib/api-client";

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
      const firstKeystrokeMs = firstKeystrokeRef.current && questionStartRef.current ? firstKeystrokeRef.current - questionStartRef.current : undefined;
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
      <div className="mx-auto max-w-2xl p-8">
        <Skeleton className="h-64 rounded-lg" />
      </div>
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
      <div className="mx-auto flex min-h-screen max-w-2xl items-center p-8">
        <Card className="w-full">
          <CardContent className="py-10 text-center text-sm text-muted-foreground">{message}</CardContent>
        </Card>
      </div>
    );
  }

  const state = stateQuery.data!;

  if (state.is_complete) {
    return (
      <div className="mx-auto flex min-h-screen max-w-2xl items-center p-8">
        <Card className="w-full">
          <CardContent className="space-y-2 py-10 text-center">
            <p className="text-lg font-medium">Thanks — you&apos;re done.</p>
            <p className="text-sm text-muted-foreground">
              The recruiting team will review your answers alongside the rest of your application. There&apos;s no automated pass/fail here.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-screen max-w-2xl p-8">
      <div className="mb-6 text-sm text-muted-foreground">
        Question {(state.current_question?.ordinal ?? 0) + 1} · {state.questions_answered} answered so far
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-normal leading-relaxed">{state.current_question?.question_text}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
          />
          {submitAnswer.isError && <p className="text-sm text-destructive">{(submitAnswer.error as Error).message}</p>}
          <Button onClick={() => submitAnswer.mutate()} disabled={!answerText.trim() || submitAnswer.isPending}>
            {submitAnswer.isPending ? "Submitting..." : "Submit answer"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
