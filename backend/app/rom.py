"""Versioned 2D segment geometry. No reference ranges or clinical diagnosis."""

import math
import statistics

from .biomechanics.engine import MIN_VISIBILITY, angle

VERSION = "rom-1.0.0"
TECHNICAL_RULES = {
    "version": "1.0.0",
    "kind": "experimental_technical",
    "source": "docs/rom.md",
    "stable_samples": 3,
    "onset_delta_deg": 4.0,
    "maximum_gap_ms": 1100,
    "minimum_brightness": 0.12,
}
DEFINITIONS = {
    "shoulder_flexion": {
        "name": "Ombro — flexão",
        "joint": "shoulder",
        "plane": "sagittal",
        "points": ["hip", "shoulder", "elbow"],
        "formula": "angle",
        "direction": 1,
    },
    "shoulder_abduction": {
        "name": "Ombro — abdução",
        "joint": "shoulder",
        "plane": "frontal",
        "points": ["hip", "shoulder", "elbow"],
        "formula": "angle",
        "direction": 1,
    },
    "elbow_flexion": {
        "name": "Cotovelo — flexão",
        "joint": "elbow",
        "plane": "sagittal",
        "points": ["shoulder", "elbow", "wrist"],
        "formula": "180-angle",
        "direction": 1,
    },
    "elbow_extension": {
        "name": "Cotovelo — extensão",
        "joint": "elbow",
        "plane": "sagittal",
        "points": ["shoulder", "elbow", "wrist"],
        "formula": "180-angle",
        "direction": -1,
    },
    "hip_flexion": {
        "name": "Quadril — flexão",
        "joint": "pelvis",
        "plane": "sagittal",
        "points": ["shoulder", "hip", "knee"],
        "formula": "180-angle",
        "direction": 1,
    },
    "knee_flexion": {
        "name": "Joelho — flexão",
        "joint": "knee",
        "plane": "sagittal",
        "points": ["hip", "knee", "ankle"],
        "formula": "180-angle",
        "direction": 1,
    },
    "knee_extension": {
        "name": "Joelho — extensão",
        "joint": "knee",
        "plane": "sagittal",
        "points": ["hip", "knee", "ankle"],
        "formula": "180-angle",
        "direction": -1,
    },
}
LIMITATIONS = [
    "Estimativa geométrica 2D, sem calibração clínica. Visibilidade não é acurácia nem probabilidade clínica.",
    "O profissional confirma plano, lado e direção: a câmera não verifica o plano anatômico em 3D.",
    "Ângulo não orientado: não distingue hiperextensão, adução ou movimento no sentido oposto.",
    "Ombro representa braço relativo ao tronco, sem isolar articulação glenoumeral; quadril usa tronco/coxa, sem medir orientação pélvica.",
    "Máximos entre amostras podem ser perdidos. Excursão observada não equivale a amplitude clínica completa.",
]


def definition(movement):
    return {
        **DEFINITIONS[movement],
        "movement": movement,
        "version": VERSION,
        "rules": TECHNICAL_RULES,
        "limitations": LIMITATIONS,
        "instructions": "Posicione a câmera perpendicular ao plano informado, mantenha os três segmentos visíveis e evite rotação. Comece parado, execute o movimento escolhido de forma controlada e termine parado. O profissional define a amplitude tolerada.",
    }


def allowed_views(config, side):
    return (
        ["anterior", "posterior"]
        if config["plane"] == "frontal"
        else ["lateral_" + side]
    )


