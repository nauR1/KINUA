"""Geometria 2D, sem diagnóstico, pixels brutos ou dependência de MediaPipe."""

import math
from dataclasses import asdict, dataclass

from ..schemas import Landmark

VERSION = "1.0.1"
# Critério técnico de visibilidade, não referência clínica nem acurácia.
MIN_VISIBILITY = 0.65


def angle(a: tuple, b: tuple, c: tuple) -> float:
    if not all(math.isfinite(value) for p in (a, b, c) for value in p):
        raise ValueError("Coordenada não finita")
    u, v = (a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])
    length = math.hypot(*u) * math.hypot(*v)
    if length < 1e-12:
        raise ValueError("Segmento de comprimento nulo")
    return math.degrees(
        math.acos(max(-1, min(1, (u[0] * v[0] + u[1] * v[1]) / length)))
    )


def horizontal_tilt(a: tuple, b: tuple) -> float:
    if not all(math.isfinite(value) for p in (a, b) for value in p):
        raise ValueError("Coordenada não finita")
    dx, dy = b[0] - a[0], b[1] - a[1]
    if math.hypot(dx, dy) < 1e-12:
        raise ValueError("Segmento de comprimento nulo")
    # Módulo, invariante ao espelhamento; não inventa lado elevado.
    return math.degrees(math.atan2(abs(dy), abs(dx)))


@dataclass
class Measurement:
    key: str
    label: str
    value: float | None
    unit: str
    confidence: float
    details: dict


class BiomechanicsEngine:
    version = VERSION

    def analyze(
        self,
        landmarks: list[Landmark],
        width: int,
        height: int,
        view: str,
        level_confirmed: bool,
        view_confirmed: bool,
        brightness: float,
    ) -> tuple[list[dict], dict]:
        lm = {p.name: p for p in landmarks}

        def point(name):
            p = lm.get(name)
            if (
                not p
                or p.visibility < MIN_VISIBILITY
                or not (0 <= p.x <= 1 and 0 <= p.y <= 1)
            ):
                raise ValueError(
                    "Landmark ausente, fora do enquadramento ou com baixa visibilidade: "
                    + name
                )
            return p.x * width / height, p.y

        measures = []

        def measure(
            key, label, names, fn, region, side="bilateral", unit="°", allowed=True
        ):
            confidence = min(
                (lm[n].visibility if n in lm else 0 for n in names), default=0
            )
            details = {
                "region": region,
                "side": side,
                "landmarks": names,
                "view": view,
                "method": key + "/1.0.0",
                "threshold_status": "threshold_pending_validation",
            }
            try:
                if not allowed or not view_confirmed:
                    raise ValueError(
                        "Plano de captura não confirmado ou incompatível com esta medida."
                    )
                if not level_confirmed:
                    raise ValueError("Confirme o nivelamento da câmera antes de medir.")
                if brightness < 0.12:
                    raise ValueError("Iluminação insuficiente. Repita a captura.")
                value = round(fn(*[point(n) for n in names]), 3)
                details["status"] = "measured"
            except ValueError as exc:
                value = None
                details.update(status="unavailable", reason=str(exc))
            measures.append(
                asdict(
                    Measurement(key, label, value, unit, round(confidence, 4), details)
                )
            )

        frontal = view in ("anterior", "posterior")
        measure(
            "shoulder_tilt",
            "Inclinação aparente dos ombros",
            ["left_shoulder", "right_shoulder"],
            horizontal_tilt,
            "shoulder",
            allowed=frontal,
        )
        measure(
            "pelvis_tilt",
            "Obliquidade aparente da pelve",
            ["left_hip", "right_hip"],
            horizontal_tilt,
            "pelvis",
            allowed=frontal,
        )
        measure(
            "head_tilt",
            "Inclinação aparente da cabeça",
            ["left_ear", "right_ear"],
            horizontal_tilt,
            "head",
            allowed=frontal,
        )

        def trunk(ls, rs, lh, rh):
            sx, sy = (ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2
            hx, hy = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
            if math.hypot(sx - hx, sy - hy) < 1e-12:
                raise ValueError("Tronco sem comprimento mensurável.")
            return math.degrees(math.atan2(abs(sx - hx), abs(sy - hy)))

        measure(
            "trunk_tilt",
            "Inclinação frontal aparente do tronco",
            ["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
            trunk,
            "trunk",
            allowed=frontal,
        )

        def stance(la, ra, lh, rh):
            pelvis = math.dist(lh, rh)
            if pelvis < 1e-6:
                raise ValueError("Largura pélvica insuficiente para normalizar.")
            return math.dist(la, ra) / pelvis

        measure(
            "stance_ratio",
            "Base de apoio / largura da pelve",
            ["left_ankle", "right_ankle", "left_hip", "right_hip"],
            stance,
            "ankle",
            unit="razão",
            allowed=frontal,
        )
        for side, label in [("left", "esquerdo"), ("right", "direito")]:
            names = [f"{side}_hip", f"{side}_knee", f"{side}_ankle"]
            measure(
                f"{side}_knee_projection",
                f"Ângulo projetado do joelho {label}",
                names,
                angle,
                "knee",
                side,
                allowed=frontal,
            )
            measure(
                f"{side}_knee_flexion",
                f"Flexão 2D do joelho {label}",
                names,
                lambda a, b, c: 180 - angle(a, b, c),
                "knee",
                side,
                allowed=view == f"lateral_{side}",
            )

        required = [
            "nose",
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
            "left_foot_index",
            "right_foot_index",
        ]
        visible = [
            n
            for n in required
            if n in lm
            and lm[n].visibility >= MIN_VISIBILITY
            and 0 <= lm[n].x <= 1
            and 0 <= lm[n].y <= 1
        ]
        messages = []
        if len(visible) != len(required):
            messages.append(
                "Corpo parcialmente visível ou landmarks com baixa visibilidade. Inclua cabeça e pés."
            )
        if brightness < 0.12:
            messages.append(
                "Iluminação insuficiente. Aumente a iluminação e repita a captura."
            )
        if not level_confirmed:
            messages.append(
                "Nivelamento da câmera ainda não confirmado pelo profissional."
            )
        if not view_confirmed:
            messages.append("Plano de captura ainda não confirmado pelo profissional.")
        if any(
            n in lm
            and (lm[n].x < 0.05 or lm[n].x > 0.95 or lm[n].y < 0.02 or lm[n].y > 0.98)
            for n in required
        ):
            messages.append(
                "Paciente próximo à borda. Centralize e aumente a distância, se necessário."
            )
        quality = {
            "landmark_visibility_mean": round(
                sum(lm[n].visibility for n in visible) / len(visible), 4
            )
            if visible
            else 0,
            "coverage": len(visible) / len(required),
            "brightness": round(brightness, 4),
            "camera_level_confirmed": level_confirmed,
            "view_confirmed": view_confirmed,
            "messages": messages,
            "valid_frames": 1 if any(m["value"] is not None for m in measures) else 0,
            "total_frames": 1,
            "temporal_stability": "not_assessed_single_frame",
            "confidence_kind": "technical_visibility_not_clinical_probability",
            "limitations": [
                "Geometria 2D não calibrada; perspectiva não quantificada.",
                "Landmarks estimados não são marcadores anatômicos palpados.",
                "Ângulo projetado do joelho não classifica varo ou valgo.",
                "Sem referências clínicas validadas para classificação.",
            ],
        }
        return measures, quality
