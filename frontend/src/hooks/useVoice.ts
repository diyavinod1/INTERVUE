import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeAudio, synthesizeSpeech } from "../services/voiceApi";
import type { VoiceUIState } from "../types/interview";

interface UseVoiceResult {
  voiceState: VoiceUIState;
  errorMessage: string | null;
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<string | null>;
  speak: (text: string) => Promise<void>;
  stopSpeaking: () => void;
}

function getSupportedMimeType(): string {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }

  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];

  for (const mimeType of candidates) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }

  return "";
}

function getMicrophoneErrorMessage(error: unknown): string {
  if (error instanceof DOMException) {
    switch (error.name) {
      case "NotAllowedError":
      case "PermissionDeniedError":
        return (
          "Microphone access was blocked. Allow microphone permission in " +
          "your browser settings and try again."
        );

      case "NotFoundError":
      case "DevicesNotFoundError":
        return (
          "No microphone was found. Connect a microphone or earphones with " +
          "a microphone and try again."
        );

      case "NotReadableError":
      case "TrackStartError":
        return (
          "Your microphone is currently unavailable. Another app may be " +
          "using it, or the selected input device may not be working."
        );

      case "OverconstrainedError":
        return (
          "The selected microphone does not support the required audio " +
          "settings. Try another microphone."
        );

      case "SecurityError":
        return (
          "Microphone access is blocked by your browser or this page. " +
          "Check your browser permissions and try again."
        );

      default:
        break;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return (
    "Couldn't access your microphone. Check browser permissions and make " +
    "sure the correct microphone is selected."
  );
}

export function useVoice(): UseVoiceResult {
  const [voiceState, setVoiceState] = useState<VoiceUIState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const stopStream = useCallback(() => {
    const stream = streamRef.current;

    if (stream) {
      stream.getTracks().forEach((track) => {
        track.stop();
      });

      streamRef.current = null;
    }
  }, []);

  const cleanupAudio = useCallback(() => {
    const audio = audioElRef.current;

    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      audio.src = "";
      audioElRef.current = null;
    }

    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  const startRecording = useCallback(async () => {
    setErrorMessage(null);

    if (isRecording || mediaRecorderRef.current) {
      return;
    }

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          "Microphone access is not supported by this browser."
        );
      }

      if (typeof MediaRecorder === "undefined") {
        throw new Error(
          "Audio recording is not supported by this browser."
        );
      }

      // Stop any previous audio playback before recording.
      cleanupAudio();

      // Clean up any stale stream from an interrupted recording.
      stopStream();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;

      const audioTracks = stream.getAudioTracks();

      if (audioTracks.length === 0) {
        stopStream();
        throw new Error("No microphone audio track was created.");
      }

      const audioTrack = audioTracks[0];

      if (!audioTrack.enabled) {
        stopStream();
        throw new Error("The selected microphone is disabled.");
      }

      if (audioTrack.readyState !== "live") {
        stopStream();
        throw new Error(
          "The selected microphone is not available."
        );
      }

      const mimeType = getSupportedMimeType();

      let recorder: MediaRecorder;

      try {
        recorder = mimeType
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream);
      } catch {
        stopStream();
        throw new Error(
          "Your browser could not start audio recording. Please try Chrome, Edge, or Safari."
        );
      }

      chunksRef.current = [];

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        setVoiceState("error");
        setErrorMessage(
          "The microphone recording encountered a problem. Please try again."
        );

        stopStream();
        mediaRecorderRef.current = null;
        setIsRecording(false);
      };

      recorder.start(250);

      mediaRecorderRef.current = recorder;

      setIsRecording(true);
      setVoiceState("recording");
    } catch (error) {
      stopStream();

      mediaRecorderRef.current = null;
      chunksRef.current = [];

      setIsRecording(false);
      setVoiceState("error");
      setErrorMessage(getMicrophoneErrorMessage(error));
    }
  }, [cleanupAudio, isRecording, stopStream]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    const recorder = mediaRecorderRef.current;

    if (!recorder || recorder.state === "inactive") {
      stopStream();
      setIsRecording(false);
      return null;
    }

    return new Promise((resolve) => {
      let settled = false;

      const finish = (result: string | null) => {
        if (settled) {
          return;
        }

        settled = true;
        resolve(result);
      };

      recorder.onstop = async () => {
        setIsRecording(false);

        // Stop the microphone immediately once recording ends.
        stopStream();

        mediaRecorderRef.current = null;

        const chunks = [...chunksRef.current];
        chunksRef.current = [];

        if (chunks.length === 0) {
          setVoiceState("error");
          setErrorMessage(
            "No audio was recorded. Please check your microphone and try again."
          );

          finish(null);
          return;
        }

        const mimeType =
          recorder.mimeType ||
          chunks.find((chunk) => chunk.type)?.type ||
          "audio/webm";

        const blob = new Blob(chunks, {
          type: mimeType,
        });

        if (blob.size === 0) {
          setVoiceState("error");
          setErrorMessage(
            "The recording was empty. Please check your microphone and try again."
          );

          finish(null);
          return;
        }

        try {
          setVoiceState("transcribing");

          const { text } = await transcribeAudio(blob);

          const cleanedText = (text || "").trim();

          if (!cleanedText) {
            throw new Error("The transcription was empty.");
          }

          setVoiceState("idle");
          setErrorMessage(null);

          finish(cleanedText);
        } catch {
          setVoiceState("error");

          setErrorMessage(
            "Voice transcription is unavailable right now.\n\n" +
              "If you're using a microphone, make sure microphone permission " +
              "is enabled and the correct input device is selected. If you're " +
              "using earphones or headphones, try disconnecting them and " +
              "recording again.\n\n" +
              "You can also type your answer instead."
          );

          finish(null);
        }
      };

      recorder.onerror = () => {
        stopStream();

        mediaRecorderRef.current = null;
        chunksRef.current = [];

        setIsRecording(false);
        setVoiceState("error");
        setErrorMessage(
          "The recording could not be completed. Please try again."
        );

        finish(null);
      };

      try {
        if (recorder.state === "recording") {
          recorder.stop();
        } else {
          stopStream();
          mediaRecorderRef.current = null;
          setIsRecording(false);
          finish(null);
        }
      } catch {
        stopStream();

        mediaRecorderRef.current = null;
        setIsRecording(false);
        setVoiceState("error");
        setErrorMessage(
          "Couldn't finish the recording. Please try again."
        );

        finish(null);
      }
    });
  }, [stopStream]);

  const speak = useCallback(
    async (text: string) => {
      const cleanedText = text.trim();

      if (!cleanedText) {
        return;
      }

      setErrorMessage(null);

      // Stop currently playing speech before starting new speech.
      cleanupAudio();

      setVoiceState("generating");

      try {
        const { audioUrl } = await synthesizeSpeech(cleanedText);

        audioUrlRef.current = audioUrl;

        const audio = new Audio(audioUrl);

        audioElRef.current = audio;

        setVoiceState("speaking");

        await new Promise<void>((resolve) => {
          let finished = false;

          const finish = () => {
            if (finished) {
              return;
            }

            finished = true;
            resolve();
          };

          audio.onended = finish;
          audio.onerror = finish;

          void audio.play().catch(() => {
            finish();
          });
        });

        cleanupAudio();

        setVoiceState("idle");
      } catch {
        cleanupAudio();

        setVoiceState("error");
        setErrorMessage(
          "Couldn't play the question aloud. The question is still available as text."
        );
      }
    },
    [cleanupAudio]
  );

  const stopSpeaking = useCallback(() => {
    cleanupAudio();
    setVoiceState("idle");
  }, [cleanupAudio]);

  // Clean up microphone/audio resources when the component using this hook
  // is unmounted.
  useEffect(() => {
    return () => {
      const recorder = mediaRecorderRef.current;

      if (recorder && recorder.state !== "inactive") {
        try {
          recorder.stop();
        } catch {
          // Ignore cleanup errors during unmount.
        }
      }

      stopStream();
      cleanupAudio();

      mediaRecorderRef.current = null;
      chunksRef.current = [];
    };
  }, [cleanupAudio, stopStream]);

  return {
    voiceState,
    errorMessage,
    isRecording,
    startRecording,
    stopRecording,
    speak,
    stopSpeaking,
  };
}