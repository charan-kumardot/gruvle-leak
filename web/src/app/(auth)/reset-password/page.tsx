"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { account } from "@/lib/appwrite";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<Card><CardBody className="pt-6 text-sm text-ink-400">Loading…</CardBody></Card>}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const userId = searchParams.get("userId");
  const secret = searchParams.get("secret");

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!userId || !secret) return;
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await account.updateRecovery(userId, secret, password);
      setDone(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "This reset link may have expired. Request a new one and try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (!userId || !secret) {
    return (
      <Card>
        <CardHeader>
          <h1 className="text-xl font-semibold tracking-tight text-ink-950">Invalid reset link</h1>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-ink-600">
            This link is missing or malformed. Request a new one from the login page.
          </p>
          <p className="mt-6 text-center text-sm text-ink-500">
            <Link href="/forgot-password" className="font-medium text-ink-900 hover:text-accent-600">
              Request a new link
            </Link>
          </p>
        </CardBody>
      </Card>
    );
  }

  if (done) {
    return (
      <Card>
        <CardHeader>
          <h1 className="text-xl font-semibold tracking-tight text-ink-950">Password updated</h1>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-ink-600">You can now log in with your new password.</p>
          <Button className="mt-6 w-full" onClick={() => router.push("/login")}>
            Go to login
          </Button>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <h1 className="text-xl font-semibold tracking-tight text-ink-950">Set a new password</h1>
      </CardHeader>
      <CardBody>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Input
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
          {error && <p className="text-sm text-accent-600">{error}</p>}
          <Button type="submit" disabled={submitting} className="mt-1">
            {submitting ? "Saving…" : "Update password"}
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
