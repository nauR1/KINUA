"use client";
import { useState } from "react";
import { Activity, ArrowUpRight, ShieldCheck } from "lucide-react";
import { api, post } from "@/lib/api";
type User = { id: string; name: string; email: string; role: string };
export default function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      await post("/auth/login", {
        email: f.get("email"),
        password: f.get("password"),
      });
      onLogin(await api<User>("/auth/me"));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="brand">
          <span>
            <Activity size={26} />
          </span>
          biometria.
        </div>
        <div>
          <span className="eyebrow">AVALIAÇÃO CORPORAL ASSISTIDA</span>
          <h1>
            Observe com precisão.
            <br />
            Interprete com contexto.
          </h1>
          <p>
            Captura, medidas e revisão profissional
            <br />
            em um único espaço clínico.
          </p>
          <div className="login-lines">
            <span>01 Capturar</span>
            <span>02 Medir</span>
            <span>03 Revisar</span>
          </div>
        </div>
        <p className="small">
          Tecnologia de apoio. Julgamento do fisioterapeuta.
        </p>
      </section>
      <section className="login-form">
        <div>
          <span className="eyebrow">ACESSO PROFISSIONAL</span>
          <h2>Bem-vindo à sua clínica</h2>
          <p className="muted">Entre com sua conta para continuar.</p>
          <form onSubmit={submit}>
            <label>
              E-mail
              <input
                name="email"
                type="email"
                required
                autoComplete="username"
                placeholder="seu@email.com"
              />
            </label>
            <label>
              Senha
              <input
                name="password"
                type="password"
                required
                autoComplete="current-password"
              />
            </label>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="full" disabled={busy}>
              {busy ? "Entrando…" : "Entrar na plataforma"}
              <ArrowUpRight size={17} />
            </button>
          </form>
          <p className="login-help">
            <ShieldCheck size={18} />
            Acesso restrito aos profissionais da clínica.
          </p>
        </div>
      </section>
    </main>
  );
}
