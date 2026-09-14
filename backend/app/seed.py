"""Criação explícita de administrador e dados fictícios; nunca executada no startup."""

import argparse
import getpass
import os

from sqlalchemy import select

from .clinical.engine import RULESET
from .core.database import SessionLocal
from .core.security import hasher
from .models import Clinic, ClinicalRule, Patient, Professional, User
from .repositories import audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--email", default="admin@biometria.local")
    args = parser.parse_args()
    password = os.environ.get("BOOTSTRAP_PASSWORD") or getpass.getpass(
        "Senha inicial (mínimo 12 caracteres): "
    )
    if len(password) < 12:
        raise SystemExit("Use no mínimo 12 caracteres.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == args.email.lower())):
            print("Usuário já existe. Nenhuma senha foi alterada.")
            return
        clinic = Clinic(name="Clínica Demonstração" if args.demo else "Minha clínica")
        db.add(clinic)
        db.flush()
        user = User(
            clinic_id=clinic.id,
            email=args.email.lower(),
            name="Administrador",
            role="admin",
            password_hash=hasher.hash(password),
        )
        db.add(user)
        db.flush()
        db.add(Professional(user_id=user.id))
        if args.demo:
            for name, birth, complaint in [
                ("Marina Exemplo", "1992-04-18", "Dados fictícios para demonstração"),
                ("Rafael Exemplo", "1985-11-09", "Dados fictícios para demonstração"),
            ]:
                db.add(
                    Patient(
                        clinic_id=clinic.id,
                        name=name,
                        birth_date=birth,
                        details={
                            "complaint": complaint,
                            "sport": "",
                            "dominance": "right",
                        },
                    )
                )
        for rule in RULESET["rules"]:
            if not db.get(ClinicalRule, rule["id"]):
                db.add(
                    ClinicalRule(
                        id=rule["id"], version=RULESET["version"], definition=rule
                    )
                )
        audit(db, user, "bootstrap.created", clinic.id)
        db.commit()
        print(
            "Administrador criado. Dados de demonstração são fictícios; nenhuma análise foi simulada."
        )


if __name__ == "__main__":
    main()
