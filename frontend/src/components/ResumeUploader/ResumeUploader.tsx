import { useCallback, useRef, useState } from "react";

const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const MAX_SIZE_MB = 5;

interface ResumeUploaderProps {
  file: File | null;
  onChange: (file: File | null) => void;
}

export function ResumeUploader({ file, onChange }: ResumeUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSet = useCallback(
    (candidate: File | undefined) => {
      if (!candidate) return;
      const ext = "." + candidate.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        setError("Please upload a PDF or DOCX file.");
        return;
      }
      if (candidate.size > MAX_SIZE_MB * 1024 * 1024) {
        setError(`File is too large. Max size is ${MAX_SIZE_MB}MB.`);
        return;
      }
      setError(null);
      onChange(candidate);
    },
    [onChange]
  );

  if (file) {
    return (
      <div className="surface flex items-center justify-between rounded-xl px-4 py-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-paper-dim dark:bg-ink-soft text-sm">
            {file.name.endsWith(".pdf") ? "PDF" : "DOC"}
          </span>
          <div>
            <p className="text-sm font-medium">{file.name}</p>
            <p className="text-xs text-ink/50 dark:text-paper/50">{(file.size / 1024).toFixed(0)} KB · ready</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => onChange(null)}
          className="text-sm text-ink/50 dark:text-paper/50 hover:text-signal-rose transition-colors"
        >
          Remove
        </button>
      </div>
    );
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          validateAndSet(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border border-dashed px-6 py-10 text-center transition-colors
                    ${isDragging ? "border-accent bg-accent/5" : "border-border-light dark:border-border-dark hover:border-accent/50"}`}
      >
        <p className="text-sm font-medium">Drag and drop your resume, or click to browse</p>
        <p className="mt-1 text-xs text-ink/50 dark:text-paper/50">PDF or DOCX, up to {MAX_SIZE_MB}MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => validateAndSet(e.target.files?.[0])}
        />
      </div>
      {error && <p className="mt-2 text-xs text-signal-rose">{error}</p>}
    </div>
  );
}
