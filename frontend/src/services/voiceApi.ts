import { ApiError, apiPost, apiPostForm } from "./api";

export interface TranscribeResult {
  text: string;
  providerUsed: string;
}

export interface SynthesizeResult {
  audioUrl: string;
  providerUsed: string;
}

export async function transcribeAudio(blob: Blob): Promise<TranscribeResult> {
  const form = new FormData();
  form.append("audio", blob, "answer.webm");
  const res = await apiPostForm<{ text: string; provider_used: string }>("/api/voice/transcribe", form);
  return { text: res.text, providerUsed: res.provider_used };
}

export async function synthesizeSpeech(text: string): Promise<SynthesizeResult> {
  const res = await apiPost<{ audio_base64: string; mime_type: string; provider_used: string }>(
    "/api/voice/synthesize",
    { text }
  );
  const byteChars = atob(res.audio_base64);
  const bytes = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
  const blob = new Blob([bytes], { type: res.mime_type });
  return { audioUrl: URL.createObjectURL(blob), providerUsed: res.provider_used };
}

export { ApiError };
