"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Card } from "@/components/ui/Card";
import { ResumePageHeader } from "@/components/resume/ResumePageHeader";
import { ResumeUploadCard } from "@/components/resume/ResumeUploadCard";
import { ResumeUploadProgress } from "@/components/resume/ResumeUploadProgress";
import { ResumeOverviewCard } from "@/components/resume/ResumeOverviewCard";
import { ResumeSkillsCard } from "@/components/resume/ResumeSkillsCard";
import { ResumeEmptyPanel } from "@/components/resume/ResumeEmptyPanel";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  getResume,
  uploadResume,
  deleteResume,
  ApiClientError,
} from "@/lib/api";
import type { Resume } from "@/lib/types";
import type { ResumeUploaderHandle } from "@/components/resume/ResumeUploader";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

type UploadProgressStatus = "idle" | "uploading" | "success" | "error";

function useResume(initial: Resume | null) {
  const [resume, setResume] = useState<Resume | null>(initial);
  const [deleting, setDeleting] = useState(false);
  return { resume, setResume, deleting, setDeleting };
}

function ResumePageSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card padding="md" className="card-elevated">
        <Skeleton width="40%" height="1rem" />
        <div className="mt-2">
          <Skeleton width="65%" height="0.75rem" />
        </div>
        <div className="mt-6">
          <Skeleton width="100%" height="12rem" rounded="0.75rem" />
        </div>
      </Card>
      <Card padding="md" className="card-elevated">
        <Skeleton width="45%" height="1rem" />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Skeleton width="100%" height="4.5rem" rounded="0.5rem" />
          <Skeleton width="100%" height="4.5rem" rounded="0.5rem" />
        </div>
        <div className="mt-4">
          <Skeleton width="100%" height="8rem" rounded="0.5rem" />
        </div>
      </Card>
    </div>
  );
}

export default function ResumePage() {
  const { toasts, addToast, dismiss } = useToast();
  const uploaderRef = useRef<ResumeUploaderHandle>(null);

  const [initialised, setInitialised] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const { resume, setResume, deleting, setDeleting } = useResume(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadProgressStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadFilename, setUploadFilename] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadResume = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getResume();
      setResume(r);
      setFetchError(null);
    } catch (err) {
      setFetchError(
        err instanceof ApiClientError ? err.message : "Failed to load resume.",
      );
    } finally {
      setLoading(false);
      setInitialised(true);
    }
  }, [setResume]);

  useEffect(() => {
    loadResume();
  }, [loadResume]);

  const dismissUploadProgress = useCallback(() => {
    setUploadStatus("idle");
    setUploadError(null);
    setUploadFilename(null);
  }, []);

  async function handleFileSelected(file: File) {
    if (uploadStatus === "uploading") return;

    setUploadFilename(file.name);
    setUploadError(null);
    setUploadStatus("uploading");

    try {
      const result = await uploadResume(file);
      setResume(result);
      setUploadStatus("success");
      addToast(
        `Uploaded "${result.filename}" — ${result.skills.length} skill${result.skills.length !== 1 ? "s" : ""} detected.`,
        "success",
      );
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : "Upload failed.";
      setUploadError(message);
      setUploadStatus("error");
      addToast(message, "error");
    }
  }

  async function handleDelete() {
    if (deleting || !resume) return;

    setDeleting(true);

    try {
      await deleteResume();

      setResume(null);

      setShowDeleteDialog(false);

      addToast("Resume deleted.", "success");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      <ResumePageHeader resume={resume} />

      {loading && !initialised ? (
        <ResumePageSkeleton />
      ) : fetchError ? (
        <Card padding="md" className="card-elevated">
          <p className="text-sm" style={{ color: "var(--color-red)" }}>
            {fetchError}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Left column — upload */}
          <div className="space-y-0">
            <ResumeUploadCard
              uploaderRef={uploaderRef}
              onFileSelected={handleFileSelected}
              loading={uploadStatus === "uploading"}
              variant={resume ? "replace" : "primary"}
            />
            {uploadStatus !== "idle" && (
              <ResumeUploadProgress
                status={uploadStatus}
                filename={uploadFilename ?? undefined}
                errorMessage={uploadError ?? undefined}
                onDismiss={dismissUploadProgress}
              />
            )}
          </div>

          {/* Right column — overview or empty state */}
          <div className="space-y-6">
            {resume ? (
              <>
                <ResumeOverviewCard
                  resume={resume}
                  onDelete={() => setShowDeleteDialog(true)}
                  deleting={deleting}
                />
                <ResumeSkillsCard resume={resume} />
              </>
            ) : (
              <ResumeEmptyPanel
                onUploadClick={() => uploaderRef.current?.openFileDialog()}
              />
            )}
          </div>
        </div>
      )}
      <ConfirmDialog
        open={showDeleteDialog}
        title="Delete Resume?"
        description="This action cannot be undone. Your uploaded resume and extracted skills will be permanently removed."
        confirmText="Delete Resume"
        cancelText="Cancel"
        loading={deleting}
        onCancel={() => setShowDeleteDialog(false)}
        onConfirm={handleDelete}
      />
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
