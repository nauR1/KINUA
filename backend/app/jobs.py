"""Durable database queue. One subprocess per job, bounded by a watchdog."""

import argparse
import subprocess
import sys
import time
from datetime import timedelta

import cv2
from fastapi import HTTPException
from sqlalchemy import select, update

from . import models as m
from .biomechanics.motion import MotionEngine, summarize
from .clinical.engine import AttentionEngine, ClinicalRulesEngine
from .core.database import SessionLocal
from .repositories import audit
from .rom import ROMEngine
from .storage import LocalStorageProvider
from .vision.provider import MediaPipePoseProvider
from .vision.video import frames


class Cancelled(Exception):
    pass


def heartbeat(job_id, progress, run_token=None):
    with SessionLocal() as db:
        changed = db.execute(
            update(m.ProcessingJob)
            .where(
                m.ProcessingJob.id == job_id,
                m.ProcessingJob.state == "running",
                m.ProcessingJob.run_token == run_token,
            )
            .values(progress=min(progress, 0.95), updated_at=m.now())
        ).rowcount
        db.commit()
        if not changed:
            raise Cancelled()


def process_job(job_id, provider_factory=MediaPipePoseProvider, expected_token=None):
    with SessionLocal() as db:
        job = db.get(m.ProcessingJob, job_id)
        if not job or job.state != "running":
            return
        run_token = job.run_token
        if expected_token is not None and run_token != expected_token:
            raise Cancelled()
        media = db.get(m.AssessmentMedia, job.media_id)
        assessment = db.get(m.Assessment, job.assessment_id)
        options = job.options
        protocol = assessment.protocol
        side = assessment.side
        rom_session = db.get(m.ROMSession, assessment.id)
    provider = provider_factory()
    engine = ROMEngine(rom_session.definition) if rom_session else MotionEngine()
    records = []
    try:
        for index, timestamp, rgb in frames(
            LocalStorageProvider().verified_path(
                media.storage_key, media.sha256, media.size
            ),
            options["fps"],
            media.metadata_json,
        ):
            heartbeat(
                job_id,
                timestamp / (max(media.metadata_json["duration_seconds"], 1) * 1000),
                run_token,
            )
            error = ""
            try:
                landmarks = provider.detect(rgb, round(timestamp))
            except ValueError as exc:
                landmarks = []
                error = str(exc)
            h, w = rgb.shape[:2]
            brightness = float(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).mean() / 255)
            measures, quality = engine.measure(
                landmarks, w, h, media.view, protocol, side, brightness
            )
            if error:
                quality["messages"].append(error)
            records.append(
                {
                    "frame_index": index,
                    "timestamp_ms": timestamp,
                    "landmarks": landmarks,
                    "measurements": {v["key"]: v for v in measures},
                    "quality": quality,
                }
            )
            if len(records) > 601:
                raise ValueError("Limite de amostras excedido.")
    finally:
        provider.close()
    if not records or not any(r["quality"]["valid_frames"] for r in records):
        raise ValueError(
            "Nenhum frame com medidas utilizáveis. Confira plano, iluminação e corpo inteiro."
        )
    summarize_frames = engine.summarize if rom_session else summarize
    summaries, motion = summarize_frames(
        records, media.view, protocol, side, options["fps"]
    )
    quality = {
        **records[0]["quality"],
        "total_frames": len(records),
        "valid_frames": sum(r["quality"]["valid_frames"] for r in records),
        "landmark_visibility_mean": sum(
            r["quality"]["landmark_visibility_mean"] for r in records
        )
        / len(records),
        "coverage": sum(r["quality"]["coverage"] for r in records) / len(records),
        "messages": list(
            dict.fromkeys(msg for r in records for msg in r["quality"]["messages"])
        ),
        "temporal_stability": "sampled_series_preserves_gaps",
    }
    quality["limitations"] += [
        "Vídeo amostrado: máximos entre amostras podem não ser detectados.",
        motion["phase_limitations"],
    ]
    with SessionLocal() as db:
        # This write locks the job and serializes cancellation with publication.
        locked = db.execute(
            update(m.ProcessingJob)
            .where(
                m.ProcessingJob.id == job_id,
                m.ProcessingJob.state == "running",
                m.ProcessingJob.run_token == run_token,
            )
            .values(updated_at=m.now())
        ).rowcount
        if not locked:
            raise Cancelled()
        current = db.scalar(
            select(m.Assessment)
            .where(m.Assessment.id == assessment.id)
            .with_for_update()
        )
        if current.status == "completed":
            raise ValueError("Avaliação concluída durante o processamento.")
        analysis = m.Analysis(
            assessment_id=assessment.id,
            media_id=media.id,
            provider="MediaPipePoseProvider",
            provider_version=provider.version,
            biomechanics_version=engine.version,
            rules_version=ClinicalRulesEngine.version,
            quality=quality,
            motion=motion,
        )
        db.add(analysis)
        db.flush()
        for i, record in enumerate(records):
            frame = m.PoseFrame(
                analysis_id=analysis.id,
                frame_index=record["frame_index"],
                timestamp_ms=record["timestamp_ms"],
                measurements={
                    "values": {
                        k: v["value"] for k, v in record["measurements"].items()
                    },
                    "velocity": record["velocity"],
                },
                phase=motion["phase_detection"]["phases"][i],
                quality=record["quality"],
            )
            db.add(frame)
            db.flush()
            db.add_all(
                [
                    m.PoseLandmark(frame_id=frame.id, **p.model_dump())
                    for p in record["landmarks"]
                ]
            )
        for summary in summaries:
            measurement = m.BiomechanicalMeasurement(analysis_id=analysis.id, **summary)
            db.add(measurement)
            db.flush()
            if summary["value"] is not None:
                if rom_session:
                    d = summary["details"]
                    db.add(
                        m.ROMMeasurement(
                            analysis_id=analysis.id,
                            measurement_id=measurement.id,
                            movement=rom_session.movement,
                            side=d["side"],
                            minimum=d["min"],
                            maximum=d["max"],
                            excursion=d["amplitude"],
                            peak_value=d["peak_value"],
                            peak_frame_index=d["peak_frame_index"],
                            peak_timestamp_ms=d["peak_timestamp_ms"],
                            confidence=d["peak_visibility"],
                            details=d,
                        )
                    )
                explanation = AttentionEngine().explain(summary)
                explanation["description"] = (
                    f"{summary['label']}: média {summary['value']:.1f} {summary['unit']}; mínimo {summary['details']['min']:.1f}; máximo {summary['details']['max']:.1f}. Sem classificação clínica."
                )
                explanation["explanation"].update(
                    timestamp_ms=summary["details"]["peak_timestamp_ms"],
                    sample_index=summary["details"].get(
                        "peak_index", summary["details"]["max_index"]
                    ),
                    frame_index=records[
                        summary["details"].get(
                            "peak_index", summary["details"]["max_index"]
                        )
                    ]["frame_index"],
                    reason="Resumo das amostras válidas. Frame indicado corresponde ao extremo observado (mínimo de flexão residual na extensão ROM), sem limiar clínico.",
                )
                db.add(
                    m.AttentionFinding(
                        analysis_id=analysis.id,
                        measurement_id=measurement.id,
                        **explanation,
                    )
                )
        current.status = "review"
        job = db.get(m.ProcessingJob, job_id)
        job.state = "succeeded"
        job.progress = 1
        job.updated_at = m.now()
        audit(db, db.get(m.User, job.owner_id), "video.processed", analysis.id)
        db.commit()


