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
  PanelLeftClose,
  PanelLeftOpen,
  FileText,
} from "lucide-react";
import { api, post, type Patient, type Assessment } from "@/lib/api";
import PatientForm from "@/components/PatientForm";
import Capture from "@/components/Capture";
import VideoCapture from "@/components/VideoCapture";
import Login from "@/components/Login";
import AssessmentTable from "@/components/AssessmentTable";
import SettingsView from "@/components/SettingsView";
import Results from "@/components/Results";
import Comparison from "@/components/Comparison";
import KinuaLogo from "@/components/brand/KinuaLogo";
import MovementArt from "@/components/brand/MovementArt";
import MetricCard from "@/components/ui/MetricCard";
import EmptyState from "@/components/ui/EmptyState";
import ProtocolCatalog from "@/components/ProtocolCatalog";
import ProtocolWorkspace from "@/components/ProtocolWorkspace";
import { ROMLauncher, ROMHistory } from "@/components/ROM";
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
    [protocolPending, setProtocolPending] = useState(false),
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
    [dark, setDark] = useState(false),
    [collapsed, setCollapsed] = useState(false),
    [mode, setMode] = useState("camera"),
    [protocol, setProtocol] = useState("bilateral_squat");
  useEffect(() => {
    try {
      setDark(localStorage.getItem("kinua-theme") === "dark");
      setCollapsed(localStorage.getItem("kinua-sidebar") === "collapsed");
    } catch {}
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
    if (protocolPending) return;
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
    if (protocolPending) return;
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
        protocol: mode === "video" ? protocol : "static",
        side:
          mode === "video" && protocol === "single_leg_squat"
            ? f.get("side")
            : "bilateral",
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
    if (protocolPending) return;
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
        <div className="brand-pulse">
          <KinuaLogo variant="symbol" size={66} />
        </div>
        <p>Carregando sua clínica…</p>
      </main>
    );
  if (!user) return <Login onLogin={setUser} />;
  const filtered = patients.filter((p) =>
    p.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  );
  const CaptureComponent =
    assessment?.mode === "video" ? VideoCapture : Capture;
  const title =
    section === "dashboard"
      ? "Início"
      : section === "protocols"
        ? "Protocolos"
        : section === "rom"
          ? "ROM"
          : section === "patients"
            ? "Pacientes"
            : section === "analysis"
              ? "Avaliação corporal"
              : section === "reports"
                ? "Relatórios"
                : section === "settings"
                  ? "Configurações"
                  : "Avaliações";
  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <a className="skip-link" href="#main-content">
        Ir para o conteúdo
      </a>
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="KINUA, início">
          <KinuaLogo
            variant={collapsed ? "symbol" : "horizontal"}
            theme="dark"
            size={collapsed ? 38 : 174}
          />
        </a>
        <button
          className="sidebar-collapse"
          aria-label={collapsed ? "Expandir navegação" : "Recolher navegação"}
          title={collapsed ? "Expandir navegação" : "Recolher navegação"}
          onClick={() => {
            setCollapsed(!collapsed);
            try {
              localStorage.setItem(
                "kinua-sidebar",
                collapsed ? "expanded" : "collapsed",
              );
            } catch {}
          }}
        >
          {collapsed ? (
            <PanelLeftOpen size={18} />
          ) : (
            <PanelLeftClose size={18} />
          )}
        </button>
        <div className="workspace-label">ESPAÇO CLÍNICO</div>
        <nav aria-label="Navegação principal">
          {[
            ["dashboard", "Início", LayoutDashboard],
            ["patients", "Pacientes", Users],
            ["assessments", "Avaliações", ClipboardList],
            ["analysis", "Análise", Activity],
            ["protocols", "Protocolos", ClipboardList],
            ["rom", "ROM", Activity],
            ["reports", "Relatórios", FileText],
            ["settings", "Configurações", Settings],
          ].map(([key, label, Icon]) => {
            const I = Icon as typeof Activity;
            return (
              <button
                key={key as string}
                className={section === key ? "active" : ""}
                disabled={protocolPending}
                aria-label={label as string}
                title={label as string}
                aria-current={section === key ? "page" : undefined}
                onClick={() => {
                  navigate(key as string);
                  if (key === "analysis") setNewAssessment(true);
                }}
              >
                <I size={19} />
                <span className="nav-label">{label as string}</span>
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
          <button
            className="theme-toggle"
            aria-label={dark ? "Tema claro" : "Tema escuro"}
            title={dark ? "Tema claro" : "Tema escuro"}
            onClick={() => {
              setDark(!dark);
              try {
                localStorage.setItem("kinua-theme", dark ? "light" : "dark");
              } catch {}
            }}
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
            <span className="nav-label">Tema {dark ? "claro" : "escuro"}</span>
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
          <div className="header-tools">
            <label className="search header-search">
              <Search size={16} />
              <input
                disabled={protocolPending}
                aria-label="Busca rápida de pacientes"
                placeholder="Buscar paciente…"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  if (section !== "patients" || patient) navigate("patients");
                }}
              />
            </label>
            <span className="header-date">
              {new Date().toLocaleDateString("pt-BR", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
            <button
              className="avatar header-profile"
              aria-label="Abrir configurações da conta"
              onClick={() => navigate("settings")}
            >
              {user.name.slice(0, 2).toUpperCase()}
            </button>
          </div>
        </header>
        <main className="content" id="main-content" tabIndex={-1}>
          {section !== "analysis" && (
            <div className="page-heading">
              <div>
                <span className="eyebrow">
                  {section === "dashboard"
                    ? "SEU ESPAÇO DE AVALIAÇÃO"
                    : "KINUA"}
                </span>
                <h1>
                  {section === "dashboard"
                    ? `Olá, ${user.name.split(" ")[0]}.`
                    : title}
                </h1>
                <p>
                  {section === "dashboard"
                    ? "Movimento gera novas possibilidades."
                    : section === "patients"
                      ? "Prontuários e histórico de avaliações da sua clínica."
                      : section === "assessments"
                        ? "Da captura à revisão profissional."
                        : ""}
                </p>
              </div>
              {section !== "settings" && (
                <button
                  disabled={protocolPending}
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
          {protocolPending && (
            <p className="info-box" role="status">
              Existem alterações não salvas. Salve os dados atuais antes de sair.
            </p>
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
                      <select
                        name="mode"
                        value={mode}
                        onChange={(e) => setMode(e.target.value)}
                      >
                        <option value="camera">Câmera em tempo real</option>
                        <option value="photo">Fotografia</option>
                        <option value="video">
                          Vídeo / gravação de movimento
                        </option>
                      </select>
                    </label>
                  </div>
                  {mode === "video" && (
                    <div className="form-grid">
                      <label>
                        Protocolo
                        <select
                          value={protocol}
                          onChange={(e) => setProtocol(e.target.value)}
                        >
                          <option value="bilateral_squat">
                            Agachamento bilateral
                          </option>
                          <option value="single_leg_squat">
                            Agachamento unipodal
                          </option>
                          <option value="arm_raise">Elevação de braço</option>
                        </select>
                      </label>
                      {protocol === "single_leg_squat" && (
                        <label>
                          Lado avaliado
                          <select name="side">
                            <option value="right">Direito</option>
                            <option value="left">Esquerdo</option>
                          </select>
                        </label>
                      )}
                    </div>
                  )}
                  <p className="muted small">
                    Medidas projetadas em 2D. Para movimento, registre uma
                    posição inicial estável antes de iniciar e retorne à posição
                    inicial.
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
                    <MetricCard
                      key={label as string}
                      label={label as string}
                      value={value as number}
                      icon={I}
                    />
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
                    <EmptyState
                      title="Prontos para começar"
                      description="Cadastre seu primeiro paciente e acompanhe cada movimento."
                    />
                  )}
                </section>
              </div>
              <div className="workflow-banner">
                <MovementArt />
                <div>
                  <span className="eyebrow">AVALIAÇÃO POSTURAL GUIADA</span>
                  <h2>Inteligência em movimento humano.</h2>
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
                  patient={patient}
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
                  <button className="secondary" onClick={() => setAdding(true)}>
                    Editar paciente
                  </button>
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
                  <div className="button-row">
                    <button onClick={() => setSection("protocols")}>
                      Iniciar protocolo
                    </button>
                    <button
                      className="secondary"
                      onClick={() => setSection("rom")}
                    >
                      Medir ROM
                    </button>
                  </div>
                  <ROMHistory
                    key={patient.id}
                    patientId={patient.id}
                    onOpen={openAssessment}
                  />
                  <Comparison history={history} />
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
                            : "Seu primeiro movimento começa aqui."}
                        </h3>
                        <p>Os prontuários cadastrados aparecerão aqui.</p>
                      </div>
                    )}
                  </div>
                </section>
              )}
            </>
          )}
          {(section === "assessments" || section === "reports") && (
            <section className="panel">
              <h2>
                {section === "reports"
                  ? "Relatórios por paciente"
                  : "Histórico por paciente"}
              </h2>
              <p className="muted">
                Selecione o paciente para consultar suas avaliações, revisar os
                resultados e gerar o relatório em PDF.
              </p>
              {!patients.length && (
                <EmptyState description="Os históricos e relatórios estarão disponíveis após a primeira avaliação." />
              )}
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
          {section === "protocols" && (
            <ProtocolCatalog
              patients={patients}
              patientId={patient?.id}
              onOpen={async (id) => {
                await refresh();
                await openAssessment(id);
              }}
            />
          )}
          {section === "rom" && (
            <ROMLauncher
              patients={patients}
              patientId={patient?.id}
              onOpen={async (id) => {
                await refresh();
                await openAssessment(id);
              }}
            />
          )}
          {section === "analysis" && assessment && (
            <>
              <div className="assessment-heading">
                <div>
                  <button
                    className="ghost"
                    disabled={protocolPending}
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
              {assessment.protocol_parent_id && (
                <button
                  className="text-button"
                  onClick={() => openAssessment(assessment.protocol_parent_id!)}
                >
                  Voltar ao protocolo
                </button>
              )}
              {assessment.assessment_protocol ? (
                <ProtocolWorkspace
                  key={assessment.id}
                  assessment={assessment}
                  onOpen={openAssessment}
                  onChanged={setAssessment}
                  onPending={setProtocolPending}
                />
              ) : (
                <>
                  <div
                    className="analysis-tabs"
                    role="group"
                    aria-label="Etapa da avaliação"
                  >
                    {assessment.status !== "completed" && (
                      <button
                        className={tab === "capture" ? "selected" : "ghost"}
                        disabled={protocolPending}
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
                      <span className="badge">
                        {assessment.analyses.length}
                      </span>
                    </button>
                  </div>
                  {tab === "capture" && assessment.status !== "completed" ? (
                    <CaptureComponent
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
                      onPending={setProtocolPending}
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
            </>
          )}
          {section === "settings" && <SettingsView user={user} />}
          <footer className="page-footer">
            KINUA · Medição assistida em 2D{" "}
            <span>A interpretação final pertence ao profissional.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
