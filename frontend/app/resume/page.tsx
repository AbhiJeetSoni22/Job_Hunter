"use client";

import { useState, useCallback } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { ResumeInfoCard } from "@/components/resume/ResumeInfoCard";
import { ResumeUploader } from "@/components/resume/ResumeUploader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import { getResume, uploadResume, deleteResume, ApiClientError } from "@/lib/api";
import type { Resume } from "@/lib/types";

// ── Hook — resume state ────────────────────────────────────────────────────────

function useResume(initial: Resume | null) {
  const [resume, setResume]       = useState<Resume | null>(initial);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting]   = useState(false);

  return { resume, setResume, uploading, setUploading, deleting, setDeleting };
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ResumePage() {
  const { toasts, addToast, dismiss } = useToast();

  // Fetch resume once on mount
  const [initialised, setInitialised] = useState(false);
  const [fetchError,  setFetchError]  = useState<string | null>(null);

  const { resume, setResume, uploading, setUploading, deleting, setDeleting } = useResume(null);

  // Load on mount via useEffect to keep this a pure client component
  // (avoids server/client hydration mismatch from async initial data)
  const [loading, setLoading] = useState(true);

  const loadResume = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getResume();
      setResume(r);
      setFetchError(null);
    } catch (err) {
      setFetchError(err instanceof ApiClientError ? err.message : "Failed to load resume.");
    } finally {
      setLoading(false);
      setInitialised(true);
    }
  }, [setResume]);

  // Run once on mount
  useState(() => { loadResume(); });

  // ── Upload ───────────────────────────────────────────────────────────────────

  async function handleFileSelected(file: File) {
    if (uploading) return;
    setUploading(true);
    try {
      const result = await uploadResume(file);
      setResume(result);
      addToast(`Uploaded "${result.filename}" — ${result.skills.length} skill${result.skills.length !== 1 ? "s" : ""} detected.`, "success");
    } catch (err) {
      addToast(err instanceof ApiClientError ? err.message : "Upload failed.", "error");
    } finally {
      setUploading(false);
    }
  }

  // ── Delete ───────────────────────────────────────────────────────────────────

  async function handleDelete() {
    if (deleting || !resume) return;
    setDeleting(true);
    try {
      await deleteResume();
      setResume(null);
      addToast("Resume deleted.", "success");
    } catch (err) {
      addToast(err instanceof ApiClientError ? err.message : "Delete failed.", "error");
    } finally {
      setDeleting(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-xl">
      <PageHeader
        title="Resume"
        subtitle="Upload a PDF to enable AI match scoring"
      />

      {loading && !initialised ? (
        <div style={{ color: "var(--color-muted)", fontSize: "0.875rem", padding: "2rem 0" }}>
          Loading…
        </div>
      ) : fetchError ? (
        <div style={{ color: "var(--color-red)", fontSize: "0.875rem", padding: "1rem 0" }}>
          {fetchError}
        </div>
      ) : resume ? (
        <>
          <ResumeInfoCard resume={resume} />
          <div className="mt-4 flex gap-3 items-center flex-wrap">
            <Button
              variant="danger"
              size="sm"
              loading={deleting}
              disabled={deleting}
              onClick={handleDelete}
            >
              {deleting ? "Deleting…" : "🗑 Delete Resume"}
            </Button>
            <span style={{ color: "var(--color-muted)", fontSize: "0.75rem" }}>
              Uploading a new PDF replaces the current one.
            </span>
          </div>
          <div className="mt-6">
            <p className="text-xs mb-3 uppercase tracking-wide" style={{ color: "var(--color-muted)" }}>
              Replace resume
            </p>
            <ResumeUploader onFileSelected={handleFileSelected} loading={uploading} />
          </div>
        </>
      ) : (
        <>
          <EmptyState
            icon="📎"
            title="No resume uploaded"
            description="Upload a PDF resume to start scoring jobs against your skills."
          />
          <div className="mt-4">
            <ResumeUploader onFileSelected={handleFileSelected} loading={uploading} />
          </div>
        </>
      )}

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}