def fail(job_id, message, run_token=None):
    with SessionLocal() as db:
        job = db.get(m.ProcessingJob, job_id)
        if (
            job
            and job.state == "running"
            and (run_token is None or job.run_token == run_token)
        ):
            job.state = "failed"
            job.error = message
            job.updated_at = m.now()
            audit(db, db.get(m.User, job.owner_id), "video.failed", job.id)
            db.commit()


def claim():
    with SessionLocal() as db:
        stale = db.scalars(
            select(m.ProcessingJob).where(
                m.ProcessingJob.state == "running",
                m.ProcessingJob.updated_at < m.now() - timedelta(minutes=5),
            )
        ).all()
        for job in stale:
            job.state = "failed"
            job.error = "Processamento interrompido. É possível tentar novamente."
            job.updated_at = m.now()
            audit(db, db.get(m.User, job.owner_id), "video.interrupted", job.id)
        db.commit()
        candidate = db.scalar(
            select(m.ProcessingJob)
            .where(m.ProcessingJob.state == "pending")
            .order_by(m.ProcessingJob.created_at)
        )
        if not candidate:
            return None
        changed = db.execute(
            update(m.ProcessingJob)
            .where(
                m.ProcessingJob.id == candidate.id, m.ProcessingJob.state == "pending"
            )
            .values(state="running", updated_at=m.now(), run_token=m.uid())
        ).rowcount
        db.commit()
        return candidate.id if changed else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job")
    parser.add_argument("--token")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.job:
        try:
            process_job(args.job, expected_token=args.token)
        except Cancelled:
            pass
        except ValueError as exc:
            fail(args.job, str(exc), args.token)
        except HTTPException as exc:
            fail(args.job, str(exc.detail), args.token)
        except Exception:
            fail(
                args.job,
                "Falha no processamento. Confira o modelo e o arquivo, depois tente novamente.",
                args.token,
            )
        return
    while True:
        job_id = claim()
        if job_id:
            with SessionLocal() as db:
                run_token = db.get(m.ProcessingJob, job_id).run_token
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "app.jobs",
                        "--job",
                        job_id,
                        "--token",
                        run_token,
                    ],
                    timeout=240,
                    capture_output=True,
                )
                if result.returncode:
                    fail(
                        job_id,
                        "O processo de análise terminou inesperadamente.",
                        run_token,
                    )
            except subprocess.TimeoutExpired:
                fail(
                    job_id,
                    "Tempo limite de quatro minutos excedido. Use um vídeo menor.",
                    run_token,
                )
        if args.once:
            return
        time.sleep(1)


if __name__ == "__main__":
    main()
