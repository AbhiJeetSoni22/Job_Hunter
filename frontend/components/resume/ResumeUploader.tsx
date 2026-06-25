"use client";

import { useRef, useState, DragEvent, ChangeEvent } from "react";
import { Button } from "@/components/ui/Button";

interface ResumeUploaderProps {
  onFileSelected: (file: File) => void;
  loading?: boolean;
}

export function ResumeUploader({ onFileSelected, loading = false }: ResumeUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file?.type === "application/pdf") onFileSelected(file);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      style={{
        border: `2px dashed ${dragging ? "var(--color-accent)" : "var(--color-border)"}`,
        background: dragging ? "rgba(99,102,241,0.05)" : "var(--color-surface)",
        borderRadius: "0.625rem",
        cursor: "pointer",
        transition: "border-color 150ms, background 150ms",
      }}
      className="flex flex-col items-center gap-3 py-10 px-6 text-center"
    >
      <span style={{ fontSize: "2rem" }}>📎</span>
      <div>
        <p style={{ color: "var(--color-text)", fontWeight: 500 }}>
          Drop your resume here
        </p>
        <p style={{ color: "var(--color-subtle)", fontSize: "0.8rem", marginTop: "0.25rem" }}>
          PDF only · max 5 MB
        </p>
      </div>
      <Button variant="secondary" size="sm" loading={loading} type="button">
        Choose file
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
}
