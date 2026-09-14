"""Criação explícita de administrador sem dados demonstrativos; nunca executada no startup."""

import argparse
import getpass
import os

from sqlalchemy import select

from .clinical.engine import RULESET
from .core.database import SessionLocal
from .core.security import hasher
from .models import Clinic, ClinicalRule, Professional, User
from .repositories import audit


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--demo", action="store_true")

    parser.add_argument("--email", default="admin@biometria.local")

    parser.add_argument("--platform-admin", action="store_true")

    args = parser.parse_args()

    if args.demo:
        raise SystemExit(
            "--demo foi desativado. Use app.demo_seed com ALLOW_DEMO_SEED=true."
        )

    password = os.environ.get("BOOTSTRAP_PASSWORD") or getpass.getpass(
        "Senha inicial (mínimo 12 caracteres): "
    )

    if len(password) < 12:
        raise SystemExit("Use no mínimo 12 caracteres.")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == args.email.lower())):
            print("Usuário já existe. Nenhuma senha foi alterada.")

            return

        clinic = Clinic(
            name="Administração KINUA" if args.platform_admin else "Minha clínica"
        )

        db.add(clinic)

        db.flush()

        user = User(
            clinic_id=clinic.id,
            email=args.email.lower(),
            name="Administrador",
            role="platform_admin" if args.platform_admin else "admin",
            password_hash=hasher.hash(password),
        )

        db.add(user)

        db.flush()

        db.add(Professional(user_id=user.id))

        for rule in RULESET["rules"]:
            if not db.get(ClinicalRule, rule["id"]):
                db.add(
                    ClinicalRule(
                        id=rule["id"], version=RULESET["version"], definition=rule
                    )
                )

        audit(db, user, "bootstrap.created", clinic.id)

        db.commit()

        print("Administrador criado. Nenhum paciente, avaliação ou mídia foi criado.")


if __name__ == "__main__":
    main()
