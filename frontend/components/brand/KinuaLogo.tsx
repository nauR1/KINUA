import geometry from "./geometry.json";

type Props = {
  variant?: "horizontal" | "compact" | "symbol";
  size?: number;
  showTagline?: boolean;
  theme?: "light" | "dark" | "monochrome";
};

export default function KinuaLogo({
  variant = "horizontal",
  size = 180,
  showTagline = false,
  theme = "light",
}: Props) {
  const compact = variant === "compact";
  const symbolOnly = variant === "symbol";
  const width = symbolOnly
    ? 128
    : compact
      ? geometry.wordmarkWidth
      : 145 + geometry.wordmarkWidth;
  const height = compact ? 250 : 150;
  return (
    <span className={`kinua-logo kinua-logo--${theme}`} style={{ width: size }}>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="KINUA">
        <g
          transform={compact ? `translate(${(width - 128) / 2} 0)` : undefined}
        >
          <circle cx="77" cy="17" r="12" className="kinua-navy" />
          {geometry.paths.map((d, i) => (
            <path
              key={d}
              d={d}
              className={i < 2 ? "kinua-navy" : "kinua-teal"}
            />
          ))}
        </g>
        {!symbolOnly && (
          <g
            className="kinua-navy"
            transform={compact ? "translate(0 163)" : "translate(145 26)"}
            dangerouslySetInnerHTML={{ __html: geometry.wordmark }}
          />
        )}
      </svg>
      {showTagline && !symbolOnly && (
        <span className="kinua-tagline">
          Inteligência em
          <br />
          movimento humano
        </span>
      )}
    </span>
  );
}