class ROMEngine:
    version = VERSION

    def __init__(self, config):
        if config["version"] != VERSION:
            raise ValueError("Versão de ROM não disponível neste processador.")
        self.config = config

    def measure(self, landmarks, width, height, view, protocol, side, brightness):
        points = {p.name: p for p in landmarks}
        limbs = ["left", "right"] if side == "bilateral" else [side]
        measures = []
        for limb in limbs:
            names = [limb + "_" + p for p in self.config["points"]]
            confidence = min(
                (points[n].visibility if n in points else 0 for n in names)
            )
            details = {
                "region": self.config["joint"],
                "side": limb,
                "method": VERSION + "/" + self.config["movement"],
                "view": view,
                "plane": self.config["plane"],
                "landmarks": names,
                "threshold_status": "threshold_pending_validation",
            }
            value = None
            try:
                if view not in allowed_views(self.config, limb):
                    raise ValueError(
                        "Plano incompatível com o movimento e o lado selecionados."
                    )
                if brightness < TECHNICAL_RULES["minimum_brightness"]:
                    raise ValueError("Iluminação insuficiente.")
                coords = []
                for name in names:
                    p = points.get(name)
                    if (
                        not p
                        or p.visibility < MIN_VISIBILITY
                        or not 0 <= p.x <= 1
                        or not 0 <= p.y <= 1
                    ):
                        raise ValueError(
                            "Landmark ausente, obstruído ou fora do quadro: " + name
                        )
                    coords.append((p.x * width / height, p.y))
                if (
                    min(
                        math.dist(coords[0], coords[1]), math.dist(coords[1], coords[2])
                    )
                    < 1e-4
                ):
                    raise ValueError("Segmentos insuficientes para medição.")
                value = angle(*coords)
                if self.config["formula"] == "180-angle":
                    value = 180 - value
                value = round(value, 4)
                details["status"] = "measured"
            except ValueError as exc:
                details.update(status="unavailable", reason=str(exc))
            measures.append(
                dict(
                    key=limb + "_rom",
                    label=self.config["name"]
                    + " · "
                    + ("direito" if limb == "right" else "esquerdo"),
                    value=value,
                    unit="°",
                    confidence=confidence,
                    details=details,
                )
            )
        valid = [m for m in measures if m["value"] is not None]
        quality = {
            "valid_frames": int(bool(valid)),
            "landmark_visibility_mean": statistics.mean(m["confidence"] for m in valid)
            if valid
            else 0,
            "coverage": len(valid) / len(measures),
            "messages": [
                m["details"]["reason"] for m in measures if m["value"] is None
            ],
            "limitations": list(LIMITATIONS),
        }
        return measures, quality

    def summarize(self, records, view, protocol, side, fps):
        summaries = []
        times = [r["timestamp_ms"] for r in records]
        events = []
        phases = ["unknown"] * len(records)
        for key, first in records[0]["measurements"].items():
            valid = [
                (i, r["measurements"][key])
                for i, r in enumerate(records)
                if r["measurements"][key]["value"] is not None
            ]
            details = {
                **first["details"],
                "statistic": "mean",
                "valid_samples": len(valid),
                "total_samples": len(records),
                "rom_version": VERSION,
                "movement": self.config["movement"],
                "direction": self.config["direction"],
            }
            baseline = None
            onset = None
            # Baseline must be consecutive, stable and before the detected onset.
            window = []
            for i, r in enumerate(records):
                v = r["measurements"][key]["value"]
                if v is None or (
                    i
                    and times[i] - times[i - 1]
                    > min(TECHNICAL_RULES["maximum_gap_ms"], 2100 / fps)
                ):
                    window = []
                    baseline = None
                    continue
                window.append(v)
                window = window[-TECHNICAL_RULES["stable_samples"] :]
                if (
                    baseline is None
                    and len(window) == TECHNICAL_RULES["stable_samples"]
                    and max(window) - min(window) <= TECHNICAL_RULES["onset_delta_deg"]
                ):
                    baseline = statistics.mean(window)
                if (
                    baseline is not None
                    and (v - baseline) * self.config["direction"]
                    > TECHNICAL_RULES["onset_delta_deg"]
                ):
                    onset = i
                    break
            if valid:
                lo = min(valid, key=lambda x: x[1]["value"])
                hi = max(valid, key=lambda x: x[1]["value"])
                peak = hi if self.config["direction"] > 0 else lo
                details.update(
                    min=lo[1]["value"],
                    max=hi[1]["value"],
                    amplitude=round(hi[1]["value"] - lo[1]["value"], 4),
                    min_index=lo[0],
                    max_index=hi[0],
                    peak_index=peak[0],
                    peak_value=peak[1]["value"],
                    peak_timestamp_ms=times[peak[0]],
                    peak_frame_index=records[peak[0]]["frame_index"],
                    baseline=baseline,
                    movement_start_index=onset,
                    peak_visibility=peak[1]["confidence"],
                    status="measured",
                )
                if onset is not None:
                    events.append(
                        dict(
                            type="movement_start",
                            index=onset,
                            timestamp_ms=times[onset],
                            side=first["details"]["side"],
                        )
                    )
                events.append(
                    dict(
                        type="maximum",
                        index=peak[0],
                        timestamp_ms=times[peak[0]],
                        side=first["details"]["side"],
                    )
                )
            summaries.append(
                {
                    **first,
                    "value": round(statistics.mean(m["value"] for _, m in valid), 4)
                    if valid
                    else None,
                    "confidence": min(m["confidence"] for _, m in valid)
                    if valid
                    else 0,
                    "details": details,
                }
            )
        for i, r in enumerate(records):
            r["velocity"] = {}
            for key, m in r["measurements"].items():
                previous = records[i - 1]["measurements"][key]["value"] if i else None
                dt = (times[i] - times[i - 1]) / 1000 if i else 0
                r["velocity"][key] = (
                    round((m["value"] - previous) / dt, 4)
                    if previous is not None
                    and m["value"] is not None
                    and 0 < dt <= 2.1 / fps
                    else None
                )
            phases[i] = "sampled" if r["quality"]["valid_frames"] else "unknown"
        return summaries, {
            "version": VERSION,
            "protocol": "rom",
            "side": side,
            "signal": summaries[0]["key"],
            "comparison": {},
            "target_fps": fps,
            "sample_count": len(records),
            "duration_seconds": times[-1] / 1000,
            "rom": self.config,
            "phase_detection": {
                "phases": phases,
                "events": events,
                "cycles": [],
                "rules": TECHNICAL_RULES,
            },
            "phase_limitations": "Início experimental após estabilidade e deslocamento angular de 4°. Pico é o extremo observado (mínimo de flexão residual na extensão); não confirma fim do movimento nem conta repetições.",
        }
