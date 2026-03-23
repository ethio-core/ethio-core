"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Camera, Loader2, RotateCcw } from "lucide-react";

type Props = {
  title?: string;
  subtitle?: string;
  onCaptured: (dataUrl: string) => void;
  disabled?: boolean;
};

type CaptureState =
  | { status: "idle" }
  | { status: "requesting" }
  | { status: "streaming" }
  | { status: "captured"; dataUrl: string }
  | { status: "error"; message: string };

function stopStream(stream: MediaStream | null) {
  if (!stream) return;
  for (const track of stream.getTracks()) track.stop();
}

export function BiometricCameraCapture({
  title = "Face Recognition",
  subtitle = "Allow camera access and take a photo",
  onCaptured,
  disabled,
}: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [captureState, setCaptureState] = useState<CaptureState>({ status: "idle" });

  const isSupported = useMemo(() => {
    if (typeof window === "undefined") return false;
    return Boolean(navigator.mediaDevices?.getUserMedia);
  }, []);

  useEffect(() => {
    return () => {
      stopStream(streamRef.current);
      streamRef.current = null;
    };
  }, []);

  const startCamera = async () => {
    if (disabled) return;

    if (typeof window !== "undefined" && !window.isSecureContext) {
      setCaptureState({
        status: "error",
        message: "Camera requires HTTPS (or http://localhost).",
      });
      return;
    }

    if (!isSupported) {
      setCaptureState({
        status: "error",
        message: "Camera not supported in this browser.",
      });
      return;
    }

    setCaptureState({ status: "requesting" });

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 720 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;

      const videoEl = videoRef.current;
      if (!videoEl) {
        stopStream(stream);
        streamRef.current = null;
        setCaptureState({ status: "error", message: "Camera element not ready." });
        return;
      }

      videoEl.srcObject = stream;
      await videoEl.play();
      setCaptureState({ status: "streaming" });
    } catch (e) {
      const message = e instanceof Error ? e.message : "Camera permission denied.";
      setCaptureState({ status: "error", message });
    }
  };

  const takePhoto = () => {
    if (disabled) return;

    const videoEl = videoRef.current;
    if (!videoEl) return;

    const width = videoEl.videoWidth || 720;
    const height = videoEl.videoHeight || 720;

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setCaptureState({ status: "error", message: "Unable to capture image." });
      return;
    }

    ctx.drawImage(videoEl, 0, 0, width, height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

    stopStream(streamRef.current);
    streamRef.current = null;

    setCaptureState({ status: "captured", dataUrl });
    onCaptured(dataUrl);
  };

  const retake = () => {
    stopStream(streamRef.current);
    streamRef.current = null;
    setCaptureState({ status: "idle" });
  };

  return (
    <div className="flex flex-col items-center rounded-lg border-2 border-dashed border-border bg-muted/30 p-8">
      {captureState.status === "captured" ? (
        <>
          <div className="mb-4 w-full max-w-sm overflow-hidden rounded-lg border border-border bg-card">
            <Image
              src={captureState.dataUrl}
              alt="Captured biometric"
              width={720}
              height={720}
              className="h-auto w-full"
              unoptimized
            />
          </div>
          <h3 className="mb-2 font-semibold text-foreground">Biometric Captured</h3>
          <p className="mb-4 text-center text-sm text-muted-foreground">
            Photo captured locally for demo biometric enrollment.
          </p>
          <Button variant="outline" onClick={retake} disabled={disabled}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Retake
          </Button>
        </>
      ) : (
        <>
          <div className="mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-muted">
            {captureState.status === "requesting" ? (
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
            ) : (
              <Camera className="h-10 w-10 text-muted-foreground" />
            )}
          </div>

          <div
            className={
              captureState.status === "streaming"
                ? "mb-4 w-full max-w-sm overflow-hidden rounded-lg border border-border bg-card"
                : "hidden"
            }
          >
            <video ref={videoRef} className="h-auto w-full" playsInline muted />
          </div>

          <h3 className="mb-2 font-semibold text-foreground">
            {captureState.status === "requesting"
              ? "Starting camera..."
              : captureState.status === "streaming"
                ? "Camera Ready"
                : title}
          </h3>

          <p className="mb-4 text-center text-sm text-muted-foreground">
            {captureState.status === "error" ? captureState.message : subtitle}
          </p>

          {captureState.status === "streaming" ? (
            <>
              <Button onClick={takePhoto} disabled={disabled}>
                <Camera className="mr-2 h-4 w-4" />
                Take Photo
              </Button>
            </>
          ) : (
            <Button onClick={startCamera} disabled={disabled || captureState.status === "requesting"}>
              {captureState.status === "requesting" ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Camera className="mr-2 h-4 w-4" />
                  Start Camera
                </>
              )}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
