"use client";

import { Button } from "@/components/ui/button";

type Props = {
  onOpen: () => void;
};

export function NextStepAction({ onOpen }: Props) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/40 px-5 py-4 flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p
          className="text-xs font-medium tracking-widest uppercase text-muted-foreground"
        >
          Next Step
        </p>
        <p className="text-sm text-foreground/80">
          You can generate a summary of your situation and share it with an
          accountant for review.
        </p>
      </div>
      <Button variant="default" className="self-start" onClick={onOpen}>
        Prepare Summary for Advisor
      </Button>
    </div>
  );
}
