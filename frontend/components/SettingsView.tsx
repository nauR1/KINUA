"use client";
import { useState, useEffect } from "react";
import { UserAccess } from "./PlatformAdmin";
import { api } from "@/lib/api";
type User = { id: string; name: string; email: string; role: string };
export default function SettingsView({ user }: { user: User }) {
  const [audits, setAudits] = useState<
      { id: string; action: string; created_at: string; resource_id: string }[]
    >([]),
    [error, setError] = useState("");
  async function load() {
    if (user.role === "admin") {
      try {
        setAudits(await api<typeof audits>("/admin/audit"));
      } catch (e) {
        setError((e as Error).message);
      }
    }
  }
  useEffect(() => {
    void load();
  }, []);
  return (
    <>
      <section className="panel">
        <span className="eyebrow">PARÂMETROS DA ANÁLISE</span>
        <h2>Regras transparentes</h2>
        <p>
          As medidas são geométricas. Nenhum limiar clínico está ativo nesta
          versão.
        </p>
        <div className="info-box">
          <strong>Referências pendentes de validação</strong>
          <p>
            As regras experimentais não geram associações clínicas. Alterações
            exigem revisão do arquivo de regras, versionamento e testes.
          </p>
        </div>
        <p className="muted">
          Visibilidade mínima por landmark: 0,65 · Critério técnico de
          engenharia, sem valor diagnóstico.
        </p>
      </section>
      {user.role === "admin" && (
        <>
          <UserAccess />
          <section className="panel">
            <h2>Auditoria recente</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Ação</th>
                    <th>Recurso</th>
                  </tr>
                </thead>
                <tbody>
                  {audits.map((a) => (
                    <tr key={a.id}>
                      <td>{new Date(a.created_at).toLocaleString("pt-BR")}</td>
                      <td>{a.action}</td>
                      <td className="small">{a.resource_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
