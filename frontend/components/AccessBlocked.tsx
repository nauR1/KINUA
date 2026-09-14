"use client";
import KinuaLogo from "./brand/KinuaLogo";
export type AccessStatus = {
  code: string;
  is_demo?: boolean;
  plan?: string;
  expires_at?: string | null;
  days_remaining?: number | null;
};
export default function AccessBlocked({
  status,
  onBack,
}: {
  status: AccessStatus;
  onBack: () => void;
}) {
  const expired = ["user_access_expired", "subscription_expired"].includes(
    status.code,
  );
  return (
    <main className="access-page">
      {status.is_demo && (
        <div className="demo-banner">
          AMBIENTE DE DEMONSTRAÇÃO — todos os dados apresentados são fictícios.
        </div>
      )}
      <section className="panel">
        <KinuaLogo size={190} />
        <span className="eyebrow">ACESSO PROFISSIONAL</span>
        <h1>
          {expired
            ? "Seu acesso ao KINUA expirou"
            : status.code === "subscription_cancelled"
              ? "Seu acesso ao KINUA foi cancelado"
              : status.code === "access_not_started"
                ? "Seu acesso ainda não iniciou"
                : "Seu acesso está temporariamente suspenso."}
        </h1>
        {status.plan && (
          <p>
            Plano: <strong>{status.plan}</strong>
          </p>
        )}
        {status.expires_at && (
          <p>
            Vencimento: {new Date(status.expires_at).toLocaleString("pt-BR")}
          </p>
        )}
        <p>Procure o administrador responsável pelo seu acesso.</p>
        <button onClick={onBack}>Voltar ao login</button>
      </section>
    </main>
  );
}
