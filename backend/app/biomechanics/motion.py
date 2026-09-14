"""Time-series geometry and experimental phase segmentation; no clinical cutoffs."""

import math
import statistics

from .engine import MIN_VISIBILITY, BiomechanicsEngine, angle, horizontal_tilt

VERSION = "2.0.1"
PHASE_RULES = {
    "version": "1.0.0",
    "kind": "experimental_technical",
    "reference": "engineering_spec/docs/movements.md",
    "angle_hysteresis_deg": 4,
    "angle_min_excursion_deg": 10,
    "ratio_hysteresis": 0.02,
    "ratio_min_excursion": 0.05,
    "initial_stable_samples": 3,
    "minimum_return_samples": 2,
    "max_gap_ms": 1100,
}


class MotionEngine:
    version = VERSION

    def measure(self, landmarks, width, height, view, protocol, side, brightness):
        measures, quality = BiomechanicsEngine().analyze(
            landmarks, width, height, view, True, True, brightness
        )
        points = {p.name: p for p in landmarks}

        def p(name):
            item = points.get(name)
            if (
                not item
                or item.visibility < MIN_VISIBILITY
                or not 0 <= item.x <= 1
                or not 0 <= item.y <= 1
            ):
                raise ValueError("Landmark indisponível: " + name)
            return item.x * width / height, item.y

        def add(
            key, label, names, fn, region, limb="bilateral", unit="°", allowed=True
        ):
            confidence = min(
                (points[n].visibility if n in points else 0 for n in names), default=0
            )
            details = {
                "region": region,
                "side": limb,
                "method": key + "/" + VERSION,
                "view": view,
                "landmarks": names,
                "threshold_status": "threshold_pending_validation",
            }
            try:
                if not allowed:
                    raise ValueError("Medida incompatível com o plano ou protocolo.")
                if brightness < 0.12:
                    raise ValueError("Iluminação insuficiente.")
                value = round(fn(*[p(n) for n in names]), 4)
                details["status"] = "measured"
            except ValueError as exc:
                value = None
                details.update(status="unavailable", reason=str(exc))
            measures.append(
                dict(
                    key=key,
                    label=label,
                    value=value,
                    unit=unit,
                    confidence=confidence,
                    details=details,
                )
            )

        def medial(hip, knee, ankle, opposite):
            dy = ankle[1] - hip[1]
            if abs(dy) < 1e-4 or math.dist(hip, opposite) < 1e-4:
                raise ValueError("Segmentos insuficientes para projeção.")
            line_x = hip[0] + (ankle[0] - hip[0]) * (knee[1] - hip[1]) / dy
            return (
                (knee[0] - line_x)
                * (1 if opposite[0] > hip[0] else -1)
                / math.dist(hip, opposite)
            )

        for limb, label in [("left", "esquerdo"), ("right", "direito")]:
            opposite = "right" if limb == "left" else "left"
            sag = view == "lateral_" + limb
            add(
                limb + "_knee_medial_ratio",
                "Deslocamento medial relativo do joelho " + label,
                [limb + "_hip", limb + "_knee", limb + "_ankle", opposite + "_hip"],
                medial,
                "knee",
                limb,
                "razão",
                view in ("anterior", "posterior"),
            )
            add(
                limb + "_hip_flexion",
                "Flexão projetada do quadril " + label,
                [limb + "_shoulder", limb + "_hip", limb + "_knee"],
                lambda a, b, c: 180 - angle(a, b, c),
                "pelvis",
                limb,
                allowed=sag,
            )
            add(
                limb + "_ankle_angle",
                "Ângulo projetado tornozelo/pé " + label,
                [limb + "_knee", limb + "_ankle", limb + "_foot_index"],
                angle,
                "ankle",
                limb,
                allowed=sag,
            )
            add(
                limb + "_arm_elevation",
                "Elevação projetada do braço " + label,
                [limb + "_hip", limb + "_shoulder", limb + "_elbow"],
                angle,
                "shoulder",
                limb,
                allowed=protocol == "arm_raise"
                and (view in ("anterior", "posterior") or sag),
            )
            add(
                limb + "_trunk_sagittal",
                "Inclinação sagital aparente do tronco " + label,
                [limb + "_hip", limb + "_shoulder"],
                lambda a, b: horizontal_tilt((a[1], a[0]), (b[1], b[0])),
                "trunk",
                limb,
                allowed=sag,
            )

        def pelvis_height(lh, rh, la, ra, ls, rs):
            trunk = math.dist(
                ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2),
                ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2),
            )
            if trunk < 1e-4:
                raise ValueError("Tronco insuficiente para normalizar.")
            return ((lh[1] + rh[1]) - (la[1] + ra[1])) / (2 * trunk)

        add(
            "pelvis_vertical_ratio",
            "Posição vertical da pelve / tronco",
            [
                "left_hip",
                "right_hip",
                "left_ankle",
                "right_ankle",
                "left_shoulder",
                "right_shoulder",
            ],
            pelvis_height,
            "pelvis",
            unit="razão",
            allowed=view in ("anterior", "posterior"),
        )
        quality["valid_frames"] = int(any(m["value"] is not None for m in measures))
        return measures, quality


def phase_signal(view, protocol, side):
    if protocol == "arm_raise":
        if view.startswith("lateral_"):
            return view.removeprefix("lateral_") + "_arm_elevation", "angle"
        return (
            "right_arm_elevation" if side == "bilateral" else side + "_arm_elevation"
        ), "angle"
    if view.startswith("lateral_"):
        return view.removeprefix("lateral_") + "_knee_flexion", "angle"
    return "pelvis_vertical_ratio", "ratio"


