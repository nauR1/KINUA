"use client";
import { useCallback, useEffect, useState } from "react";
import { api, post } from "@/lib/api";
import KinuaLogo from "./brand/KinuaLogo";
type Access = {
  expires_at: string | null;
  allowed: boolean;
  code: string | null;
  days_remaining: number | null;
};
type Clinic = {
  id: string;
  name: string;
  is_active: boolean;
  plan_code: string;
  subscription_status: string;
  access_starts_at: string | null;
  access_expires_at: string | null;
  max_users: number | null;
  access: Access;
};
type Member = {
  id: string;
  name: string;
  email: string;
  role: string;
  clinic_id: string;
  is_active: boolean;
  access_expires_at: string | null;
  last_login_at: string | null;
  access: Access;
};
const planLabels: Record<string, string> = {
  trial: "Teste",
  monthly: "Mensal",
  quarterly: "Trimestral",
  annual: "Anual",
  custom: "Personalizado",
  lifetime: "Vitalício",
};
const roleLabels: Record<string, string> = {
  platform_admin: "Administrador global",
  admin: "Administrador da clínica",
  physiotherapist: "Fisioterapeuta",
};
const statusLabels: Record<string, string> = {
  active: "Ativo",
  trial: "Teste",
  suspended: "Suspenso",
  expired: "Expirado",
  cancelled: "Cancelado",
};
const dateLabel = (v: string | null) =>
  v ? new Date(v).toLocaleString("pt-BR") : "Sem expiração";
const inputDate = (v: string | null) =>
  v
    ? new Date(new Date(v).getTime() - new Date(v).getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16)
    : "";
const iso = (v: FormDataEntryValue | null) =>
  v ? new Date(String(v)).toISOString() : null;
const patch = (path: string, body: unknown) =>
  api(path, { method: "PATCH", body: JSON.stringify(body) });
