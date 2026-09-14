"use client";
import { useEffect, useRef, useState } from "react";
import { Check, FileDown, Info, X } from "lucide-react";
import {
  api,
  post,
  type Assessment,
  type Analysis,
  type Finding,
} from "@/lib/api";
import { drawSkeleton } from "@/vision/draw";
import MotionTimeline from "./MotionTimeline";
import BodyMap from "./BodyMap";
import { ROMSummary } from "./ROM";
const stateNames: Record<string, string> = {
  needs_review: "A revisar",
  professional_confirmed: "Confirmado",
  professional_rejected: "Descartado",
  detected: "Detectado",
};
function FindingReview({
  finding,
  disabled,
  onReviewed,
  onLocate,
}: {
  finding: Finding;
  disabled: boolean;
  onReviewed: () => void;
  onLocate?: () => void;
}) {
  const [note, setNote] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function review(state: string) {
    setBusy(true);
    setError("");
    try {
      await post("/findings/" + finding.id + "/review", { state, note });
      onReviewed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="finding">
      <summary>
        <span>{finding.description.split(":")[0]}</span>
        <span
          className={
            "badge " +
            (finding.state === "professional_confirmed" ? "positive" : "")
          }
        >
          {stateNames[finding.state]}
        </span>
      </summary>
      <div className="finding-body">
        <p>{finding.description}</p>
        {onLocate && (
          <button className="secondary" onClick={onLocate}>
            Ver instante do extremo observado (
            {((finding.explanation.timestamp_ms || 0) / 1000).toFixed(2)} s)
          </button>
        )}
        <p className="muted">{finding.explanation.reason}</p>
        <p>
          Visibilidade dos landmarks:{" "}
          <strong>{(finding.confidence * 100).toFixed(0)}%</strong>. Não
          representa probabilidade clínica.
        </p>
        <label>
          Observação do fisioterapeuta
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={10000}
            disabled={disabled}
          />
        </label>
        <div className="button-row">
          <button
            disabled={busy || disabled}
            onClick={() => review("professional_confirmed")}
          >
            <Check size={16} />
            Confirmar medida
          </button>
          <button
            className="secondary"
            disabled={busy || disabled}
            onClick={() => review("professional_rejected")}
          >
            <X size={16} />
            Descartar
          </button>
          <button
            className="ghost"
            disabled={busy || disabled}
            onClick={() => review("needs_review")}
          >
            Reabrir revisão
          </button>
        </div>
        {finding.reviews.map((r, i) => (
          <p key={i} className="small muted">
            {new Date(r.created_at).toLocaleString("pt-BR")} ·{" "}
            {stateNames[r.state]} {r.note && "· " + r.note}
          </p>
        ))}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </div>
    </details>
  );
}
export function AnalysisImage({ analysis }: { analysis: Analysis }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (canvas.current)
      drawSkeleton(
        canvas.current,
        analysis.frames[0]?.landmarks || [],
        analysis.media.width,
        analysis.media.height,
      );
  }, [analysis]);
  return (
    <div className="result-image">
      <img
        src={"/api/media/" + analysis.media_id}
        alt={"Captura " + analysis.media.view}
      />
      <canvas ref={canvas} />
    </div>
  );
}
export default function Results({
  assessment,
  onChanged,
  onPending,
}: {
  assessment: Assessment;
  onChanged: (a: Assessment) => void;
  onPending: (pending: boolean) => void;
}) {
  const [selected, setSelected] = useState(0),
    [notes, setNotes] = useState(assessment.notes),
    [conclusion, setConclusion] = useState(assessment.conclusion),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [frame, setFrame] = useState(0),
    [region, setRegion] = useState("");
  const analysis =
      assessment.analyses[Math.min(selected, assessment.analyses.length - 1)],
    done = assessment.status === "completed";
  const baseline = useRef({
    notes: assessment.notes,
    conclusion: assessment.conclusion,
  });
  const dirty =
    !done &&
    (notes !== baseline.current.notes ||
      conclusion !== baseline.current.conclusion);
  useEffect(() => {
    onPending(dirty);
    const leave = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", leave);
    return () => {
      onPending(false);
      window.removeEventListener("beforeunload", leave);
    };
  }, [dirty, onPending]);
  async function reload() {
    try {
      onChanged(await api<Assessment>("/assessments/" + assessment.id));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function save(complete: boolean) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      onChanged(
        await api<Assessment>("/assessments/" + assessment.id, {
          method: "PATCH",
          body: JSON.stringify({
            notes,
            conclusion,
            expected_notes: baseline.current.notes,
            expected_conclusion: baseline.current.conclusion,
            status: complete ? "completed" : "review",
          }),
        }),
      );
      baseline.current = { notes, conclusion };
      setMessage(complete ? "Avaliação concluída." : "Observações salvas.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function report() {
    if (dirty) {
      setError("Salve as observações antes de gerar o relatório.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const r = await fetch("/api/assessments/" + assessment.id + "/report");
      if (!r.ok) throw new Error("Não foi possível gerar o relatório.");
      const url = URL.createObjectURL(await r.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = "avaliacao-" + assessment.id + ".pdf";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!analysis)
    return (
      <div className="panel empty">
        <ScanEmpty />
        <h3>Nenhuma captura analisada</h3>
        <p>Abra a câmera ou envie uma foto para obter medidas reais.</p>
      </div>
    );
  return (
    <div>
      <div className="section-heading">
        <div>
          <span className="eyebrow">MEDIÇÃO OBJETIVA</span>
          <h2>Resultados da avaliação</h2>
        </div>
        <button className="secondary" onClick={report} disabled={busy}>
          <FileDown size={17} />
          Baixar relatório PDF
        </button>
      </div>
      <div className="result-selector">
        <label>
          Captura
          <select
            value={selected}
            onChange={(e) => {
              setSelected(Number(e.target.value));
              setFrame(0);
              setRegion("");
            }}
          >
            {assessment.analyses.map((a, i) => (
              <option key={a.id} value={i}>
                {i + 1} ·{" "}
                {a.media.view
                  .replace("lateral_right", "Lateral direita")
                  .replace("lateral_left", "Lateral esquerda")}{" "}
                · {new Date(a.created_at).toLocaleTimeString("pt-BR")}
              </option>
            ))}
          </select>
        </label>
        <span className="muted">
          Valores preservados com as versões originais dos motores.
        </span>
      </div>
      <ROMSummary analysis={analysis} frame={frame} onSelect={setFrame} />
      <div
        className={
          "results-layout" + (analysis.motion?.version ? " motion-results" : "")
        }
      >
        <div>
          <div className="panel image-panel">
            {analysis.media.mime.startsWith("video/") ? (
              <MotionTimeline
                key={analysis.id}
                analysis={analysis}
                selected={frame}
                onSelect={setFrame}
              />
            ) : (
              <AnalysisImage analysis={analysis} />
            )}
            <div className="image-caption">
              <span>Imagem + landmarks</span>
              <span>
                {analysis.media.width} × {analysis.media.height}
              </span>
            </div>
          </div>
          <div className="panel quality-panel">
            <h3>Qualidade técnica</h3>
            <div className="quality-number">
              {(analysis.quality.landmark_visibility_mean * 100).toFixed(0)}
              <span>%</span>
            </div>
            <p>Visibilidade média dos landmarks disponíveis</p>
            <div className="progress">
              <span style={{ width: analysis.quality.coverage * 100 + "%" }} />
            </div>
            <p className="small muted">
              Cobertura corporal: {(analysis.quality.coverage * 100).toFixed(0)}
              %. Não é uma estimativa de acurácia clínica.
            </p>
            {analysis.quality.messages.map((m) => (
              <p key={m} className="warning">
                {m}
              </p>
            ))}
          </div>
        </div>
        <div className="panel measurement-panel">
          <h3>
            {analysis.motion?.version
              ? "Medidas do movimento · média"
              : "Medidas posturais"}
          </h3>
          <p className="muted">
            Sem classificação de normalidade ou diagnóstico.
          </p>
          <div className="measurements">
            {analysis.measurements
              .slice()
              .sort(
                (a, b) => Number(a.value === null) - Number(b.value === null),
              )
              .map((m) => (
                <div key={m.id} className="measurement">
                  <div>
                    <strong>{m.label}</strong>
                    {m.value === null ? (
                      <p className="small muted">{m.details.reason}</p>
                    ) : (
                      <p className="small muted">
                        Visibilidade técnica {(m.confidence * 100).toFixed(0)}%
                        {m.details.min !== undefined && (
                          <>
                            <br />
                            Mín. {m.details.min.toFixed(1)} · Máx.{" "}
                            {m.details.max?.toFixed(1)} · Amplitude{" "}
                            {m.details.amplitude?.toFixed(1)} {m.unit}
                            <br />
                            {m.details.valid_samples}/{m.details.total_samples}{" "}
                            amostras válidas
                          </>
                        )}
                      </p>
                    )}
                  </div>
                  <span
                    className={
                      m.value === null ? "unavailable" : "measure-value"
                    }
                  >
                    {m.value === null ? (
                      "Não mensurável"
                    ) : (
                      <>
                        {m.value.toFixed(1)}
                        <small>{m.unit}</small>
                      </>
                    )}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>
      <section className="panel review-panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">JULGAMENTO PROFISSIONAL</span>
            <h2>Registros para revisão</h2>
          </div>
          <span className="badge">
            {analysis.findings.filter((f) => f.state === "needs_review").length}{" "}
            a revisar
          </span>
        </div>
        <p className="muted">
          Confirme a qualidade da medida ou descarte o registro. A confirmação
          não constitui diagnóstico.
        </p>
        <BodyMap
          findings={analysis.findings}
          selected={region}
          onSelect={setRegion}
        />
        {analysis.findings
          .filter((f) => !region || f.region === region)
          .map((f) => (
            <FindingReview
              key={f.id}
              finding={f}
              disabled={done}
              onReviewed={() => void reload()}
              onLocate={
                analysis.motion?.version &&
                f.explanation.sample_index !== undefined
                  ? () => {
                      setFrame(f.explanation.sample_index!);
                      document
                        .querySelector(".motion-timeline")
                        ?.scrollIntoView({
                          behavior: "smooth",
                          block: "center",
                        });
                    }
                  : undefined
              }
            />
          ))}
      </section>
      <section className="panel form-panel">
        <h2>Interpretação do fisioterapeuta</h2>
        <label>
          Observações
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={done}
            maxLength={20000}
          />
        </label>
        <label>
          Conclusão profissional
          <textarea
            value={conclusion}
            onChange={(e) => setConclusion(e.target.value)}
            disabled={done}
            maxLength={20000}
          />
        </label>
        <div className="button-row">
          <button disabled={busy || done} onClick={() => save(false)}>
            Salvar observações
          </button>
          <button
            className="secondary"
            disabled={busy || done}
            onClick={() => save(true)}
          >
            Concluir avaliação
          </button>
        </div>
        <p role="status" className="success">
          {message}
        </p>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </section>
      <details className="panel technical">
        <summary>Limitações e rastreabilidade</summary>
        {analysis.quality.limitations.map((l) => (
          <p key={l}>{l}</p>
        ))}
        <p>
          Pose: {analysis.provider_version} · Biomecânica:{" "}
          {analysis.biomechanics_version} · Regras: {analysis.rules_version}
        </p>
      </details>
    </div>
  );
}
function ScanEmpty() {
  return <Info size={32} />;
}
