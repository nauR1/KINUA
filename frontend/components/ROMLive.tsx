"use client";
import { useEffect, useRef, useState, type RefObject } from "react";
import { MediaPipePoseProvider } from "@/vision/provider";
import { drawSkeleton } from "@/vision/draw";
import { post, type Measurement } from "@/lib/api";
import { sideLabels, type ROMDefinition } from "@/lib/protocols";

export default function ROMLive({
  video,
  canvas,
  active,
  config,
  side,
  view,
  confirmed,
}: {
  video: RefObject<HTMLVideoElement | null>;
  canvas: RefObject<HTMLCanvasElement | null>;
  active: boolean;
  config: ROMDefinition;
  side: string;
  view: string;
  confirmed: boolean;
}) {
  const [measures, setMeasures] = useState<Measurement[]>([]),
    [error, setError] = useState(""),
    [messages, setMessages] = useState<string[]>([]);
  const maxima = useRef<Record<string, number>>({});
  useEffect(() => {
    if (!active) {
      setMeasures([]);
      return;
    }
    let stopped = false,
      processing = false;
    maxima.current = {};
    setError("");
    const detector = new MediaPipePoseProvider();
    const timer = setInterval(async () => {
      const v = video.current;
      if (stopped || processing || !v || v.readyState < 2) return;
      processing = true;
      try {
        const pose = await detector.detect(await createImageBitmap(v));
        if (stopped) return;
        if (canvas.current)
          drawSkeleton(
            canvas.current,
            pose.landmarks,
            v.videoWidth,
            v.videoHeight,
          );
        if (!confirmed) {
          setMessages(["Confirme o plano e o nivelamento antes de medir."]);
          setMeasures([]);
          return;
        }
        const sample = document.createElement("canvas");
        sample.width = 16;
        sample.height = 16;
        const ctx = sample.getContext("2d")!;
        ctx.drawImage(v, 0, 0, 16, 16);
        const pixels = ctx.getImageData(0, 0, 16, 16).data;
        let sum = 0;
        for (let i = 0; i < pixels.length; i += 4)
          sum +=
            0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2];
        const data = await post<{
          measurements: Measurement[];
          quality: { messages: string[] };
        }>("/rom/preview", {
          movement: config.movement,
          side,
          view,
          landmarks: pose.landmarks,
          width: v.videoWidth,
          height: v.videoHeight,
          brightness: sum / (256 * 255),
          plane_confirmed: true,
        });
        if (stopped) return;
        for (const m of data.measurements)
          if (m.value !== null)
            maxima.current[m.key] = Math.max(
              maxima.current[m.key] ?? m.value,
              m.value,
            );
        setMeasures(data.measurements);
        setMessages(data.quality.messages);
        setError("");
      } catch (e) {
        if (!stopped) {
          setError((e as Error).message);
          setMeasures([]);
          if (canvas.current) {
            const ctx = canvas.current.getContext("2d");
            ctx?.clearRect(0, 0, canvas.current.width, canvas.current.height);
          }
        }
      } finally {
        processing = false;
      }
    }, 333);
    return () => {
      stopped = true;
      clearInterval(timer);
      detector.close();
    };
  }, [active, config, side, view, confirmed, video, canvas]);
  if (!active) return null;
  return (
    <div className="rom-live">
      <span className="eyebrow">ROM AO VIVO · PRÉVIA</span>
      <div className="button-row">
        {measures.map((m) => (
          <div key={m.key}>
            <strong>
              {sideLabels[m.details.side]}:{" "}
              {m.value === null ? "Indisponível" : m.value.toFixed(1) + "°"}
            </strong>
            <p className="small">
              Máximo na prévia: {maxima.current[m.key]?.toFixed(1) ?? "—"}° ·
              visibilidade {(m.confidence * 100).toFixed(0)}%
            </p>
          </div>
        ))}
      </div>
      {!measures.length && !error && <p>Detectando segmentos…</p>}
      {messages.map((m) => (
        <p className="small" key={m}>
          {m}
        </p>
      ))}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <p className="small muted">
        Prévia transitória. O vídeo será reprocessado para salvar medidas,
        landmarks, pico e qualidade com as versões do servidor.
      </p>
    </div>
  );
}
