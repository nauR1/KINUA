"use client";
import { useEffect, useRef, useState } from "react";
import type { Analysis } from "@/lib/api";
import { drawSkeleton } from "@/vision/draw";
const phases: Record<string, string> = {
  sampled: "Amostra ROM",
  movement_start: "Início do movimento",
  initial: "Inicial",
  descending: "Descida",
  ascending: "Subida",
  maximum: "Maior amplitude",
  final: "Final",
  raising: "Elevação",
  lowering: "Retorno",
  unknown: "Indeterminada",
  insufficient_excursion: "Excursão insuficiente",
};
export default function MotionTimeline({
  analysis,
  selected,
  onSelect,
}: {
  analysis: Analysis;
  selected: number;
  onSelect: (n: number) => void;
}) {
  const video = useRef<HTMLVideoElement>(null),
    overlay = useRef<HTMLCanvasElement>(null),
    synchronized = useRef<number | null>(null);
  const measurable = analysis.measurements.filter((m) => m.value !== null);
  const [key, setKey] = useState(
    measurable.some((m) => m.key === analysis.motion?.signal)
      ? analysis.motion!.signal
      : measurable[0]?.key || "",
  );
  const metric = analysis.measurements.find((m) => m.key === key);
  const frame = analysis.frames[selected] || analysis.frames[0],
    lastTime = analysis.frames.at(-1)?.timestamp_ms || 1;
  useEffect(() => {
    if (overlay.current && frame)
      drawSkeleton(
        overlay.current,
        frame.landmarks,
        analysis.media.width,
        analysis.media.height,
      );
  }, [frame, analysis]);
  function seek(index: number) {
    onSelect(index);
    if (video.current)
      video.current.currentTime = analysis.frames[index].timestamp_ms / 1000;
  }
  function sync() {
    if (!video.current) return;
    const time = video.current.currentTime * 1000;
    let closest = 0;
    analysis.frames.forEach((f, i) => {
      if (
        Math.abs(f.timestamp_ms - time) <
        Math.abs(analysis.frames[closest].timestamp_ms - time)
      )
        closest = i;
    });
    synchronized.current = closest;
    onSelect(closest);
  }
  // Peaks chosen in the findings panel seek the video too.
  useEffect(() => {
    if (synchronized.current === selected) {
      synchronized.current = null;
      return;
    }
    if (
      video.current &&
      frame &&
      Math.abs(video.current.currentTime - frame.timestamp_ms / 1000) > 0.12
    ) {
      video.current.pause();
      video.current.currentTime = frame.timestamp_ms / 1000;
    }
  }, [selected]);
  const partner = key.startsWith("left_")
    ? key.replace("left_", "right_")
    : key.startsWith("right_")
      ? key.replace("right_", "left_")
      : null;
  const values = (metricKey: string) =>
    analysis.frames.map((f) => f.measurements?.values[metricKey] ?? null);
  const primary = values(key),
    secondary = partner ? values(partner) : [];
  const all = [...primary, ...secondary].filter((v): v is number => v !== null);
  const low = all.length ? Math.min(...all) : 0,
    high = all.length ? Math.max(...all) : 1,
    span = Math.max(high - low, 1);
  function path(list: (number | null)[]) {
    let d = "",
      move = true;
    list.forEach((v, i) => {
      if (v === null) {
        move = true;
        return;
      }
      d +=
        (move ? "M" : "L") +
        (40 + (analysis.frames[i].timestamp_ms / lastTime) * 820) +
        "," +
        (180 - ((v - low) / span) * 140) +
        " ";
      move = false;
    });
    return d;
  }
  return (
    <section className="panel motion-panel motion-timeline">
      <div className="section-heading">
        <div>
          <span className="eyebrow">SÉRIE TEMPORAL</span>
          <h2>Vídeo e medidas sincronizados</h2>
        </div>
        {!analysis.motion?.rom && (
          <span className="badge">
            {analysis.motion?.phase_detection.cycles.filter((c) => c.complete)
              .length || 0}{" "}
            ciclos completos · experimental
          </span>
        )}
      </div>
      <div className="motion-layout">
        <div className="video-stage">
          <video
            ref={video}
            src={"/api/media/" + analysis.media_id}
            controls
            muted
            playsInline
            onTimeUpdate={sync}
          />
          <canvas ref={overlay} />
        </div>
        <div>
          <label>
            Parâmetro
            <select value={key} onChange={(e) => setKey(e.target.value)}>
              {measurable.map((m) => (
                <option key={m.key} value={m.key}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <div className="phase-card">
            <span>
              Frame {frame?.frame_index} ·{" "}
              {(frame?.timestamp_ms / 1000).toFixed(2)} s
            </span>
            <strong>{phases[frame?.phase] || "Indeterminada"}</strong>
            <p>
              {primary[selected] === null
                ? "Medida indisponível neste frame"
                : `${primary[selected]?.toFixed(1)} ${metric?.unit || ""}`}
            </p>
          </div>
          <p className="small muted">
            Variação temporal:{" "}
            {frame.measurements?.velocity[key] != null
              ? `${frame.measurements.velocity[key]!.toFixed(2)} ${metric?.unit}/s`
              : "indisponível nesta amostra"}
          </p>
          {partner &&
            primary[selected] != null &&
            secondary[selected] != null && (
              <p className="small muted">
                Diferença D − E neste instante:{" "}
                {(
                  (key.startsWith("right_") ? 1 : -1) *
                  (primary[selected]! - secondary[selected]!)
                ).toFixed(2)}{" "}
                {metric?.unit}
              </p>
            )}
          <p className="small muted">
            Skeleton da amostra mais próxima. Intervalo alvo:{" "}
            {1000 / (analysis.motion?.target_fps || 5)} ms. Lacunas não são
            interpoladas.
          </p>
          <p className="small muted">{analysis.motion?.phase_limitations}</p>
        </div>
      </div>
      <label>
        Frame da análise
        <input
          type="range"
          min={0}
          max={analysis.frames.length - 1}
          value={selected}
          onChange={(e) => seek(Number(e.target.value))}
        />
      </label>
      <div className="chart-legend">
        <span>● {metric?.label}</span>
        {partner && secondary.some((v) => v !== null) && (
          <span className="opposite">● Lado oposto</span>
        )}
        <span>Unidade: {metric?.unit}</span>
      </div>
      <svg
        viewBox="0 0 900 220"
        className="motion-chart"
        role="img"
        aria-label="Medida ao longo do tempo; selecione um frame pelo controle acima"
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          const t =
            Math.max(
              0,
              Math.min(
                1,
                (((e.clientX - box.left) / box.width) * 900 - 40) / 820,
              ),
            ) * lastTime;
          let index = 0;
          analysis.frames.forEach((f, i) => {
            if (
              Math.abs(f.timestamp_ms - t) <
              Math.abs(analysis.frames[index].timestamp_ms - t)
            )
              index = i;
          });
          seek(index);
        }}
      >
        <line x1="40" x2="860" y1="180" y2="180" stroke="var(--line)" />
        <text x="4" y="45">
          {high.toFixed(1)}
        </text>
        <text x="4" y="180">
          {low.toFixed(1)}
        </text>
        <path
          d={path(primary)}
          stroke="var(--accent)"
          fill="none"
          strokeWidth="3"
        />
        <path
          d={path(secondary)}
          stroke="var(--chart-secondary)"
          fill="none"
          strokeWidth="2"
        />
        <line
          x1={40 + ((frame?.timestamp_ms || 0) / lastTime) * 820}
          x2={40 + ((frame?.timestamp_ms || 0) / lastTime) * 820}
          y1="30"
          y2="185"
          stroke="var(--muted)"
          strokeDasharray="4 4"
        />
        <text x="40" y="211">
          0 s
        </text>
        <text x="810" y="211">
          {(lastTime / 1000).toFixed(1)} s
        </text>
      </svg>
      <div className="button-row">
        {analysis.motion?.phase_detection.events.map((event, i) => (
          <button
            className="secondary"
            key={i}
            onClick={() => seek(event.index)}
          >
            {phases[event.type] || "Início"} ·{" "}
            {(event.timestamp_ms / 1000).toFixed(1)} s
          </button>
        ))}
      </div>
    </section>
  );
}
