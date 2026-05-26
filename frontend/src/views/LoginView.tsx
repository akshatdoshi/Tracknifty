import { useState } from "react";
import { api } from "../api/client";

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("manager1");
  const [password, setPassword] = useState("manager123");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(username, password);
      onLogin();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mb-2 text-3xl font-bold text-indigo-400">Tracknifty</div>
          <div className="text-sm text-slate-500">AI-Driven BSH Recommendation Engine</div>
        </div>
        <form
          onSubmit={submit}
          className="rounded-xl border border-slate-800 bg-slate-900 p-8 shadow-2xl"
        >
          <label className="mb-4 block">
            <span className="text-sm font-medium text-slate-300">Username</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </label>
          <label className="mb-6 block">
            <span className="text-sm font-medium text-slate-300">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </label>

          {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="mt-5 text-center text-xs text-slate-600">
            admin / admin123 · manager1 / manager123 · manager2 / manager123
          </p>
        </form>
      </div>
    </div>
  );
}
