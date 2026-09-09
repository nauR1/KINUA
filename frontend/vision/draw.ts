import { connections, type Landmark } from "./types";
export function drawSkeleton(
  canvas: HTMLCanvasElement,
  landmarks: Landmark[],
  width: number,
  height: number,
) {
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle =
    getComputedStyle(canvas).getPropertyValue("--brand-teal").trim() ||
    "#14B8A6";
  ctx.fillStyle =
    getComputedStyle(canvas).getPropertyValue("--brand-mint").trim() ||
    "#A7F3D0";
  ctx.lineWidth = Math.max(2, width / 350);
  const points = new Map(
    landmarks.filter((p) => p.visibility >= 0.65).map((p) => [p.name, p]),
  );
  for (const [a, b] of connections) {
    const p = points.get(a),
      q = points.get(b);
    if (!p || !q) continue;
    ctx.beginPath();
    ctx.moveTo(p.x * width, p.y * height);
    ctx.lineTo(q.x * width, q.y * height);
    ctx.stroke();
  }
  for (const p of points.values()) {
    ctx.beginPath();
    ctx.arc(
      p.x * width,
      p.y * height,
      Math.max(3, width / 220),
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }
}