def segment_phases(values, times, kind, protocol):
    phases = ["unknown"] * len(values)
    events = []
    cycles = []
    hysteresis = PHASE_RULES[
        "angle_hysteresis_deg" if kind == "angle" else "ratio_hysteresis"
    ]
    excursion = PHASE_RULES[
        "angle_min_excursion_deg" if kind == "angle" else "ratio_min_excursion"
    ]
    stable_limit = hysteresis / 2
    state = "waiting"
    window = []
    baseline = 0.0
    start = peak = 0
    maximum = 0.0
    return_count = 0
    for i, value in enumerate(values):
        if value is None or (i and times[i] - times[i - 1] > PHASE_RULES["max_gap_ms"]):
            if state in ("down", "up"):
                cycles.append(
                    {
                        "start_index": start,
                        "peak_index": peak,
                        "end_index": None,
                        "complete": False,
                        "reason": "gap",
                    }
                )
            state = "waiting"
            window = []
            continue
        if state == "waiting":
            window.append((i, value))
            window = window[-PHASE_RULES["initial_stable_samples"] :]
            if (
                len(window) == PHASE_RULES["initial_stable_samples"]
                and max(v for _, v in window) - min(v for _, v in window)
                <= stable_limit
            ):
                baseline = statistics.mean(v for _, v in window)
                state = "initial"
                for j, _ in window:
                    phases[j] = "initial"
            continue
        if state == "initial":
            phases[i] = "initial"
            if value - baseline >= hysteresis:
                state = "down"
                start = i
                peak = i
                maximum = value
                return_count = 0
                events.append({"type": "start", "index": i, "timestamp_ms": times[i]})
                phases[i] = "raising" if protocol == "arm_raise" else "descending"
        elif state == "down":
            phases[i] = "raising" if protocol == "arm_raise" else "descending"
            if value > maximum:
                maximum = value
                peak = i
            if maximum - value >= hysteresis:
                if maximum - baseline < excursion:
                    phases[start : i + 1] = ["insufficient_excursion"] * (i + 1 - start)
                    state = "waiting"
                    window = []
                    continue
                phases[peak] = "maximum"
                state = "up"
                phases[i] = "lowering" if protocol == "arm_raise" else "ascending"
                events.append(
                    {"type": "maximum", "index": peak, "timestamp_ms": times[peak]}
                )
        elif state == "up":
            phases[i] = "lowering" if protocol == "arm_raise" else "ascending"
            if value <= baseline + hysteresis:
                return_count += 1
                if return_count >= PHASE_RULES["minimum_return_samples"]:
                    phases[i] = "final"
                    cycles.append(
                        {
                            "start_index": start,
                            "peak_index": peak,
                            "end_index": i,
                            "complete": True,
                        }
                    )
                    events.append(
                        {"type": "final", "index": i, "timestamp_ms": times[i]}
                    )
                    state = "initial"
            else:
                return_count = 0
    if state in ("down", "up"):
        cycles.append(
            {
                "start_index": start,
                "peak_index": peak,
                "end_index": None,
                "complete": False,
                "reason": "recording_ended",
            }
        )
    return {
        "phases": phases,
        "events": events,
        "cycles": cycles,
        "rules": PHASE_RULES,
        "status": "experimental",
    }


def summarize(records, view, protocol, side, target_fps):
    first = records[0]["measurements"]
    times = [r["timestamp_ms"] for r in records]
    summaries = []
    for key, definition in first.items():
        samples = [
            (i, r["measurements"][key]["value"], r["measurements"][key]["confidence"])
            for i, r in enumerate(records)
            if r["measurements"][key]["value"] is not None
        ]
        details = {
            **definition["details"],
            "statistic": "mean",
            "valid_samples": len(samples),
            "total_samples": len(records),
        }
        if samples:
            lo = min(samples, key=lambda x: x[1])
            hi = max(samples, key=lambda x: x[1])
            details.update(
                min=lo[1],
                max=hi[1],
                amplitude=round(hi[1] - lo[1], 4),
                min_index=lo[0],
                max_index=hi[0],
                peak_timestamp_ms=times[hi[0]],
                status="measured",
            )
        summaries.append(
            {
                **definition,
                "value": round(statistics.mean(v for _, v, _ in samples), 4)
                if samples
                else None,
                "confidence": min(c for _, _, c in samples) if samples else 0,
                "details": details,
            }
        )
    # D/E comparisons only across simultaneous valid samples, never independent extrema.
    pairs = {}
    for base in ("knee_projection", "knee_medial_ratio", "arm_elevation"):
        pair = []
        for r in records:
            left = r["measurements"].get("left_" + base, {}).get("value")
            right = r["measurements"].get("right_" + base, {}).get("value")
            pair.append(
                round(right - left, 4)
                if left is not None and right is not None
                else None
            )
        pairs[base] = {"values": pair, "convention": "right_minus_left"}
    for i, r in enumerate(records):
        r["velocity"] = {}
        if not i:
            continue
        dt = (times[i] - times[i - 1]) / 1000
        for key, m in r["measurements"].items():
            before = records[i - 1]["measurements"][key]["value"]
            r["velocity"][key] = (
                round((m["value"] - before) / dt, 4)
                if m["value"] is not None
                and before is not None
                and 0 < dt <= 2.1 / target_fps
                else None
            )
    signal, kind = phase_signal(view, protocol, side)
    values = [r["measurements"].get(signal, {}).get("value") for r in records]
    phases = segment_phases(values, times, kind, protocol)
    return summaries, {
        "version": VERSION,
        "protocol": protocol,
        "side": side,
        "signal": signal,
        "comparison": pairs,
        "target_fps": target_fps,
        "sample_count": len(records),
        "duration_seconds": times[-1] / 1000,
        "phase_detection": phases,
        "phase_limitations": "Fases experimentais. Exige início estável e plano fixo. Não constitui classificação clínica.",
    }
