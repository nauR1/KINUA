"use client";
import { useEffect, useRef, useState } from "react";
import {
  Camera,
  CameraOff,
  Upload,
  ScanLine,
  Check,
  LoaderCircle,
} from "lucide-react";
import { MediaPipePoseProvider } from "@/vision/provider";
import { cameraError } from "@/lib/camera";
import { drawSkeleton } from "@/vision/draw";
import type { PoseProvider } from "@/vision/types";
import { api, post, type Assessment } from "@/lib/api";

const views = [
  ["anterior", "Anterior"],
  ["posterior", "Posterior"],
  ["lateral_right", "Lateral direita"],
  ["lateral_left", "Lateral esquerda"],
];
export default function Capture({
  assessment,
  onSaved,
}: {
  assessment: Assessment;
  onSaved: (a: Assessment) => void;
}) {
  const video = useRef<HTMLVideoElement>(null),
    canvas = useRef<HTMLCanvasElement>(null),
    stream = useRef<MediaStream | null>(null),
    provider = useRef<PoseProvider | null>(null),
    mounted = useRef(true),
    running = useRef(false),
    processing = useRef(false);
  const [live, setLive] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [view, setView] = useState("anterior"),
    [level, setLevel] = useState(false),
    [plane, setPlane] = useState(false),
    [fps, setFps] = useState(5),
    [poseInfo, setPoseInfo] = useState("Aguardando câmera"),
    [preview, setPreview] = useState(""),
    [blob, setBlob] = useState<Blob | null>(null),
    [stage, setStage] = useState("");
  function getProvider() {
    if (!provider.current) provider.current = new MediaPipePoseProvider();
    return provider.current;
  }
  function stop() {
    running.current = false;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    setLive(false);
  }
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      running.current = false;
      stream.current?.getTracks().forEach((t) => t.stop());
      provider.current?.close();
    };
  }, []);
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);
  useEffect(() => {
    if (!live) return;
    const interval = setInterval(async () => {
      if (
        !running.current ||
        processing.current ||
        !video.current ||
        video.current.readyState < 2
      )
        return;
      processing.current = true;
      try {
        const result = await getProvider().detect(
          await createImageBitmap(video.current),
        );
        if (!running.current) return;
        if (canvas.current)
          drawSkeleton(
            canvas.current,
            result.landmarks,
            video.current.videoWidth,
            video.current.videoHeight,
          );
        const required = [
          "nose",
          "left_shoulder",
          "right_shoulder",
          "left_hip",
          "right_hip",
          "left_knee",
          "right_knee",
          "left_ankle",
          "right_ankle",
          "left_foot_index",
          "right_foot_index",
        ];
        const visible = result.landmarks.filter(
          (p) =>
            required.includes(p.name) &&
            p.visibility >= 0.65 &&
            p.x >= 0 &&
            p.x <= 1 &&
            p.y >= 0 &&
            p.y <= 1,
        );
        setPoseInfo(
          visible.length === required.length
            ? "Corpo detectado · confira enquadramento e plano"
            : result.landmarks.length
              ? "Inclua cabeça e pés; verifique obstruções."
              : "Nenhum corpo detectado. Centralize o paciente.",
        );
      } catch (e) {
        if (running.current) {
          setError((e as Error).message);
          stop();
          provider.current?.close();
          provider.current = null;
        }
      } finally {
        processing.current = false;
      }
    }, 1000 / fps);
    return () => clearInterval(interval);
  }, [live, fps]);
  async function start() {
    setError("");
    setBusy(true);
    setBlob(null);
    setPreview("");
    setPoseInfo("Carregando detector corporal…");
    try {
      if (!navigator.mediaDevices?.getUserMedia)
        throw new Error("Câmera indisponível. Abra em localhost ou HTTPS.");
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "environment",
        },
        audio: false,
      });
      if (!mounted.current) {
        stream.current.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current.getVideoTracks().forEach((t) =>
        t.addEventListener("ended", () => {
          if (mounted.current) {
            stop();
            setError(
              "A câmera foi desconectada. Conecte novamente ou envie uma foto.",
            );
          }
        }),
      );
      if (video.current) {
        video.current.srcObject = stream.current;
        await video.current.play();
      }
      running.current = true;
      setLive(true);
    } catch (e) {
      stop();
      if (mounted.current) setError(cameraError(e));
    } finally {
      setBusy(false);
    }
  }
  async function capture() {
    if (!video.current || video.current.readyState < 2) return;
    const c = document.createElement("canvas");
    c.width = video.current.videoWidth;
    c.height = video.current.videoHeight;
    c.getContext("2d")!.drawImage(video.current, 0, 0);
    const b = await new Promise<Blob | null>((r) =>
      c.toBlob(r, "image/jpeg", 0.95),
    );
    if (!b) {
      setError("Não foi possível capturar a imagem.");
      return;
    }
    stop();
    setBlob(b);
    setPreview(URL.createObjectURL(b));
    setPoseInfo("Imagem capturada. Confira o plano antes de processar.");
  }
  async function uploadFile(file: File) {
    stop();
    setBlob(null);
    setPreview("");
    setError("");
    if (file.size > 20 * 1024 * 1024) {
      setError("Use uma imagem de até 20 MB.");
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Use JPEG, PNG ou WebP.");
      return;
    }
    try {
      const bitmap = await createImageBitmap(file);
      if (bitmap.width * bitmap.height > 20_000_000) {
        bitmap.close();
        throw new Error("Limite de 20 megapixels.");
      }
      const c = document.createElement("canvas"),
        scale = Math.min(1, 1920 / Math.max(bitmap.width, bitmap.height));
      c.width = Math.round(bitmap.width * scale);
      c.height = Math.round(bitmap.height * scale);
      c.getContext("2d")!.drawImage(bitmap, 0, 0, c.width, c.height);
      bitmap.close();
      const b = await new Promise<Blob | null>((r) =>
        c.toBlob(r, "image/jpeg", 0.95),
      );
      if (!b) throw new Error("Imagem incompatível.");
      setBlob(b);
      setPreview(URL.createObjectURL(b));
      setPoseInfo("Foto pronta para análise.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function analyze() {
    if (!blob) return;
    setBusy(true);
    setError("");
    try {
      setStage("Salvando imagem…");
      const form = new FormData();
      form.append("file", blob, "capture.jpg");
      form.append("view", view);
      const media = await api<{ id: string }>(
        "/assessments/" + assessment.id + "/media",
        { method: "POST", body: form },
      );
      setStage("Detectando landmarks reais…");
      const response = await fetch("/api/media/" + media.id, {
        credentials: "include",
      });
      if (!response.ok) throw new Error("Falha ao carregar a captura salva.");
      const result = await getProvider().detect(
        await createImageBitmap(await response.blob()),
      );
      if (!result.landmarks.length)
        throw new Error(
          "Não foi possível detectar um corpo nesta captura. A imagem foi salva; repita com melhor enquadramento.",
        );
      setStage("Calculando e salvando medidas…");
      const updated = await post<Assessment>(
        "/assessments/" + assessment.id + "/analyze",
        {
          media_id: media.id,
          ...result,
          camera_level_confirmed: level,
          view_confirmed: plane,
        },
      );
      onSaved(updated);
      setBlob(null);
      setPreview("");
      setPoseInfo(
        "Captura salva. Selecione a próxima vista ou revise os resultados.",
      );
      const index = views.findIndex((v) => v[0] === view);
      if (index < 3) {
        setView(views[index + 1][0]);
        setPlane(false);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      setStage("");
    }
  }
  return (
    <section className="capture-layout">
      <div className="capture-main panel">
        <div className="capture-toolbar">
          <span className="eyebrow">CAPTURA GUIADA</span>
          <span className={"badge " + (live ? "live" : "")}>
            {live ? "CÂMERA ATIVA" : "FOTO / CÂMERA"}
          </span>
        </div>
        <div className="view-tabs" role="group" aria-label="Vista da captura">
          {views.map(([key, label], i) => (
            <button
              key={key}
              className={view === key ? "selected" : "ghost"}
              disabled={busy}
              onClick={() => {
                setView(key);
                setPlane(false);
              }}
            >
              <span>{i + 1}</span>
              {label}
              {assessment.analyses?.some((a) => a.media.view === key) && (
                <Check size={14} />
              )}
            </button>
          ))}
        </div>
        <div className="camera-stage">
          <video
            ref={video}
            muted
            playsInline
            className={live ? "" : "hidden"}
          />
          <canvas
            ref={canvas}
            className={"skeleton " + (live ? "" : "hidden")}
          />
          {preview && (
            <img src={preview} alt="Imagem capturada para avaliação" />
          )}
          {!live && !preview && (
            <div className="camera-empty">
              <div className="scan-icon">
                <ScanLine size={44} />
              </div>
              <h3>Enquadre o corpo inteiro</h3>
              <p>
                Inclua a cabeça e os pés, com iluminação uniforme.
                <br />
                Use uma câmera estável e aproximadamente nivelada.
              </p>
              <button onClick={start} disabled={busy}>
                <Camera size={18} />
                Abrir câmera
              </button>
              <span>
                As imagens só são enviadas quando você escolhe analisar.
              </span>
            </div>
          )}
          {live && <span className="stage-label">{poseInfo}</span>}
        </div>
        <div className="capture-controls">
          <div className="button-row">
            {live ? (
              <>
                <button onClick={capture} disabled={busy}>
                  <Camera size={17} />
                  Capturar imagem
                </button>
                <button className="secondary" onClick={stop}>
                  <CameraOff size={17} />
                  Desligar
                </button>
              </>
            ) : preview ? (
              <button className="secondary" onClick={start} disabled={busy}>
                Refazer com câmera
              </button>
            ) : null}
            <label className="button secondary upload">
              <Upload size={17} />
              Enviar foto
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={busy}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void uploadFile(f);
                  e.target.value = "";
                }}
              />
            </label>
          </div>
          <label className="fps-label">
            Análise ao vivo
            <select
              value={fps}
              onChange={(e) => setFps(Number(e.target.value))}
            >
              <option value={2}>2 FPS</option>
              <option value={5}>5 FPS</option>
              <option value={10}>10 FPS</option>
            </select>
          </label>
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </div>
      <aside className="capture-guide panel">
        <span className="eyebrow">QUALIDADE DA CAPTURA</span>
        <h3>Antes de medir</h3>
        <ol className="check-list">
          <li>Paciente centralizado, cabeça e pés visíveis.</li>
          <li>Iluminação uniforme, sem contraluz.</li>
          <li>Sem obstrução das articulações.</li>
          <li>Câmera estável, sem inclinação.</li>
        </ol>
        <div className="divider" />
        <label className="checkbox">
          <input
            type="checkbox"
            checked={level}
            onChange={(e) => setLevel(e.target.checked)}
            disabled={busy}
          />
          Conferi o nivelamento da câmera.
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={plane}
            onChange={(e) => setPlane(e.target.checked)}
            disabled={busy}
          />
          Confirmei a vista{" "}
          {views.find((v) => v[0] === view)?.[1].toLowerCase()}.
        </label>
        <div className="info-box">
          <strong>Medição em 2D</strong>
          <p>
            Perspectiva e posição da câmera influenciam os valores. A análise
            não fornece diagnóstico.
          </p>
        </div>
        <button
          className="full"
          disabled={!blob || !level || !plane || busy}
          onClick={analyze}
        >
          {busy ? (
            <LoaderCircle className="spin" size={18} />
          ) : (
            <ScanLine size={18} />
          )}{" "}
          {stage || "Analisar e salvar captura"}
        </button>
        <p className="muted small" aria-live="polite">
          {!live && poseInfo}
        </p>
      </aside>
    </section>
  );
}
