"use client";
import { ArrowUpRight } from "lucide-react";
import EmptyState from "./ui/EmptyState";
import type { Patient, Assessment } from "@/lib/api";
const statusLabels: Record<string, string> = {
  draft: "Em preparação",
  review: "A revisar",
  completed: "Concluída",
};
const kindLabels: Record<string, string> = {
  postural: "Postural",
  functional: "Funcional",
  movement: "Movimento",
  sports: "Esportiva",
  followup: "Acompanhamento",
};
export default function AssessmentTable({
  list,
  patients,
  onOpen,
}: {
  list: Assessment[];
  patients: Patient[];
  onOpen: (id: string) => void;
}) {
  if (!list.length)
    return (
      <EmptyState description="Inicie uma avaliação para registrar a primeira captura." />
    );
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Paciente / avaliação</th>
            <th>Data</th>
            <th>Estado</th>
            <th>Abrir</th>
          </tr>
        </thead>
        <tbody>
          {list.map((a) => (
            <tr key={a.id}>
              <td>
                <strong>
                  {patients.find((p) => p.id === a.patient_id)?.name ||
                    "Paciente"}
                </strong>
                <small>{kindLabels[a.kind]}</small>
              </td>
              <td>{new Date(a.created_at).toLocaleDateString("pt-BR")}</td>
              <td>
                <span
                  className={
                    "badge " + (a.status === "completed" ? "positive" : "")
                  }
                >
                  {statusLabels[a.status]}
                </span>
              </td>
              <td>
                <button
                  className="icon-button"
                  aria-label={"Abrir avaliação " + a.id}
                  onClick={() => onOpen(a.id)}
                >
                  <ArrowUpRight size={18} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
