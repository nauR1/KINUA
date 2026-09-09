/** Decorative geometry only. It never represents patient data or a measurement. */
export default function MovementArt({
  className = "",
}: {
  className?: string;
}) {
  return (
    <svg
      className={`movement-art ${className}`}
      viewBox="0 0 600 400"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M-40 370C100 200 155 390 290 237S470 40 660 150"
        className="movement-wave"
      />
      <path
        d="M-50 410C90 225 160 430 310 257S490 55 670 190"
        className="movement-wave secondary-wave"
      />
      <path
        d="M-70 300C115 440 150 115 310 196S420 380 650 260"
        className="movement-wave faint-wave"
      />
      <g
        className="movement-person"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="393" cy="91" r="25" />
        <path d="M382 119C367 146 369 184 385 214L356 283L335 336M382 128L333 167L298 162M393 136L439 167L468 138M386 212L425 265L452 280" />
        <path
          d="M376 144L401 154M374 181L390 180M375 210L395 209"
          className="faint-wave"
        />
      </g>
      <g className="movement-joints">
        {[
          [382, 128],
          [374, 181],
          [385, 214],
          [333, 167],
          [439, 167],
          [356, 283],
          [425, 265],
          [335, 336],
          [452, 280],
        ].map(([cx, cy]) => (
          <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="5" />
        ))}
      </g>
      <circle cx="298" cy="162" r="13" className="movement-orbit" />
      <circle cx="468" cy="138" r="19" className="movement-orbit" />
    </svg>
  );
}
