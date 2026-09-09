"use client";
import { useEffect, useState } from "react";
import {
  Activity,
  LayoutDashboard,
  Users,
  ClipboardList,
  Settings,
  LogOut,
  Plus,
  ArrowUpRight,
  Search,
  ShieldCheck,
  ChevronLeft,
  Sun,
  Moon,
  Camera,
} from "lucide-react";
import { api, post, type Patient, type Assessment } from "@/lib/api";
import PatientForm from "@/components/PatientForm";
import Capture from "@/components/Capture";
import Login from "@/components/Login";
import AssessmentTable from "@/components/AssessmentTable";
import SettingsView from "@/components/SettingsView";
import Results from "@/components/Results";
type User = { id: string; name: string; email: string; role: string };
type Dashboard = {
  patients: number;
  assessments: number;
  pending: number;
  last_30_days: number;
  recent: Assessment[];
};
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

export default function Home() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [section, setSection] = useState("dashboard"),
    [patients, setPatients] = useState<Patient[]>([]),
    [dashboard, setDashboard] = useState<Dashboard | null>(null),
    [patient, setPatient] = useState<Patient | null>(null),
    [history, setHistory] = useState<Assessment[]>([]),
    [assessment, setAssessment] = useState<Assessment | null>(null),
    [tab, setTab] = useState("capture"),
    [adding, setAdding] = useState(false),
    [query, setQuery] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [newAssessment, setNewAssessment] = useState(false),
    [dark, setDark] = useState(false);
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  async function refresh() {
    try {
      const [p, d] = await Promise.all([
        api<Patient[]>("/patients"),
        api<Dashboard>("/dashboard"),
      ]);
      setPatients(p);
      setDashboard(d);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    if (user) void refresh();
  }, [user]);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  async function choosePatient(p: Patient) {
    setPatient(p);
    setAssessment(null);
    setNewAssessment(false);
    setAdding(false);
    setSection("patients");
    setError("");
    try {
      setHistory(await api<Assessment[]>("/patients/" + p.id + "/assessments"));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function openAssessment(id: string) {
    setBusy(true);
    setError("");
    try {
      const a = await api<Assessment>("/assessments/" + id);
      setAssessment(a);
      setPatient(patients.find((p) => p.id === a.patient_id) || null);
      setTab(a.analyses.length ? "results" : "capture");
      setSection("analysis");
      setNewAssessment(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function navigate(next: string) {
    setSection(next);
    setAssessment(null);
    setPatient(null);
    setAdding(false);
    setNewAssessment(false);
    setError("");
  }
  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(event.currentTarget);
    try {
      const a = await post<Assessment>("/assessments", {
        patient_id: f.get("patient_id"),
        kind: f.get("kind"),
        mode: f.get("mode"),
      });
      await refresh();
      await openAssessment(a.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await post("/auth/logout", {});
      setUser(null);
      setPatients([]);
      setDashboard(null);
      setAssessment(null);
      setPatient(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (loading)
    return (
      <main className="loading-screen">
        <Activity className="spin" />
        <p>Carregando sua clínica…</p>
      </main>
    );
  if (!user) return <Login onLogin={setUser} />;
  const filtered = patients.filter((p) =>
    p.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  );
  const title =
    section === "dashboard"
      ? "Visão geral"
      : section === "patients"
        ? "Pacientes"
        : section === "analysis"
          ? "Avaliação corporal"
          : section === "settings"
            ? "Configurações"
            : "Avaliações";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Biometria, início">
          <span>
            <Activity size={24} />
          </span>
          biometria<span className="brand-dot">.</span>
        </a>
        <div className="workspace-label">ESPAÇO CLÍNICO</div>
        <nav aria-label="Navegação principal">
          {[
            ["dashboard", "Visão geral", LayoutDashboard],
            ["patients", "Pacientes", Users],
            ["assessments", "Avaliações", ClipboardList],
            ["settings", "Configurações", Settings],
          ].map(([key, label, Icon]) => {
            const I = Icon as typeof Activity;
            return (
              <button
                key={key as string}
                className={section === key ? "active" : ""}
                onClick={() => navigate(key as string)}
              >
                <I size={19} />
                {label as string}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="clinical-note">
            <ShieldCheck size={19} />
            <p>
              Apoio à avaliação.
              <br />
              <strong>Decisão profissional.</strong>
            </p>
          </div>
          <button className="theme-toggle" onClick={() => setDark(!dark)}>
            {dark ? <Sun size={18} /> : <Moon size={18} />}Tema{" "}
            {dark ? "claro" : "escuro"}
          </button>
          <div className="user-block">
            <span className="avatar">
              {user.name.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <strong>{user.name}</strong>
              <small>
                {user.role === "admin" ? "Administrador" : "Fisioterapeuta"}
              </small>
            </div>
            <button className="icon-button" aria-label="Sair" onClick={logout}>
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span>
            Clínica <span className="breadcrumb">/ {title}</span>
          </span>
          <span className="header-date">
            {new Date().toLocaleDateString("pt-BR", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </span>
        </header>
        <main className="content">
          {section !== "analysis" && (
            <div className="page-heading">
              <div>
                <span className="eyebrow">
                  {section === "dashboard"
                    ? "SEU ESPAÇO DE AVALIAÇÃO"
                    : "BIOMETRIA"}
                </span>
                <h1>{title}</h1>
                <p>
                  {section === "dashboard"
                    ? "Medidas objetivas. Contexto clínico. Acompanhamento contínuo."
                    : section === "patients"
                      ? "Prontuários e histórico de avaliações da sua clínica."
                      : section === "assessments"
                        ? "Da captura à revisão profissional."
                        : ""}
                </p>
              </div>
              {section !== "settings" && (
                <button
                  onClick={() => {
                    setNewAssessment(true);
                    setAdding(false);
                  }}
                >
                  <Plus size={18} />
                  Nova avaliação
                </button>
              )}
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              {error}
              <button className="ghost" onClick={() => setError("")}>
                Fechar
              </button>
            </div>
          )}
          {newAssessment && (
            <section className="panel form-panel">
              <div className="section-heading">
                <h2>Iniciar avaliação</h2>
                <button
                  className="ghost"
                  onClick={() => setNewAssessment(false)}
                >
                  Cancelar
                </button>
              </div>
              {patients.length ? (
                <form onSubmit={create}>
                  <div className="form-grid">
                    <label className="span2">
                      Paciente
                      <select
                        name="patient_id"
                        defaultValue={patient?.id}
                        required
                      >
                        {patients.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Tipo
                      <select name="kind">
                        {Object.entries(kindLabels).map(([k, v]) => (
                          <option key={k} value={k}>
                            {v}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Modo
                      <select name="mode">
                        <option value="camera">Câmera em tempo real</option>
                        <option value="photo">Fotografia</option>
                      </select>
                    </label>
                  </div>
                  <p className="muted small">
                    Neste MVP, todos os tipos registram medidas posturais
                    estáticas. Protocolos de movimento entram na próxima
                    entrega.
                  </p>
                  <button disabled={busy}>
                    {busy ? "Criando…" : "Iniciar captura"}
                  </button>
                </form>
              ) : (
                <div className="empty">
                  <p>Cadastre um paciente para iniciar.</p>
                  <button
                    onClick={() => {
                      setNewAssessment(false);
                      setSection("patients");
                      setAdding(true);
                    }}
                  >
                    Cadastrar paciente
                  </button>
                </div>
              )}
            </section>
          )}
          {section === "dashboard" && dashboard && (
            <>
              <div className="stat-grid">
                {[
                  [dashboard.patients, "Pacientes cadastrados", Users],
                  [dashboard.assessments, "Avaliações no total", ClipboardList],
                  [dashboard.last_30_days, "Nos últimos 30 dias", Activity],
                  [dashboard.pending, "Aguardando conclusão", Camera],
                ].map(([value, label, Icon]) => {
                  const I = Icon as typeof Activity;
                  return (
                    <div className="stat-card panel" key={label as string}>
                      <div>
                        <span>{label as string}</span>
                        <I size={19} />
                      </div>
                      <strong>{value as number}</strong>
                    </div>
                  );
                })}
              </div>
              <div className="dashboard-grid">
                <section className="panel">
                  <div className="section-heading">
                    <h2>Últimas avaliações</h2>
                    <button
                      className="text-button"
                      onClick={() => navigate("assessments")}
                    >
                      Ver avaliações <ArrowUpRight size={16} />
                    </button>
                  </div>
                  <AssessmentTable
                    list={dashboard.recent}
                    patients={patients}
                    onOpen={openAssessment}
                  />
                </section>
                <section className="panel recent-patients">
                  <div className="section-heading">
                    <h2>Pacientes recentes</h2>
                    <button
                      className="icon-button"
                      aria-label="Cadastrar paciente"
                      onClick={() => {
                        navigate("patients");
                        setAdding(true);
                      }}
                    >
                      <Plus size={18} />
                    </button>
                  </div>
                  {patients.slice(0, 5).map((p) => (
                    <button
                      className="patient-link"
                      key={p.id}
                      onClick={() => choosePatient(p)}
                    >
                      <span className="avatar">
                        {p.name
                          .split(" ")
                          .slice(0, 2)
                          .map((n) => n[0])
                          .join("")}
                      </span>
                      <span>
                        <strong>{p.name}</strong>
                        <small>Ver prontuário e histórico</small>
                      </span>
                      <ArrowUpRight size={17} />
                    </button>
                  ))}
                  {!patients.length && (
                    <p className="muted">Nenhum paciente cadastrado.</p>
                  )}
                </section>
              </div>
              <div className="workflow-banner">
                <div>
                  <span className="eyebrow">AVALIAÇÃO POSTURAL GUIADA</span>
                  <h2>Uma captura. Medidas rastreáveis.</h2>
                  <p>
                    Registre as vistas, confira os landmarks e revise cada
                    medida.
                  </p>
                </div>
                <button
                  className="secondary"
                  onClick={() => setNewAssessment(true)}
                >
                  Iniciar avaliação <ArrowUpRight size={17} />
                </button>
              </div>
            </>
          )}
          {section === "patients" && (
            <>
              {adding ? (
                <PatientForm
                  onCancel={() => setAdding(false)}
                  onSaved={async (p) => {
                    await refresh();
                    await choosePatient(p);
                  }}
                />
              ) : patient ? (
                <>
                  <div className="section-heading">
                    <button className="ghost" onClick={() => setPatient(null)}>
                      <ChevronLeft size={17} />
                      Todos os pacientes
                    </button>
                    <button onClick={() => setNewAssessment(true)}>
                      <Plus size={17} />
                      Avaliar paciente
                    </button>
                  </div>
                  <section className="panel patient-detail">
                    <span className="avatar large">{patient.name[0]}</span>
                    <div>
                      <h2>{patient.name}</h2>
                      <p className="muted">
                        Nascimento:{" "}
                        {new Date(
                          patient.birth_date + "T12:00:00",
                        ).toLocaleDateString("pt-BR")}
                      </p>
                      <p>
                        {String(
                          patient.details.complaint || "Sem queixa registrada.",
                        )}
                      </p>
                    </div>
                  </section>
                  <section className="panel">
                    <h2>Histórico de avaliações</h2>
                    <AssessmentTable
                      list={history}
                      patients={patients}
                      onOpen={openAssessment}
                    />
                  </section>
                </>
              ) : (
                <section className="panel">
                  <div className="section-heading">
                    <label className="search">
                      <Search size={18} />
                      <input
                        placeholder="Buscar paciente pelo nome"
                        aria-label="Buscar paciente"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </label>
                    <button onClick={() => setAdding(true)}>
                      <Plus size={17} />
                      Cadastrar paciente
                    </button>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Paciente</th>
                          <th>Nascimento</th>
                          <th>Prática esportiva</th>
                          <th>Prontuário</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map((p) => (
                          <tr key={p.id}>
                            <td>
                              <strong>{p.name}</strong>
                            </td>
                            <td>
                              {new Date(
                                p.birth_date + "T12:00:00",
                              ).toLocaleDateString("pt-BR")}
                            </td>
                            <td>{p.details.sport || "Não informado"}</td>
                            <td>
                              <button
                                className="text-button"
                                onClick={() => choosePatient(p)}
                              >
                                Abrir <ArrowUpRight size={15} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!filtered.length && (
                      <div className="empty">
                        <Users size={32} />
                        <h3>
                          {query
                            ? "Nenhum resultado"
                            : "Comece pelo primeiro paciente"}
                        </h3>
                        <p>Os prontuários cadastrados aparecerão aqui.</p>
                      </div>
                    )}
                  </div>
                </section>
              )}
            </>
          )}
          {section === "assessments" && (
            <section className="panel">
              <h2>Histórico por paciente</h2>
              <p className="muted">
                Selecione o paciente para consultar todas as suas avaliações.
              </p>
              {patients.map((p) => (
                <button
                  className="patient-link"
                  key={p.id}
                  onClick={() => choosePatient(p)}
                >
                  <span className="avatar">{p.name[0]}</span>
                  <strong>{p.name}</strong>
                  <ArrowUpRight size={18} />
                </button>
              ))}
            </section>
          )}
          {section === "analysis" && assessment && (
            <>
              <div className="assessment-heading">
                <div>
                  <button
                    className="ghost"
                    onClick={() =>
                      patient ? choosePatient(patient) : navigate("assessments")
                    }
                  >
                    <ChevronLeft size={16} />
                    Histórico
                  </button>
                  <h1>{patient?.name || "Avaliação corporal"}</h1>
                  <p>
                    {kindLabels[assessment.kind]} ·{" "}
                    {new Date(assessment.created_at).toLocaleString("pt-BR")}
                  </p>
                </div>
                <span className="badge">{statusLabels[assessment.status]}</span>
              </div>
              <div
                className="analysis-tabs"
                role="group"
                aria-label="Etapa da avaliação"
              >
                {assessment.status !== "completed" && (
                  <button
                    className={tab === "capture" ? "selected" : "ghost"}
                    onClick={() => setTab("capture")}
                  >
                    01 Captura
                  </button>
                )}
                <button
                  className={tab === "results" ? "selected" : "ghost"}
                  onClick={() => setTab("results")}
                >
                  02 Medidas e revisão{" "}
                  <span className="badge">{assessment.analyses.length}</span>
                </button>
              </div>
              {tab === "capture" && assessment.status !== "completed" ? (
                <Capture
                  key={assessment.id}
                  assessment={assessment}
                  onSaved={(a) => {
                    setAssessment(a);
                    setTab("results");
                    void refresh();
                  }}
                />
              ) : (
                <Results
                  key={assessment.id}
                  assessment={assessment}
                  onChanged={(a) => {
                    setAssessment(a);
                    void refresh();
                  }}
                />
              )}
            </>
          )}
          {section === "settings" && <SettingsView user={user} />}
          <footer className="page-footer">
            Biometria · Medição assistida em 2D{" "}
            <span>A interpretação final pertence ao profissional.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
