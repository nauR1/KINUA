"use client";
import { useEffect, useState } from "react";
import { api, type Assessment, type Analysis } from "@/lib/api";
import { AnalysisImage } from "./Results";
type Result = {
  comparable: boolean;
  reasons: string[];
  notice?: string;
  measurements: {
    key: string;
    label: string;
    unit: string;
    a: number | null;
    b: number | null;
    difference: number | null;
    reason: string | null;
    statistic: string;
  }[];
};
export default function Comparison({ history }: { history: Assessment[] }) {
  const [options, setOptions] = useState<
      { analysis: Analysis; assessment: Assessment }[]
    >([]),
    [a, setA] = useState(""),
    [b, setB] = useState(""),
    [result, setResult] = useState<Result | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [opened, setOpened] = useState(false);
  useEffect(() => {
    setOpened(false);
    setOptions([]);
    setResult(null);
    setA("");
    setB("");
  }, [history]);
  async function load() {
    setBusy(true);
    setError("");
    try {
      const all = await Promise.all(
        history.map((h) => api<Assessment>("/assessments/" + h.id)),
      );
      setOptions(
        all.flatMap((assessment) =>
          assessment.analyses.map((analysis) => ({ analysis, assessment })),
        ),
      );
      setOpened(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function compare() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(
        await api<Result>(
          "/comparisons?a=" +
            encodeURIComponent(a) +
            "&b=" +
            encodeURIComponent(b),
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function report() {
    setBusy(true);
    setError("");
    try {
      const target = options.find((o) => o.analysis.id === b)!;
      const response = await fetch(
        "/api/assessments/" +
          target.assessment.id +
          "/report?compare_to=" +
          encodeURIComponent(a) +
          "&analysis_id=" +
          encodeURIComponent(b),
      );
      if (!response.ok)
        throw new Error("Não foi possível gerar o relatório de evolução.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = "evolucao-" + target.assessment.id + ".pdf";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel comparison-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">ACOMPANHAMENTO</span>
          <h2>Comparar avaliações</h2>
        </div>
        {!opened && (
          <button
            className="secondary"
            disabled={history.length < 2 || busy}
            onClick={load}
          >
            {busy ? "Carregando…" : "Selecionar capturas"}
          </button>
        )}
      </div>
      {history.length < 2 && (
        <p className="muted">Disponível após duas avaliações deste paciente.</p>
      )}
      {opened && (
        <>
          <div className="form-grid">
            {(["A", "B"] as const).map((label) => (
              <label key={label}>
                Avaliação {label}
                <select
                  value={label === "A" ? a : b}
                  onChange={(e) => {
                    (label === "A" ? setA : setB)(e.target.value);
                    setResult(null);
                  }}
                >
                  <option value="">Selecione uma captura</option>
                  {options.map(({ analysis, assessment }) => (
                    <option key={analysis.id} value={analysis.id}>
                      {new Date(assessment.created_at).toLocaleString("pt-BR")}{" "}
                      · {analysis.media.view} · {assessment.protocol} ·{" "}
                      {assessment.status} · {analysis.id.slice(0, 6)}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          <button disabled={!a || !b || busy} onClick={compare}>
            Comparar medidas
          </button>
        </>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result &&
        (result.comparable ? (
          <>
            <p className="muted">{result.notice}</p>
            <button className="secondary" onClick={report} disabled={busy}>
              Baixar PDF de evolução
            </button>
            <div className="comparison-images">
              {[a, b].map((id, i) => {
                const item = options.find((o) => o.analysis.id === id)!;
                return (
                  <div key={i}>
                    <h3>
                      Avaliação {i ? "B" : "A"} · {item.assessment.status}
                    </h3>
                    {item.analysis.media.mime.startsWith("video/") ? (
                      <video
                        controls
                        src={"/api/media/" + item.analysis.media_id}
                      />
                    ) : (
                      <AnalysisImage analysis={item.analysis} />
                    )}
                  </div>
                );
              })}
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Medida</th>
                    <th>A</th>
                    <th>B</th>
                    <th>Diferença B − A</th>
                  </tr>
                </thead>
                <tbody>
                  {result.measurements.map((m) => (
                    <tr key={m.key}>
                      <td>
                        {m.label}
                        <small className="muted">
                          {m.statistic === "mean"
                            ? " · média temporal"
                            : " · instante"}
                        </small>
                      </td>
                      <td>{m.a?.toFixed(2) ?? "Indisponível"}</td>
                      <td>{m.b?.toFixed(2) ?? "Indisponível"}</td>
                      <td>
                        {m.difference !== null
                          ? `${m.difference > 0 ? "+" : ""}${m.difference.toFixed(2)} ${m.unit}`
                          : m.reason}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="warning">
            Comparação indisponível: diferenças em {result.reasons.join(", ")}.
            Selecione capturas compatíveis.
          </p>
        ))}
    </section>
  );
}
