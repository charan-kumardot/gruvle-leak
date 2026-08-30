"use client";

import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";

export default function ActionsPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-950">Actions</h1>
        <p className="mt-1 text-sm text-ink-500">
          Recovery steps drafted from confirmed findings — assign them, track status, done.
        </p>
      </div>

      <EmptyState
        eyebrow="No actions yet"
        title="Actions show up once you confirm a finding."
        description="Confirm a suspected leak from the Leaks page and Gruvle will draft a recommended next step here."
        action={
          <Link href="/leaks">
            <Button size="lg" variant="secondary">
              Go to Leaks
            </Button>
          </Link>
        }
      />
    </div>
  );
}
