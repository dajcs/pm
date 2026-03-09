"use client";

import { useState } from "react";
import * as api from "@/lib/api";

interface AccountModalProps {
  username: string;
  onClose: () => void;
}

export const AccountModal = ({ username, onClose }: AccountModalProps) => {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next !== confirm) {
      setError("New passwords do not match");
      return;
    }
    if (next.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    try {
      await api.changePassword(current, next);
      setSuccess(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-sm rounded-[24px] border border-[var(--stroke)] bg-white p-7 shadow-[var(--shadow)]">
        <div className="mb-5 flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">Account</p>
            <h2 className="mt-1 font-display text-xl font-bold text-[var(--navy-dark)]">{username}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-lg leading-none px-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {success ? (
          <div className="rounded-xl bg-green-50 border border-green-200 px-4 py-3 text-sm font-medium text-green-700">
            Password updated successfully.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]">
              Change Password
            </p>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-[var(--gray-text)]">Current password</span>
              <input
                type="password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
                className="rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-[var(--gray-text)]">New password</span>
              <input
                type="password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                required
                minLength={6}
                className="rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-[var(--gray-text)]">Confirm new password</span>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                className="rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
              />
            </label>

            {error && (
              <p className="text-sm text-red-600 font-medium" role="alert">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-[var(--primary-blue)] py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Updating..." : "Update Password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
