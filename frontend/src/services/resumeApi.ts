import { apiPostForm } from "./api";
import type { CandidateProfile } from "../types/candidate";

export async function parseResumePreview(file: File): Promise<CandidateProfile> {
  const form = new FormData();
  form.append("resume", file);
  return apiPostForm<CandidateProfile>("/api/resume/parse", form);
}
