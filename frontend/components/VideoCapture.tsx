"use client";
import { useEffect, useRef, useState } from "react";
import { Camera, Square, Upload, Play, LoaderCircle } from "lucide-react";
import { api, post, type Assessment, type ProcessingJob } from "@/lib/api";
import { cameraError } from "@/lib/camera";
import ROMLive from "./ROMLive";
export default function VideoCapture({
  assessment,
  onSaved,
}: {
  assessment: Assessment;
  onSaved: (a: Assessment) => void;
}) {
  const [jobs, setJobs] = useState(assessment.jobs || []),
    [view, setView] = useState(
      assessment.rom_session?.definition.plane === "sagittal"
        ? "lateral_" + assessment.side
        : "anterior",
    ),
    [fps, setFps] = useState(5),
    [level, setLevel] = useState(false),
    [plane, setPlane] = useState(false),
    [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState(""),
    [recording, setRecording] = useState(false),
    [seconds, setSeconds] = useState(0),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [stage, setStage] = useState("");
  const video = useRef<HTMLVideoElement>(null),
    canvas = useRef<HTMLCanvasElement>(null),
    stream = useRef<MediaStream | null>(null),
    recorder = useRef<MediaRecorder | null>(null),
    timer = useRef<ReturnType<typeof setInterval> | null>(null),
    mounted = useRef(true);
  const active = jobs.some((j) => ["pending", "running"].includes(j.state));
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) clearInterval(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  useEffect(() => {
    if (!active) return;
    let gone = false;
    const interval = setInterval(async () => {
      try {
        const next = await api<ProcessingJob[]>(
          "/assessments/" + assessment.id + "/jobs",
        );
        if (gone) return;
        setJobs(next);
        if (
          next.some(
            (j) =>
              j.state === "succeeded" &&
              !assessment.analyses.some((a) => a.media_id === j.media_id),
          )
        )
          onSaved(await api<Assessment>("/assessments/" + assessment.id));
      } catch (e) {
        if (!gone) setError((e as Error).message);
      }
    }, 1500);
    return () => {
      gone = true;
      clearInterval(interval);
    };
  }, [active, assessment, onSaved]);
  function selectFile(f: File) {
    setFile(null);
    setPreview("");
    setError("");
    if (f.size > 100 * 1024 * 1024) {
      setError("Limite de 100 MB.");
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
    if (video.current) video.current.srcObject = null;
  }
  function stop() {
    if (recorder.current?.state === "recording") recorder.current.stop();
    if (timer.current) clearInterval(timer.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    setRecording(false);
  }
  async function record() {
    setError("");
    setBusy(true);
    setPreview("");
    setFile(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
        throw new Error(
          "Gravação indisponível. Use HTTPS/localhost ou envie um vídeo.",
        );
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
              "A câmera foi desconectada. Confira a gravação antes de continuar.",
            );
          }
        }),
      );
      const mime = ["video/webm;codecs=vp8", "video/webm", "video/mp4"].find(
        (m) => MediaRecorder.isTypeSupported(m),
      );
      if (!mime)
        throw new Error("Navegador sem formato compatível de gravação.");
      const parts: Blob[] = [];
      recorder.current = new MediaRecorder(stream.current, {
        mimeType: mime,
        videoBitsPerSecond: 2500000,
      });
      recorder.current.ondataavailable = (e) => {
        if (e.data.size) parts.push(e.data);
      };
      recorder.current.onerror = () => {
        stop();
        setError("Falha na gravação. Confira a câmera e tente novamente.");
      };
      recorder.current.onstop = () => {
        if (mounted.current) {
          const ext = mime.includes("mp4") ? "mp4" : "webm";
          selectFile(new File(parts, "captura." + ext, { type: mime }));
        }
      };
      if (video.current) {
        video.current.srcObject = stream.current;
        await video.current.play();
      }
      recorder.current.start();
      setRecording(true);
      setSeconds(0);
      let elapsed = 0;
      timer.current = setInterval(() => {
        elapsed++;
        setSeconds(elapsed);
        if (elapsed >= 60) stop();
      }, 1000);
    } catch (e) {
      stop();
      setError(cameraError(e));
    } finally {
      setBusy(false);
    }
  }
  async function startJob(mediaId: string) {
    const job = await post<ProcessingJob>(
      "/assessments/" + assessment.id + "/jobs",
      {
        media_id: mediaId,
        fps,
        camera_level_confirmed: level,
        view_confirmed: plane,
      },
    );
    setJobs((old) => [...old.filter((j) => j.id !== job.id), job]);
  }
  async function submit() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      setStage("Enviando e verificando vídeo…");
      const form = new FormData();
      form.append("file", file);
      form.append("view", view);
      const media = await api<{ id: string }>(
        "/assessments/" + assessment.id + "/videos",
        { method: "POST", body: form },
      );
      await startJob(media.id);
      setFile(null);
      setStage("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStage("");
      setBusy(false);
    }
  }
  async function cancel(id: string) {
    try {
      await post("/jobs/" + id + "/cancel", {});
      setJobs(
        await api<ProcessingJob[]>("/assessments/" + assessment.id + "/jobs"),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function retry(job: ProcessingJob) {
    setBusy(true);
    try {
      const next = await post<ProcessingJob>(
        "/assessments/" + assessment.id + "/jobs",
        { ...job.options, media_id: job.media_id },
      );
      setJobs(jobs.map((j) => (j.id === next.id ? next : j)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="capture-layout">
      <section className="panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">ANÁLISE DE MOVIMENTO</span>
            <h2>Vídeo da avaliação</h2>
          </div>
          <span className="badge">
            {recording ? `Gravando · ${seconds}s` : "Até 60 segundos"}
          </span>
        </div>
        <div className="video-stage">
          <video
            ref={video}
            src={preview || undefined}
            controls={!!preview}
            muted
            playsInline
          />
          {assessment.rom_session && recording && <canvas ref={canvas} />}
          {!preview && !recording && (
            <div className="video-placeholder">
              <Camera size={36} />
              <p>Grave ou envie um vídeo do movimento.</p>
            </div>
          )}
        </div>
        {assessment.rom_session && (
          <ROMLive
            video={video}
            canvas={canvas}
            active={recording}
            config={assessment.rom_session.definition}
            side={assessment.side}
            view={view}
            confirmed={plane && level}
          />
        )}
        <div className="button-row">
          {recording ? (
            <button onClick={stop}>
              <Square size={16} />
              Parar gravação
            </button>
          ) : (
            <button
              className="secondary"
              disabled={
                busy ||
                active ||
                (!!assessment.rom_session && (!plane || !level))
              }
              onClick={record}
            >
              <Camera size={17} />
              Gravar movimento
            </button>
          )}
          <label className="button secondary upload">
            <Upload size={17} />
            Enviar vídeo
            <input
              type="file"
              accept="video/mp4,video/webm,.mp4,.webm"
              disabled={busy || active || recording}
              onChange={(e) => {
                if (e.target.files?.[0]) selectFile(e.target.files[0]);
                e.target.value = "";
              }}
            />
          </label>
        </div>
        {jobs.map((j) => (
          <div className="job-card" key={j.id}>
            <div className="section-heading">
              <strong>
                {
                  (
                    {
                      pending: "Na fila",
                      running: "Processando vídeo",
                      succeeded: "Análise salva",
                      failed: "Não foi possível analisar",
                      cancelled: "Cancelado",
                    } as Record<string, string>
                  )[j.state]
                }
              </strong>
              {["pending", "running"].includes(j.state) && (
                <button className="ghost" onClick={() => cancel(j.id)}>
                  Cancelar processamento
                </button>
              )}
            </div>
            <div className="progress">
              <span style={{ width: j.progress * 100 + "%" }} />
            </div>
            {j.error && <p className="error">{j.error}</p>}
            {["failed", "cancelled"].includes(j.state) && (
              <button
                className="secondary"
                disabled={busy || active || recording}
                onClick={() => retry(j)}
              >
                Tentar novamente
              </button>
            )}
            {j.state === "pending" && (
              <p className="small muted">
                Aguardando o processador de vídeos. Você pode sair desta tela e
                acompanhar pelo histórico.
              </p>
            )}
            {j.state === "succeeded" && (
              <button
                className="text-button"
                onClick={async () =>
                  onSaved(
                    await api<Assessment>("/assessments/" + assessment.id),
                  )
                }
              >
                Abrir resultados
              </button>
            )}
          </div>
        ))}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </section>
      <aside className="panel capture-guide">
        <span className="eyebrow">PROTOCOLO DE CAPTURA</span>
        <h3>Uma pessoa, câmera fixa</h3>
        {assessment.rom_session && (
          <div className="info-box">
            <strong>{assessment.rom_session.definition.name}</strong>
            <p>{assessment.rom_session.definition.instructions}</p>
            <p>
              Plano{" "}
              {assessment.rom_session.definition.plane === "frontal"
                ? "frontal"
                : "sagital"}{" "}
              · lado{" "}
              {assessment.side === "right"
                ? "direito"
                : assessment.side === "left"
                  ? "esquerdo"
                  : "bilateral"}
              .
            </p>
          </div>
        )}
        <p className="small muted">
          Comece parado por um segundo, execute o movimento e termine parado.
          Inclua cabeça, mãos e pés.
        </p>
        <label>
          Vista do vídeo
          <select
            value={view}
            onChange={(e) => {
              setView(e.target.value);
              setPlane(false);
            }}
            disabled={busy || active || recording || !!assessment.rom_session}
          >
            <option value="anterior">Anterior</option>
            <option value="posterior">Posterior</option>
            <option value="lateral_right">Lateral direita</option>
            <option value="lateral_left">Lateral esquerda</option>
          </select>
        </label>
        <label>
          Amostragem
          <select
            value={fps}
            onChange={(e) => setFps(Number(e.target.value))}
            disabled={busy || active || recording}
          >
            <option value={2}>2 quadros por segundo</option>
            <option value={5}>5 quadros por segundo</option>
            <option value={10}>10 quadros por segundo</option>
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={level}
            onChange={(e) => setLevel(e.target.checked)}
            disabled={busy || active || recording}
          />
          Conferi a câmera fixa e nivelada.
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={plane}
            onChange={(e) => setPlane(e.target.checked)}
            disabled={busy || active || recording}
          />
          Confirmei o plano do movimento.
        </label>
        <div className="info-box">
          <strong>O plano limita a medida</strong>
          <p>
            Use vista lateral para flexão de joelho. A vista frontal mostra
            projeções D/E, pelve e tronco. Fases são experimentais.
          </p>
        </div>
        <button
          className="full"
          disabled={!file || busy || active || recording || !plane || !level}
          onClick={submit}
        >
          {busy ? (
            <LoaderCircle size={17} className="spin" />
          ) : (
            <Play size={17} />
          )}{" "}
          {stage || "Processar vídeo"}
        </button>
      </aside>
    </div>
  );
}
