import type { LucideIcon } from "lucide-react";
export default function MetricCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: LucideIcon;
}) {
  return (
    <article className="stat-card panel">
      <div>
        <span>{label}</span>
        <span className="metric-icon">
          <Icon size={20} aria-hidden="true" />
        </span>
      </div>
      <strong>{value.toLocaleString("pt-BR")}</strong>
      <span className="metric-caption">Registros da clínica</span>
    </article>
  );
}
