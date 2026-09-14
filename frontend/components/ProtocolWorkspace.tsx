"use client";
import { useEffect, useRef, useState } from "react";
import { api, post, type Assessment } from "@/lib/api";
import {
  stepLabels,
  sideLabels,
  type ProtocolRun,
  type ProtocolStep,
  type ROMDefinition,
} from "@/lib/protocols";

export default function ProtocolWorkspace({
  assessment,
  onOpen,
  onChanged,
  onPending,
}: {
  assessment: Assessment;
  onOpen: (id: string) => void;
  onChanged: (a: Assessment) => void;
  onPending: (value: boolean) => void;
}) {
  const [run, setRun] = useState(assessment.assessment_protocol!),
    [index, setIndex] = useState(() =>
      Math.max(
        0,
        assessment.assessment_protocol!.steps.findIndex(
          (s) => !["completed", "skipped"].includes(s.state),
        ),
      ),
    ),
    [error, setError] = useState(""),
    [conclusion, setConclusion] = useState(assessment.conclusion),
    [busy, setBusy] = useState(false),
    [stepPending, setStepPending] = useState(false),
    [savedConclusion, setSavedConclusion] = useState(assessment.conclusion);
  const conclusionQueue = useRef<Promise<boolean>>(Promise.resolve(true));
  const conclusionValue = useRef(conclusion);
  conclusionValue.current = conclusion;
  const conclusionSaved = useRef(assessment.conclusion);
  const saveRef = useRef<() => Promise<boolean>>(async () => true);
  const done = assessment.status === "completed";
  const conclusionDirty = conclusion !== savedConclusion && !done;
  useEffect(() => {
    onPending(stepPending || conclusionDirty);
    return () => onPending(false);
  }, [stepPending, conclusionDirty, onPending]);
  useEffect(() => {
    if (!conclusionDirty) return;
    const timer = setTimeout(() => {
      void saveConclusion();
    }, 900);
    const leave = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", leave);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("beforeunload", leave);
    };
  }, [conclusion, conclusionDirty]);
  function saveConclusion(): Promise<boolean> {
    conclusionQueue.current = conclusionQueue.current.then(async () => {
      const value = conclusionValue.current;
      if (done || value === conclusionSaved.current) return true;
      try {
        await api(`/assessments/${assessment.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            conclusion: value,
            expected_conclusion: conclusionSaved.current,
          }),
        });
        conclusionSaved.current = value.trim();
        setSavedConclusion(value);
        return true;
      } catch (e) {
        setError((e as Error).message);
        return false;
      }
    });
    return conclusionQueue.current;
  }
  const count = run.steps.filter((s) =>
    ["completed", "skipped"].includes(s.state),
  ).length;
  async function move(next: number) {
    if (await saveRef.current()) setIndex(next);
  }
  async function report() {
    if (!(await saveRef.current())) return;
    if (!(await saveConclusion())) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/assessments/${assessment.id}/report`, {
        credentials: "include",
      });
      if (!response.ok) throw new Error("Não foi possível gerar o relatório.");
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `protocolo-${assessment.id}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function finish() {
    if (!(await saveRef.current())) return;
    if (!(await saveConclusion())) return;
    setBusy(true);
    setError("");
    try {
      await post(`/assessment-protocols/${assessment.id}/complete`, {
        conclusion,
      });
      onChanged(await api<Assessment>(`/assessments/${assessment.id}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="section-heading">
        <div>
          <span className="eyebrow">
            KINUA ASSESSMENT PROTOCOLS · {run.snapshot.version}
          </span>
          <h2>{run.snapshot.name}</h2>
          <p className="muted">
            {count} de {run.steps.length} etapas concluídas ou justificadas
          </p>
        </div>
        <button className="secondary" disabled={busy} onClick={report}>
          Baixar relatório do protocolo
        </button>
      </div>
      <div className="progress">
        <span style={{ width: (count / run.steps.length) * 100 + "%" }} />
      </div>
      <div className="protocol-workspace">
        <nav className="panel protocol-steps" aria-label="Etapas do protocolo">
          {run.steps.map((s, i) => (
            <button
              key={s.id}
              className={index === i ? "selected" : "ghost"}
              aria-current={index === i ? "step" : undefined}
              onClick={() => move(i)}
            >
              <span>{i + 1}</span>
              <span>
                <strong>{s.definition.name}</strong>
                <small>{stepLabels[s.state]}</small>
              </span>
              <span aria-hidden="true">
                {s.state === "completed"
                  ? "✓"
                  : s.state === "skipped"
                    ? "–"
                    : ""}
              </span>
            </button>
          ))}
        </nav>
        <StepEditor
          key={run.steps[index].id}
          step={run.steps[index]}
          assessmentId={assessment.id}
          done={done}
          onSaved={setRun}
          register={(fn) => {
            saveRef.current = fn;
          }}
          onPending={setStepPending}
          onOpen={async (id) => {
            if (await saveConclusion()) onOpen(id);
          }}
        />
      </div>
      <div className="button-row">
        <button
          className="secondary"
          disabled={index === 0}
          onClick={() => move(index - 1)}
        >
          Etapa anterior
        </button>
        <button
          disabled={index === run.steps.length - 1}
          onClick={() => move(index + 1)}
        >
          Próxima etapa
        </button>
      </div>
      <section className="panel protocol-conclusion">
        <h3>Conclusão do roteiro</h3>
        <label>
          Conclusão do protocolo
          <textarea
            value={conclusion}
            onChange={(e) => setConclusion(e.target.value)}
            disabled={done}
            maxLength={20000}
          />
        </label>
        <button onClick={finish} disabled={done || busy || !conclusion}>
          {done ? "Protocolo concluído" : "Concluir protocolo"}
        </button>
        <p className="small muted">
          A conclusão exige todas as etapas concluídas ou justificadas e a
          revisão das capturas vinculadas.
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </section>
    </>
  );
}

function StepEditor({
  step,
  assessmentId,
  done,
  onSaved,
  register,
  onPending,
  onOpen,
}: {
  step: ProtocolStep;
  assessmentId: string;
  done: boolean;
  onSaved: (r: ProtocolRun) => void;
  register: (fn: () => Promise<boolean>) => void;
  onPending: (v: boolean) => void;
  onOpen: (id: string) => void;
}) {
  const [state, setState] = useState(step.state),
    [result, setResult] = useState(step.result),
    [note, setNote] = useState(step.note),
    [message, setMessage] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [movements, setMovements] = useState<ROMDefinition[]>([]),
    [movement, setMovement] = useState(step.definition.movements?.[0] || ""),
    [side, setSide] = useState("right");
  const latest = useRef({ state, result, note }),
    saved = useRef(JSON.stringify(latest.current)),
    revision = useRef(step.revision),
    queue = useRef<Promise<boolean>>(Promise.resolve(true)),
    mounted = useRef(true);
  latest.current = { state, result, note };
  const dirty = JSON.stringify(latest.current) !== saved.current;
  function save(): Promise<boolean> {
    queue.current = queue.current.then(async () => {
      const value = { ...latest.current };
      if (done || JSON.stringify(value) === saved.current) return true;
      setBusy(true);
      setError("");
      try {
        const r = await api<ProtocolRun>(
          `/assessment-protocols/${assessmentId}/steps/${step.step_key}`,
          {
            method: "PATCH",
            body: JSON.stringify({ ...value, revision: revision.current }),
          },
        );
        revision.current = r.steps.find((s) => s.id === step.id)!.revision;
        saved.current = JSON.stringify(value);
        if (mounted.current) {
          onSaved(r);
          setMessage("Alterações salvas");
        }
        return true;
      } catch (e) {
        if (mounted.current) setError((e as Error).message);
        return false;
      } finally {
        if (mounted.current) setBusy(false);
      }
    });
    return queue.current;
  }
  register(save);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      onPending(false);
    };
  }, [onPending]);
  useEffect(() => {
    onPending(dirty);
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    if (!dirty)
      return () => window.removeEventListener("beforeunload", handler);
    setMessage("Alterações não salvas");
    const timer = setTimeout(() => {
      void save();
    }, 900);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("beforeunload", handler);
    };
  }, [state, result, note, dirty]);
  useEffect(() => {
    if (step.definition.kind === "rom")
      api<ROMDefinition[]>("/rom/movements")
        .then(setMovements)
        .catch((e) => setError(e.message));
  }, [step.definition.kind]);
  async function capture() {
    if (!(await save())) return;
    setBusy(true);
    setError("");
    try {
      const r = await post<{ assessment_id: string }>(
        `/assessment-protocols/${assessmentId}/steps/${step.step_key}/capture`,
        { side, movement: step.definition.kind === "rom" ? movement : null },
      );
      onOpen(r.assessment_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel step-editor">
      <span className="eyebrow">ETAPA DO PROTOCOLO</span>
      <h2>{step.definition.name}</h2>
      <p className="muted">{step.definition.instructions}</p>
      {!step.definition.available && (
        <p className="warning">
          Módulo fora desta rodada. Esta etapa não pode ser marcada como
          realizada.
        </p>
      )}
      {step.definition.kind === "manual" && (
        <p className="small muted">
          Registro textual do profissional. Não é uma análise automatizada.
        </p>
      )}
      {(step.definition.kind === "capture" ||
        step.definition.kind === "rom") && (
        <div className="info-box">
          {step.child ? (
            <>
              <p>
                Captura vinculada ·{" "}
                {step.child.status === "completed"
                  ? "Concluída"
                  : "Aguardando análise ou revisão"}
              </p>
              <button
                className="secondary"
                disabled={busy}
                onClick={async () => {
                  if (await save()) onOpen(step.child_assessment_id!);
                }}
              >
                Abrir captura e resultados
              </button>
            </>
          ) : (
            <>
              <div className="form-grid">
                {step.definition.kind === "rom" && (
                  <label>
                    Movimento ROM
                    <select
                      disabled={done || busy}
                      value={movement}
                      onChange={(e) => setMovement(e.target.value)}
                    >
                      {movements
                        .filter((m) =>
                          step.definition.movements?.includes(m.movement),
                        )
                        .map((m) => (
                          <option key={m.movement} value={m.movement}>
                            {m.name}
                          </option>
                        ))}
                    </select>
                  </label>
                )}
                <label>
                  Lado da captura
                  <select
                    disabled={done || busy}
                    value={side}
                    onChange={(e) => setSide(e.target.value)}
                  >
                    {Object.entries(sideLabels).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button disabled={done || busy} onClick={capture}>
                Iniciar captura da etapa
              </button>
            </>
          )}
        </div>
      )}
      <label>
        Estado da etapa
        <select
          value={state}
          disabled={done || busy}
          onChange={(e) => setState(e.target.value)}
        >
          <option value="not_started">Não iniciada</option>
          {step.definition.available && (
            <>
              <option value="in_progress">Em andamento</option>
              <option value="completed">Concluída</option>
            </>
          )}
          {step.definition.optional && (
            <option value="skipped">Ignorada com justificativa</option>
          )}
        </select>
      </label>
      <label>
        Resultado da etapa
        <textarea
          value={result}
          onChange={(e) => setResult(e.target.value)}
          disabled={done || !step.definition.available}
          maxLength={20000}
        />
      </label>
      <label>
        Observação / justificativa
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          disabled={done}
          maxLength={10000}
        />
      </label>
      <div className="button-row">
        <button disabled={done || busy} onClick={() => save()}>
          Salvar etapa
        </button>
        <span className="small muted" role="status">
          {busy ? "Salvando…" : message || "Etapa carregada"}
        </span>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}{" "}
          <button className="text-button" onClick={() => save()}>
            Tentar salvar novamente
          </button>
        </p>
      )}
      {step.started_at && (
        <p className="small muted">
          Iniciada em {new Date(step.started_at).toLocaleString("pt-BR")}
        </p>
      )}
      {step.completed_at && (
        <p className="small muted">
          Concluída em {new Date(step.completed_at).toLocaleString("pt-BR")}
        </p>
      )}
    </section>
  );
}
