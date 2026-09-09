"use client";
import type { Finding } from "@/lib/api";
const regions = [
  { key: "head", name: "Cabeça", x: 100, y: 28 },
  { key: "shoulder", name: "Ombros", x: 100, y: 72 },
  { key: "trunk", name: "Tronco", x: 100, y: 116 },
  { key: "pelvis", name: "Pelve", x: 100, y: 160 },
  { key: "knee", name: "Joelhos", x: 100, y: 218 },
  { key: "ankle", name: "Tornozelos / pés", x: 100, y: 280 },
];
export default function BodyMap({
  findings,
  selected,
  onSelect,
}: {
  findings: Finding[];
  selected: string;
  onSelect: (region: string) => void;
}) {
  return (
    <div className="body-map">
      <svg
        viewBox="0 0 200 310"
        role="img"
        aria-label="Mapa das regiões com medidas registradas"
      >
        <circle
          cx="100"
          cy="28"
          r="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          d="M100 50V155 M52 75H148 M52 75L35 160 M148 75L165 160 M100 155L73 225L65 285 M100 155L127 225L135 285"
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {regions.map((r) => (
          <circle
            key={r.key}
            cx={r.x}
            cy={r.y}
            r="10"
            fill={
              selected === r.key
                ? "var(--chart-secondary)"
                : findings.some((f) => f.region === r.key)
                  ? "var(--accent)"
                  : "var(--line)"
            }
          />
        ))}
      </svg>
      <div>
        <p className="muted">
          Filtre os registros por região. Destaque indica presença de medidas,
          sem classificação de alteração.
        </p>
        <div className="button-row">
          <button
            className={!selected ? "" : "secondary"}
            onClick={() => onSelect("")}
          >
            Todas
          </button>
          {regions.map((r) => (
            <button
              key={r.key}
              className={selected === r.key ? "" : "secondary"}
              onClick={() => onSelect(r.key)}
            >
              {r.name}{" "}
              <span className="badge">
                {findings.filter((f) => f.region === r.key).length}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
