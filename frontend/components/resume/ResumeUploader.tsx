"use client";

import {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
  DragEvent,
  ChangeEvent,
} from "react";
import { Button } from "@/components/ui/Button";

export interface ResumeUploaderHandle {
  openFileDialog: () => void;
}

interface ResumeUploaderProps {
  onFileSelected: (file: File) => void;
  loading?: boolean;
}

function UploadCloudIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 16V8m0 0L9 11m3-3 3 3" />
      <path d="M20 16.5A4.5 4.5 0 0 0 17.5 10H17a6 6 0 1 0-11.3 2.5A4.5 4.5 0 0 0 4 16.5" />
    </svg>
  );
}

export const ResumeUploader = forwardRef<ResumeUploaderHandle, ResumeUploaderProps>(
  function ResumeUploader({ onFileSelected, loading = false }, ref) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [dragging, setDragging] = useState(false);

    useImperativeHandle(ref, () => ({
      openFileDialog: () => {
        if (!loading) inputRef.current?.click();
      },
    }));

    function handleDrop(e: DragEvent<HTMLDivElement>) {
      e.preventDefault();
      setDragging(false);
      if (loading) return;
      const file = e.dataTransfer.files[0];
      if (file?.type === "application/pdf") onFileSelected(file);
    }

    function handleChange(e: ChangeEvent<HTMLInputElement>) {
      const file = e.target.files?.[0];
      if (file) onFileSelected(file);
    }

    const isActive = dragging && !loading;

    return (
      <div
        onDragOver={(e) => {
          if (!loading) {
            e.preventDefault();
            setDragging(true);
          }
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !loading && inputRef.current?.click()}
        className={`upload-dropzone flex flex-col items-center gap-4 py-12 px-6 text-center rounded-xl ${isActive ? "upload-dropzone-active" : ""}`}
        style={{
          border: `2px dashed ${isActive ? "var(--color-accent)" : "var(--color-border)"}`,
          background: isActive
            ? "linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(99,102,241,0.02) 100%)"
            : "var(--color-bg)",
          cursor: loading ? "not-allowed" : "pointer",
          opacity: loading ? 0.55 : 1,
          pointerEvents: loading ? "none" : "auto",
          transition: "border-color 200ms, background 200ms, opacity 200ms, box-shadow 200ms",
          boxShadow: isActive
            ? "0 0 0 4px rgba(99,102,241,0.1), inset 0 1px 0 rgba(255,255,255,0.03)"
            : "inset 0 1px 0 rgba(255,255,255,0.02)",
        }}
        aria-busy={loading}
      >
        <div
          className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-transform duration-200 ${isActive ? "scale-105" : ""}`}
          style={{
            background: isActive
              ? "rgba(99,102,241,0.2)"
              : "rgba(99,102,241,0.1)",
            color: "var(--color-accent-h)",
            border: `1px solid ${isActive ? "rgba(99,102,241,0.4)" : "rgba(99,102,241,0.2)"}`,
          }}
        >
          <UploadCloudIcon />
        </div>

        <div>
          <p
            className="text-sm font-medium"
            style={{ color: "var(--color-text)" }}
          >
            {loading ? "Processing your resume…" : "Drop your resume here"}
          </p>
          <p
            className="text-xs mt-1.5"
            style={{ color: "var(--color-subtle)" }}
          >
            or click to browse from your device
          </p>
        </div>

        <Button variant="secondary" size="sm" loading={loading} type="button">
          {loading ? "Uploading…" : "Choose PDF file"}
        </Button>

        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleChange}
        />
      </div>
    );
  },
);
