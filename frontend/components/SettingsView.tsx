"use client";
import { useState, useEffect } from "react";
import { api, post } from "@/lib/api";
type User = { id: string; name: string; email: string; role: string };
export default function SettingsView({ user }: { user: User }) {
  const [audits, setAudits] = useState<
      { id: string; action: string; created_at: string; resource_id: string }[]
    >([]),
    [members, setMembers] = useState<User[]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function load() {
    if (user.role === "admin") {
      try {
        const [a, m] = await Promise.all([
          api<typeof audits>("/admin/audit"),
          api<User[]>("/admin/users"),
        ]);
        setAudits(a);
        setMembers(m);
      } catch (e) {
        setError((e as Error).message);
      }
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    try {
      await post("/admin/users", Object.fromEntries(new FormData(form)));
      form.reset();
      setMessage("Profissional cadastrado.");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
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
          <section className="panel form-panel">
            <h2>Equipe da clínica</h2>
            {members.map((m) => (
              <p key={m.id}>
                <strong>{m.name}</strong> · {m.email} ·{" "}
                {m.role === "admin" ? "Administrador" : "Fisioterapeuta"}
              </p>
            ))}
            <h3>Cadastrar profissional</h3>
            <form onSubmit={create}>
              <div className="form-grid">
                <label>
                  Nome
                  <input name="name" required minLength={2} />
                </label>
                <label>
                  E-mail
                  <input type="email" name="email" required />
                </label>
                <label>
                  Senha inicial
                  <input
                    name="password"
                    type="password"
                    required
                    minLength={12}
                    autoComplete="new-password"
                  />
                </label>
                <label>
                  Permissão
                  <select name="role">
                    <option value="physiotherapist">Fisioterapeuta</option>
                    <option value="admin">Administrador</option>
                  </select>
                </label>
              </div>
              <button disabled={busy}>Cadastrar profissional</button>
            </form>
            <p role="status" className="success">
              {message}
            </p>
          </section>
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