export function AccessBadge({
  access,
  trial = false,
  unlimited = false,
}: {
  access: Access;
  trial?: boolean;
  unlimited?: boolean;
}) {
  let label =
    access.code === "subscription_cancelled"
      ? "CANCELADO"
      : access.code?.includes("expired")
        ? "EXPIRADO"
        : !access.allowed
          ? "SUSPENSO"
          : trial
            ? "TESTE"
            : unlimited
              ? "ILIMITADO"
              : access.days_remaining !== null && access.days_remaining <= 7
                ? "VENCE EM BREVE"
                : "ATIVO";
  return (
    <span className={"access-badge " + (!access.allowed ? "blocked" : "")}>
      {label}
    </span>
  );
}
export function UserAccess({
  platform = false,
  clinics = [],
}: {
  platform?: boolean;
  clinics?: Clinic[];
}) {
  const base = platform ? "/platform/users" : "/admin/users";
  const [members, setMembers] = useState<Member[]>([]),
    [selected, setSelected] = useState<Member | null>(null),
    [q, setQ] = useState(""),
    [clinic, setClinic] = useState(""),
    [status, setStatus] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const load = useCallback(async () => {
    setBusy(true);
    try {
      setMembers(
        await api<Member[]>(
          base + "?" + new URLSearchParams({ q, clinic_id: clinic, status }),
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [base, q, clinic, status]);
  useEffect(() => {
    const timer = setTimeout(() => void load(), 200);
    return () => clearTimeout(timer);
  }, [load]);
  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (selected) {
        if (
          f.get("is_active") === "false" &&
          !window.confirm("Suspender este usuário e encerrar suas sessões?")
        )
          return;
        await patch(base + "/" + selected.id, {
          role: f.get("role"),
          is_active: f.get("is_active") === "true",
          access_expires_at: iso(f.get("access_expires_at")),
          suspension_reason: f.get("suspension_reason") || null,
        });
      } else {
        await post(base, {
          name: f.get("name"),
          email: f.get("email"),
          password: f.get("password"),
          role: f.get("role"),
          ...(platform ? { clinic_id: f.get("clinic_id") } : {}),
        });
      }
      setSelected(null);
      form.reset();
      setMessage("Acesso salvo.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>Usuários e acessos</h2>
      <div className="form-grid">
        <label>
          Buscar nome ou e-mail
          <input value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        {platform && (
          <label>
            Filtrar clínica
            <select value={clinic} onChange={(e) => setClinic(e.target.value)}>
              <option value="">Todas as clínicas</option>
              {clinics.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Filtrar status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            <option value="active">Ativos</option>
            <option value="account_disabled">Usuários suspensos</option>
            <option value="user_access_expired">Expiração individual</option>
            <option value="subscription_expired">Assinatura expirada</option>
            <option value="clinic_suspended">Clínica suspensa</option>
          </select>
        </label>
      </div>
      {busy && <p role="status">Carregando…</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Usuário</th>
              <th>Permissão</th>
              <th>Acesso</th>
              <th>Último login</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            {members.map((u) => (
              <tr key={u.id}>
                <td>
                  <strong>{u.name}</strong>
                  <br />
                  {u.email}
                </td>
                <td>{roleLabels[u.role] || u.role}</td>
                <td>
                  <AccessBadge access={u.access} />
                  <br />
                  {dateLabel(u.access.expires_at)}
                </td>
                <td>
                  {u.last_login_at
                    ? dateLabel(u.last_login_at)
                    : "Nunca acessou"}
                </td>
                <td>
                  <button className="secondary" onClick={() => setSelected(u)}>
                    Gerenciar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!busy && !members.length && <p>Nenhum usuário encontrado.</p>}
      <h3>
        {selected ? "Editar acesso de " + selected.name : "Cadastrar usuário"}
      </h3>
      <form key={selected?.id || "new"} onSubmit={save}>
        <div className="form-grid">
          {!selected && (
            <>
              <label>
                Nome
                <input name="name" required minLength={2} />
              </label>
              <label>
                E-mail
                <input name="email" type="email" required />
              </label>
              <label>
                Senha inicial
                <input
                  name="password"
                  type="password"
                  minLength={12}
                  maxLength={128}
                  autoComplete="new-password"
                  required
                />
              </label>
              {platform && (
                <label>
                  Clínica
                  <select name="clinic_id" required>
                    {clinics.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </>
          )}
          <label>
            Permissão
            <select
              name="role"
              defaultValue={selected?.role || "physiotherapist"}
            >
              <option value="physiotherapist">Fisioterapeuta</option>
              <option value="admin">Administrador da clínica</option>
              {platform && (
                <option value="platform_admin">Administrador global</option>
              )}
            </select>
          </label>
          {selected && (
            <>
              <label>
                Estado
                <select
                  name="is_active"
                  defaultValue={String(selected.is_active)}
                >
                  <option value="true">Ativo</option>
                  <option value="false">Suspenso</option>
                </select>
              </label>
              <label>
                Expiração individual (vazio segue clínica)
                <input
                  name="access_expires_at"
                  type="datetime-local"
                  defaultValue={inputDate(selected.access_expires_at)}
                />
              </label>
              <label>
                Motivo da suspensão
                <input name="suspension_reason" maxLength={2000} />
              </label>
            </>
          )}
        </div>
        <button disabled={busy}>
          {selected ? "Salvar acesso" : "Cadastrar usuário"}
        </button>
        {selected && (
          <button
            className="secondary"
            type="button"
            onClick={() => setSelected(null)}
          >
            Cancelar edição
          </button>
        )}
      </form>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <p role="status" className="success">
        {message}
      </p>
    </section>
  );
}
export default function PlatformAdmin({
  onLogout,
}: {
  onLogout: () => Promise<void>;
}) {
  const [tab, setTab] = useState("Visão geral"),
    [clinics, setClinics] = useState<Clinic[]>([]),
    [stats, setStats] = useState<Record<string, number>>({}),
    [logs, setLogs] = useState<
      {
        id: string;
        action: string;
        actor_id: string;
        resource_id: string;
        created_at: string;
        changes: unknown;
      }[]
    >([]),
    [selected, setSelected] = useState<Clinic | null>(null),
    [q, setQ] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [c, s, a] = await Promise.all([
        api<Clinic[]>("/platform/clinics"),
        api<Record<string, number>>("/platform/dashboard"),
        api<typeof logs>("/platform/audit"),
      ]);
      setClinics(c);
      setStats(s);
      setLogs(a);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      name: f.get("name"),
      plan_code: f.get("plan_code"),
      subscription_status: f.get("subscription_status"),
      is_active: f.get("subscription_status") !== "suspended",
      access_starts_at: iso(f.get("access_starts_at")),
      access_expires_at: iso(f.get("access_expires_at")),
      max_users: f.get("max_users") ? Number(f.get("max_users")) : null,
      suspension_reason: f.get("suspension_reason") || null,
    };
    if (
      body.subscription_status === "suspended" &&
      !window.confirm("Suspender esta clínica e encerrar as sessões da equipe?")
    )
      return;
    await mutate(async () => {
      if (selected) await patch("/platform/clinics/" + selected.id, body);
      else await post("/platform/clinics", body);
      setSelected(null);
    });
  }
  async function mutate(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
      setMessage("Alteração salva.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const labels: Record<string, string> = {
    clinics: "Clínicas",
    active_clinics: "Clínicas ativas",
    expired_subscriptions: "Assinaturas expiradas",
    expiring_7: "Vencem em 7 dias",
    expiring_30: "Vencem em 30 dias",
    active_users: "Usuários ativos",
    suspended_users: "Usuários suspensos",
    expired_users: "Usuários expirados",
  };
  return (
    <main className="platform-shell">
      <header className="platform-header">
        <KinuaLogo size={175} />
        <div>
          <span className="eyebrow">ADMINISTRAÇÃO DA PLATAFORMA</span>
          <h1>Gestão de acessos</h1>
        </div>
        <button
          className="secondary"
          onClick={() => void onLogout().catch((e) => setError(e.message))}
        >
          Sair
        </button>
      </header>
      <nav className="platform-tabs" aria-label="Administração">
        {["Visão geral", "Clínicas", "Usuários e acessos", "Auditoria"].map(
          (t) => (
            <button
              aria-current={tab === t ? "page" : undefined}
              className={tab === t ? "" : "secondary"}
              key={t}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ),
        )}
      </nav>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <p role="status">{busy ? "Carregando…" : message}</p>
      {tab === "Visão geral" && (
        <>
          <div className="platform-metrics">
            {Object.entries(labels).map(([k, v]) => (
              <article className="panel" key={k}>
                <span>{v}</span>
                <strong>{stats[k] ?? "—"}</strong>
              </article>
            ))}
          </div>
          <section className="panel">
            <h2>Controle comercial, responsabilidade clínica preservada</h2>
            <p>
              Gerencie clínicas, planos e usuários. A administração global não
              concede acesso a prontuários.
            </p>
          </section>
        </>
      )}
      {tab === "Clínicas" && (
        <>
          <section className="panel">
            <h2>Clínicas</h2>
            <label>
              Buscar clínica
              <input value={q} onChange={(e) => setQ(e.target.value)} />
            </label>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Clínica</th>
                    <th>Plano</th>
                    <th>Status</th>
                    <th>Vencimento</th>
                    <th>Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {clinics
                    .filter((c) =>
                      c.name.toLowerCase().includes(q.toLowerCase()),
                    )
                    .map((c) => (
                      <tr key={c.id}>
                        <td>{c.name}</td>
                        <td>{planLabels[c.plan_code] || c.plan_code}</td>
                        <td>
                          <AccessBadge
                            access={c.access}
                            trial={c.subscription_status === "trial"}
                            unlimited={!c.access_expires_at}
                          />
                        </td>
                        <td>{dateLabel(c.access_expires_at)}</td>
                        <td>
                          <button
                            className="secondary"
                            onClick={() => setSelected(c)}
                          >
                            Gerenciar clínica
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
            {!clinics.length && <p>Nenhuma clínica cadastrada.</p>}
          </section>
          <section className="panel">
            <h2>{selected ? "Editar clínica" : "Nova clínica"}</h2>
            {selected && (
              <div className="platform-tabs">
                <button
                  disabled={busy}
                  onClick={() =>
                    void mutate(async () => {
                      const c = await post<Clinic>(
                        "/platform/clinics/" + selected.id + "/extend",
                        { days: 7, trial: true },
                      );
                      setSelected(c);
                    })
                  }
                >
                  Teste 7 dias
                </button>
                {[7, 30, 90, 365].map((days) => (
                  <button
                    className="secondary"
                    disabled={busy}
                    key={days}
                    onClick={() =>
                      void mutate(async () => {
                        const c = await post<Clinic>(
                          "/platform/clinics/" + selected.id + "/extend",
                          { days },
                        );
                        setSelected(c);
                      })
                    }
                  >
                    +{days} dias
                  </button>
                ))}
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    void mutate(async () => {
                      await patch("/platform/clinics/" + selected.id, {
                        access_expires_at: null,
                        access_starts_at: null,
                        subscription_status: "active",
                        is_active: true,
                        plan_code: "lifetime",
                      });
                      setSelected(null);
                    })
                  }
                >
                  Acesso ilimitado
                </button>
              </div>
            )}
            <form
              key={selected ? selected.id + selected.access_expires_at : "new"}
              onSubmit={save}
            >
              <div className="form-grid">
                <label>
                  Nome da clínica
                  <input
                    name="name"
                    defaultValue={selected?.name}
                    required
                    minLength={2}
                  />
                </label>
                <label>
                  Plano
                  <select
                    name="plan_code"
                    defaultValue={selected?.plan_code || "trial"}
                  >
                    {[
                      "trial",
                      "monthly",
                      "quarterly",
                      "annual",
                      "custom",
                      "lifetime",
                    ].map((v) => (
                      <option key={v} value={v}>
                        {planLabels[v] || statusLabels[v] || v}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Status da assinatura
                  <select
                    name="subscription_status"
                    defaultValue={selected?.subscription_status || "active"}
                  >
                    {[
                      "active",
                      "trial",
                      "suspended",
                      "expired",
                      "cancelled",
                    ].map((v) => (
                      <option key={v} value={v}>
                        {planLabels[v] || statusLabels[v] || v}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Início
                  <input
                    type="datetime-local"
                    name="access_starts_at"
                    defaultValue={inputDate(selected?.access_starts_at || null)}
                  />
                </label>
                <label>
                  Vencimento personalizado (vazio = ilimitado)
                  <input
                    type="datetime-local"
                    name="access_expires_at"
                    defaultValue={inputDate(
                      selected?.access_expires_at || null,
                    )}
                  />
                </label>
                <label>
                  Limite de usuários ativos
                  <input
                    name="max_users"
                    type="number"
                    min={1}
                    max={100000}
                    defaultValue={selected?.max_users ?? ""}
                  />
                </label>
                <label>
                  Motivo da suspensão
                  <input name="suspension_reason" maxLength={2000} />
                </label>
              </div>
              <button disabled={busy}>Salvar clínica</button>
              {selected && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setSelected(null)}
                >
                  Nova clínica
                </button>
              )}
            </form>
          </section>
        </>
      )}
      {tab === "Usuários e acessos" && (
        <UserAccess platform clinics={clinics} />
      )}
      {tab === "Auditoria" && (
        <section className="panel">
          <h2>Auditoria administrativa</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Ação</th>
                  <th>Ator / alvo</th>
                  <th>Alterações</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((a) => (
                  <tr key={a.id}>
                    <td>{dateLabel(a.created_at)}</td>
                    <td>{a.action}</td>
                    <td>
                      {a.actor_id}
                      <br />
                      {a.resource_id}
                    </td>
                    <td>
                      <code>{JSON.stringify(a.changes)}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!logs.length && <p>Nenhuma alteração registrada.</p>}
        </section>
      )}
    </main>
  );
}
