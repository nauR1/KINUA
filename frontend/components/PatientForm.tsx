"use client";
import { useState } from "react";
import { api, post, type Patient } from "@/lib/api";
export default function PatientForm({
  onSaved,
  onCancel,
  patient,
}: {
  patient?: Patient | null;
  onSaved: (p: Patient) => void;
  onCancel: () => void;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const data = Object.fromEntries(form) as Record<string, unknown>;
    data.height_cm = form.get("height_cm")
      ? Number(form.get("height_cm"))
      : null;
    data.weight_kg = form.get("weight_kg")
      ? Number(form.get("weight_kg"))
      : null;
    try {
      onSaved(
        patient
          ? await api<Patient>("/patients/" + patient.id, {
              method: "PATCH",
              body: JSON.stringify({
                ...data,
                expected_revision: patient.revision,
              }),
            })
          : await post<Patient>("/patients", data),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel form-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">PRONTUÁRIO</span>
          <h2>{patient ? "Editar paciente" : "Novo paciente"}</h2>
        </div>
        <button className="ghost" onClick={onCancel} disabled={busy}>
          Cancelar
        </button>
      </div>
      <form onSubmit={submit}>
        <div className="form-grid">
          <label className="span2">
            Nome completo
            <input
              defaultValue={patient?.name ?? ""}
              name="name"
              required
              minLength={2}
              maxLength={160}
              autoComplete="name"
            />
          </label>
          <label>
            Data de nascimento
            <input
              defaultValue={patient?.birth_date ?? ""}
              name="birth_date"
              type="date"
              required
              max={new Date().toISOString().slice(0, 10)}
            />
          </label>
          <label>
            Dominância
            <select
              defaultValue={patient?.details.dominance ?? ""}
              name="dominance"
            >
              <option value="">Não informado</option>
              <option value="right">Direita</option>
              <option value="left">Esquerda</option>
              <option value="both">Ambidestra</option>
            </select>
          </label>
          <label>
            Telefone
            <input
              defaultValue={patient?.details.phone ?? ""}
              name="phone"
              type="tel"
              maxLength={40}
            />
          </label>
          <label>
            E-mail
            <input
              defaultValue={patient?.details.email ?? ""}
              name="email"
              type="email"
              maxLength={254}
            />
          </label>
          <label>
            Profissão
            <input
              defaultValue={patient?.details.occupation ?? ""}
              name="occupation"
              maxLength={160}
            />
          </label>
          <label>
            Prática / modalidade esportiva
            <input
              defaultValue={patient?.details.sport ?? ""}
              name="sport"
              maxLength={160}
            />
          </label>
          <label>
            Altura (cm)
            <input
              defaultValue={patient?.details.height_cm ?? ""}
              name="height_cm"
              type="number"
              min={30}
              max={260}
              step="0.1"
            />
          </label>
          <label>
            Peso (kg)
            <input
              defaultValue={patient?.details.weight_kg ?? ""}
              name="weight_kg"
              type="number"
              min={1}
              max={500}
              step="0.1"
            />
          </label>
          <label className="span2">
            Sexo biológico · preencher somente quando necessário à avaliação
            <select
              defaultValue={patient?.details.biological_sex ?? ""}
              name="biological_sex"
            >
              <option value="">Não coletado</option>
              <option value="female">Feminino</option>
              <option value="male">Masculino</option>
              <option value="intersex">Intersexo</option>
            </select>
          </label>
          <label className="span2">
            Queixa principal
            <textarea
              defaultValue={patient?.details.complaint ?? ""}
              name="complaint"
              maxLength={10000}
            />
          </label>
          <label className="span2">
            Histórico relevante
            <textarea
              defaultValue={patient?.details.history ?? ""}
              name="history"
              maxLength={10000}
            />
          </label>
          <label className="span2">
            Observações
            <textarea
              defaultValue={patient?.details.notes ?? ""}
              name="notes"
              maxLength={10000}
            />
          </label>
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="form-footer">
          <span className="muted">
            Dados visíveis apenas para profissionais desta clínica.
          </span>
          <button disabled={busy}>
            {busy
              ? "Salvando…"
              : patient
                ? "Salvar paciente"
                : "Cadastrar paciente"}
          </button>
        </div>
      </form>
    </section>
  );
}
