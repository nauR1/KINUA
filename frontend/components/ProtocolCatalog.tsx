"use client";
import { useEffect, useState } from "react";
import { ArrowUpRight, ClipboardList } from "lucide-react";
import { api, post, type Patient } from "@/lib/api";
import type { ProtocolCatalog as Catalog } from "@/lib/protocols";
import EmptyState from "./ui/EmptyState";

export default function ProtocolCatalog({
  patients,
  patientId,
  onOpen,
}: {
  patients: Patient[];
  patientId?: string;
  onOpen: (id: string) => void;
}) {
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [category, setCategory] = useState(""),
    [selectedPatient, setPatient] = useState(
      patientId || patients[0]?.id || "",
    ),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [pending, setPending] = useState<
      {
        assessment: { id: string; patient_id: string };
        name: string;
        version: string;
        completed_steps: number;
        total_steps: number;
      }[]
    >([]);
  useEffect(() => {
    let gone = false;
    Promise.all([
      api<Catalog>("/protocols"),
      api<typeof pending>("/protocols/pending"),
    ])
      .then(([c, p]) => {
        if (!gone) {
          setCatalog(c);
          setPending(p);
        }
      })
      .catch((e) => {
        if (!gone) setError(e.message);
      });
    return () => {
      gone = true;
    };
  }, []);
  async function start(version_id: string) {
    setBusy(true);
    setError("");
    try {
      const r = await post<{ assessment_id: string }>("/assessment-protocols", {
        patient_id: selectedPatient,
        version_id,
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
        <span className="eyebrow">KINUA ASSESSMENT PROTOCOLS</span>
        <h2>Um roteiro para cada avaliação</h2>
        <p className="muted">
          Escolha a finalidade, registre as etapas e retome de onde parou. A
          condução permanece com o profissional.
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="form-grid">
          <label>
            Paciente do protocolo
            <select
              value={selectedPatient}
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
            Categoria
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">Todas as regiões</option>
              {catalog?.categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!catalog && !error && <p role="status">Carregando protocolos…</p>}
        <div className="protocol-cards">
          {catalog?.versions
            .filter((v) => !category || v.protocol.category_id === category)
            .map((v) => (
              <article className="protocol-card" key={v.id}>
                <ClipboardList size={22} />
                <h3>{v.protocol.name}</h3>
                <p className="muted small">
                  {v.definition.steps.length} etapas · versão {v.version}
                </p>
                <p className="small">
                  {v.definition.steps.filter((s) => s.available).length} etapas
                  disponíveis nesta rodada.
                </p>
                <button
                  disabled={busy || !selectedPatient}
                  onClick={() => start(v.id)}
                >
                  Iniciar protocolo <ArrowUpRight size={15} />
                </button>
              </article>
            ))}
        </div>
        {!patients.length && (
          <p className="info-box">
            Cadastre um paciente para iniciar um protocolo.
          </p>
        )}
      </section>
      <section className="panel">
        <h2>Protocolos em andamento</h2>
        {pending.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Paciente</th>
                  <th>Protocolo</th>
                  <th>Progresso</th>
                  <th>Retomar</th>
                </tr>
              </thead>
              <tbody>
                {pending.map((p) => (
                  <tr key={p.assessment.id}>
                    <td>
                      {
                        patients.find((x) => x.id === p.assessment.patient_id)
                          ?.name
                      }
                    </td>
                    <td>
                      {p.name} · {p.version}
                    </td>
                    <td>
                      {p.completed_steps}/{p.total_steps}
                    </td>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => onOpen(p.assessment.id)}
                      >
                        Continuar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhum roteiro pendente"
            description="Os protocolos iniciados poderão ser retomados aqui."
          />
        )}
      </section>
    </>
  );
}
