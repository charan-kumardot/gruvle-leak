"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { account } from "@/lib/appwrite";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const redirectUrl = `${window.location.origin}/reset-password`;
      await account.createRecovery(email, redirectUrl);
      setSent(true);
    } catch (err) {
      // Deliberately vague on failure too — don't reveal whether an email is registered.
      setError(err instanceof Error ? err.message : "Could not send the reset email. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <Card>
        <CardHeader>
          <h1 className="text-xl font-semibold tracking-tight text-ink-950">Check your email</h1>
        </CardHeader>
        <CardBody>
          <p className="text-sm leading-relaxed text-ink-600">
            If an account exists for <strong>{email}</strong>, we&apos;ve sent a link to reset your
            password. It expires in an hour.
          </p>
          <p className="mt-6 text-center text-sm text-ink-500">
            <Link href="/login" className="font-medium text-ink-900 hover:text-accent-600">
              Back to log in
            </Link>
          </p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <h1 className="text-xl font-semibold tracking-tight text-ink-950">Reset your password</h1>
        <p className="mt-1.5 text-sm text-ink-500">We&apos;ll email you a link to set a new one.</p>
      </CardHeader>
      <CardBody>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Email"
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {error && <p className="text-sm text-accent-600">{error}</p>}
          <Button type="submit" disabled={submitting} className="mt-1">
            {submitting ? "Sending…" : "Send reset link"}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-ink-500">
          <Link href="/login" className="font-medium text-ink-900 hover:text-accent-600">
            Back to log in
          </Link>
        </p>
      </CardBody>
    </Card>
  );
}
