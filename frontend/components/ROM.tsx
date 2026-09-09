"use client";
import { useEffect, useState } from "react";
import { api, post, type Patient, type Analysis } from "@/lib/api";
import {
  sideLabels,
  type ROMDefinition,
  type ROMRecord,
} from "@/lib/protocols";
import EmptyState from "./ui/EmptyState";

export function ROMLauncher({
  patients,
  patientId,
  onOpen,
}: {
  patients: Patient[];
  patientId?: string;
  onOpen: (id: string) => void;
}) {
  const [definitions, setDefinitions] = useState<ROMDefinition[]>([]),
    [patient, setPatient] = useState(patientId || patients[0]?.id || ""),
    [movement, setMovement] = useState("shoulder_flexion"),
    [side, setSide] = useState("right"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<ROMDefinition[]>("/rom/movements")
      .then(setDefinitions)
      .catch((e) => setError(e.message));
  }, []);
  const config = definitions.find((d) => d.movement === movement);
  async function start() {
    setBusy(true);
    setError("");
    try {
      const r = await post<{ assessment_id: string }>("/rom/assessments", {
        patient_id: patient,
        movement,
        side,
      });
      onOpen(r.assessment_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel">
        <span className="eyebrow">KINUA ROM</span>
        <h2>Amplitude de movimento</h2>
        <p className="muted">
          Acompanhe ângulos projetados, extremos e excursão observada. A medição
          2D não substitui a avaliação clínica.
        </p>
        <div className="form-grid">
          <label>
            Paciente do ROM
            <select
              value={patient}
              onChange={(e) => setPatient(e.target.value)}
            >
              <option value="">Selecione</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Articulação e movimento
            <select
              value={movement}
              onChange={(e) => {
                setMovement(e.target.value);
                setSide("right");
              }}
            >
              {definitions.map((d) => (
                <option key={d.movement} value={d.movement}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Lado do ROM
            <select value={side} onChange={(e) => setSide(e.target.value)}>
              <option value="right">Direito</option>
              <option value="left">Esquerdo</option>
              {config?.plane === "frontal" && (
                <option value="bilateral">Ambos, na mesma captura</option>
              )}
            </select>
          </label>
        </div>
        {config && (
          <div className="info-box">
            <strong>
              Plano{" "}
              {config.plane === "frontal"
                ? "frontal — câmera à frente ou atrás"
                : "sagital — câmera no lado avaliado"}
            </strong>
            <p>{config.instructions}</p>
            <p>
              Segmentos necessários:{" "}
              {config.points
                .map(
                  (p) =>
                    ({
                      shoulder: "ombro",
                      hip: "quadril",
                      elbow: "cotovelo",
                      wrist: "punho",
                      knee: "joelho",
                      ankle: "tornozelo",
                    })[p as "hip"],
                )
                .join(" → ")}
            </p>
            {config.direction < 0 && (
              <p>
                Extensão: será registrado o menor ângulo de flexão residual.
                Hiperextensão não é distinguida.
              </p>
            )}
          </div>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button disabled={busy || !patient || !config} onClick={start}>
          Iniciar avaliação ROM
        </button>
        {!patients.length && (
          <p className="muted">Cadastre um paciente para medir ROM.</p>
        )}
      </section>
      {patient && (
        <ROMHistory key={patient} patientId={patient} onOpen={onOpen} />
      )}
    </>
  );
}

export function ROMSummary({
  analysis,
  frame,
  onSelect,
}: {
  analysis: Analysis;
  frame: number;
  onSelect: (index: number) => void;
}) {
  const records = analysis.rom_measurements || [];
  const config = analysis.motion?.rom;
  if (!config) return null;
  return (
    <section className="panel rom-summary">
      <span className="eyebrow">KINUA ROM · {config.version}</span>
      <h2>{config.name}</h2>
      <p className="muted small">
        Plano {config.plane === "frontal" ? "frontal" : "sagital"} · medidas
        estimadas por vídeo 2D.
      </p>
      <div className="rom-value-grid">
        {records.map((r) => {
          const current =
            analysis.frames[frame]?.measurements?.values[r.side + "_rom"];
          return (
            <article key={r.id}>
              <span>{sideLabels[r.side]}</span>
              <strong>
                {current == null ? "—" : current.toFixed(1) + "°"}
              </strong>
              <small>Ângulo no frame selecionado</small>
              <dl>
                <dt>Máximo registrado</dt>
                <dd>{r.maximum.toFixed(1)}°</dd>
                <dt>
                  {config.direction < 0
                    ? "Mínima flexão residual"
                    : "Pico observado"}
                </dt>
                <dd>{r.peak_value.toFixed(1)}°</dd>
                <dt>Excursão observada</dt>
                <dd>{r.excursion.toFixed(1)}°</dd>
                <dt>Visibilidade no pico</dt>
                <dd>{(r.confidence * 100).toFixed(0)}%</dd>
                <dt>Amostras válidas</dt>
                <dd>
                  {r.details.valid_samples}/{r.details.total_samples}
                </dd>
              </dl>
              <button
                className="secondary"
                onClick={() => onSelect(r.details.peak_index)}
              >
                Ver pico · frame {r.peak_frame_index}
              </button>
              {r.details.movement_start_index == null && (
                <p className="small muted">
                  Início do movimento não identificado com estabilidade
                  suficiente.
                </p>
              )}
            </article>
          );
        })}
      </div>
      {records.length === 2 &&
        (() => {
          const left = analysis.frames[frame]?.measurements?.values.left_rom,
            right = analysis.frames[frame]?.measurements?.values.right_rom;
          return (
            <p>
              Diferença absoluta D/E neste frame:{" "}
              <strong>
                {left == null || right == null
                  ? "Indisponível"
                  : Math.abs(right - left).toFixed(1) + "°"}
              </strong>
            </p>
          );
        })()}
      <p className="small muted">
        A confiança técnica deriva da visibilidade dos landmarks, não representa
        acurácia clínica. O extremo de cada lado pode ocorrer em frames
        diferentes.
      </p>
    </section>
  );
}

export function ROMHistory({
  patientId,
  onOpen,
}: {
  patientId: string;
  onOpen: (id: string) => void;
}) {
  const [rows, setRows] = useState<ROMRecord[]>([]),
    [definitions, setDefinitions] = useState<ROMDefinition[]>([]),
    [error, setError] = useState(""),
    [movement, setMovement] = useState(""),
    [side, setSide] = useState("right");
  useEffect(() => {
    let gone = false;
    Promise.all([
      api<ROMRecord[]>(`/patients/${patientId}/rom`),
      api<ROMDefinition[]>("/rom/movements"),
    ])
      .then(([r, d]) => {
        if (!gone) {
          setRows(r);
          setDefinitions(d);
          setMovement(r.at(-1)?.movement || "knee_flexion");
        }
      })
      .catch((e) => {
        if (!gone) setError(e.message);
      });
    return () => {
      gone = true;
    };
  }, [patientId]);
  const filtered = rows.filter(
      (r) => r.movement === movement && r.side === side,
    ),
    confirmed = filtered.filter(
      (r) => r.review_state === "professional_confirmed",
    ),
    latest = confirmed.at(-1);
  const series = confirmed.filter(
    (r) =>
      r.view === latest?.view &&
      r.engine_version === latest?.engine_version &&
      r.provider_version === latest?.provider_version &&
      r.fps === latest?.fps,
  );
  const low = Math.min(...series.map((r) => r.peak_value), 0),
    high = Math.max(...series.map((r) => r.peak_value), 1),
    span = Math.max(1, high - low);
  const x = (i: number) => 40 + (i / Math.max(1, series.length - 1)) * 600,
    y = (r: ROMRecord) => 155 - ((r.peak_value - low) / span) * 120;
  return (
    <section className="panel">
      <span className="eyebrow">HISTÓRICO ROM</span>
      <h2>Movimento ao longo do tempo</h2>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!rows.length && !error ? (
        <EmptyState
          title="Ainda sem medidas ROM"
          description="As capturas de ROM salvas para este paciente aparecerão aqui."
        />
      ) : (
        <>
          <div className="form-grid">
            <label>
              Movimento no histórico
              <select
                value={movement}
                onChange={(e) => setMovement(e.target.value)}
              >
                {definitions.map((d) => (
                  <option value={d.movement} key={d.movement}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Lado no histórico
              <select value={side} onChange={(e) => setSide(e.target.value)}>
                <option value="right">Direito</option>
                <option value="left">Esquerdo</option>
              </select>
            </label>
          </div>
          {series.length > 0 && (
            <svg
              className="rom-history-chart"
              viewBox="0 0 690 200"
              role="group"
              aria-label="Histórico de picos ROM confirmados, por data"
            >
              <path
                d={series
                  .map((r, i) => (i ? "L" : "M") + x(i) + "," + y(r))
                  .join(" ")}
                fill="none"
                stroke="var(--accent)"
                strokeWidth="2"
              />
              {series.map((r, i) => (
                <g
                  key={r.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`Abrir ROM ${r.peak_value.toFixed(1)} graus de ${new Date(r.created_at!).toLocaleDateString("pt-BR")}`}
                  onClick={() => onOpen(r.assessment_id!)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onOpen(r.assessment_id!);
                    }
                  }}
                >
                  <circle cx={x(i)} cy={y(r)} r="6" fill="var(--accent)" />
                  <text x={x(i)} y={y(r) - 12} textAnchor="middle">
                    {r.peak_value.toFixed(1)}°
                  </text>
                  <text x={x(i)} y="183" textAnchor="middle">
                    {new Date(r.created_at!).toLocaleDateString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                    })}
                  </text>
                </g>
              ))}
            </svg>
          )}
          {series.length > 1 && (
            <p>
              Variação observada entre primeiro e último registro compatível:{" "}
              <strong>
                {(series.at(-1)!.peak_value - series[0].peak_value).toFixed(1)}°
              </strong>
              .
            </p>
          )}
          <p className="muted small">
            O gráfico usa somente medidas confirmadas, do mesmo lado, movimento,
            plano, modelo, versão e FPS do último registro confirmado. Não
            indica melhora clínica. Em extensão, o valor é a flexão residual
            mínima.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Pico</th>
                  <th>Excursão</th>
                  <th>Revisão</th>
                  <th>Avaliação</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id}>
                    <td>{new Date(r.created_at!).toLocaleString("pt-BR")}</td>
                    <td>{r.peak_value.toFixed(1)}°</td>
                    <td>{r.excursion.toFixed(1)}°</td>
                    <td>
                      {r.review_state === "professional_confirmed"
                        ? "Confirmado"
                        : r.review_state === "professional_rejected"
                          ? "Descartado"
                          : "A revisar"}
                    </td>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => onOpen(r.assessment_id!)}
                      >
                        Abrir ROM
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
