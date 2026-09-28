"""
Security helpers.

Two responsibilities live here:

1. Upload validation (file type / size) so we never parse arbitrary files.
2. Light "prompt injection awareness" for text that gets embedded into LLM
   prompts (resume text, job descriptions, candidate answers). We do not try
   to be a bulletproof injection filter (that's an open research problem),
   but we:
     - always keep instructions and untrusted content in clearly separated
       message roles/sections (see agents/prompts/*.py),
     - strip characters commonly used to fake a role switch,
     - cap the length of any single blob that gets embedded in a prompt.
"""
import re

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Sequences a malicious resume/JD could use to try to hijack the prompt by
# pretending to be a new instruction block.
_SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore (all )?(previous|above) instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"</?(system|assistant|user)>", re.IGNORECASE),
]

MAX_EMBEDDED_TEXT_CHARS = 12_000
MAX_RESUME_EMBEDDED_TEXT_CHARS = 40_000


def validate_resume_upload(file: UploadFile, raw_bytes: bytes) -> None:
    settings = get_settings()
    filename = (file.filename or "").lower()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""

    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Please upload a PDF or DOCX file.",
        )

    if file.content_type and file.content_type not in ALLOWED_RESUME_MIME_TYPES:
        # Some browsers send generic types (application/octet-stream); we only
        # hard-reject when the content type is clearly something else.
        if file.content_type not in ("application/octet-stream", ""):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type '{file.content_type}'.",
            )

    max_bytes = settings.max_resume_size_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {settings.max_resume_size_mb}MB.",
        )

    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")


def sanitize_for_prompt(text: str, *, label: str = "content") -> str:
    """
    Defuse obvious prompt-injection attempts in untrusted text (resume text,
    job descriptions, candidate answers) before it is embedded into an LLM
    prompt, and cap its length. This text is always wrapped in clearly
    delimited sections in the actual prompt templates - this function is a
    second layer, not the only layer.
    """
    if not text:
        return ""

    cleaned = text
    for pattern in _SUSPICIOUS_PATTERNS:
        cleaned = pattern.sub("[redacted]", cleaned)

    if len(cleaned) > MAX_EMBEDDED_TEXT_CHARS:
        cleaned = cleaned[:MAX_EMBEDDED_TEXT_CHARS] + f"\n...[{label} truncated]"

    return cleaned



def sanitize_resume_for_prompt(text: str) -> str:
    """Sanitize the original resume with a larger bound than short prompt blobs.

    Resumes are the primary grounding source for the interviewer, so truncating
    them at the generic 12k prompt limit can silently hide later sections.
    """
    if not text:
        return ""
    cleaned = text
    for pattern in _SUSPICIOUS_PATTERNS:
        cleaned = pattern.sub("[redacted]", cleaned)
    if len(cleaned) > MAX_RESUME_EMBEDDED_TEXT_CHARS:
        cleaned = cleaned[:MAX_RESUME_EMBEDDED_TEXT_CHARS] + "\n...[full resume truncated for safety]"
    return cleaned
