"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/overview");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not log in. Check your credentials."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <h1 className="text-xl font-semibold tracking-tight text-ink-950">
          Log in
        </h1>
        <p className="mt-1.5 text-sm text-ink-500">
          Welcome back. Pick up where you left off.
        </p>
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
          <Input
            label="Password"
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-accent-600">{error}</p>}
          <Button type="submit" disabled={submitting} className="mt-1">
            {submitting ? "Logging in…" : "Log in"}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-ink-500">
          New to Gruvle?{" "}
          <Link href="/signup" className="font-medium text-ink-900 hover:text-accent-600">
            Create an account
          </Link>
        </p>
      </CardBody>
    </Card>
  );
}
