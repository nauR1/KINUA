"""Demo credential regressions; conftest runs unchanged against PostgreSQL too."""

import json
import secrets
import sys

import pytest
from sqlalchemy import select

from app import demo_seed
from app import models as m
from app.core.config import settings
from app.core.security import digest, verify_password


def run_cli(monkeypatch, db, email, password, *args):
    monkeypatch.setattr(demo_seed, "SessionLocal", db)
    monkeypatch.setattr(settings(), "allow_demo_seed", True)
    monkeypatch.setenv("DEMO_PASSWORD", password)
    monkeypatch.setattr(sys, "argv", ["demo_seed", "--email", email, *args])
    demo_seed.main()


def post_login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_cli_seed_login_reset_password_post_again(db, client, monkeypatch, capsys):
    a, b, c = [secrets.token_urlsafe(24) + "!$" for _ in range(3)]
    email = "demo@test.local"
    with db() as session:
        session.get(m.User, "user-2").role = "platform_admin"
        normal_hash = session.get(m.User, "user-1").password_hash
        session.commit()
    run_cli(monkeypatch, db, "  DEMO@test.local  ", a)
    assert post_login(client, email, a).status_code == 200
    run_cli(monkeypatch, db, email, b, "--reset")
    assert post_login(client, email, a).status_code == 401
    assert post_login(client, " DEMO@test.local ", b).status_code == 200
    run_cli(monkeypatch, db, "newdemo@test.local", c)
    assert post_login(client, "newdemo@test.local", c).status_code == 200
    assert (
        post_login(client, "user1@test.local", "Test-password-123").status_code == 200
    )
    assert (
        post_login(client, "user2@test.local", "Test-password-123").status_code == 200
    )
    with db() as session:
        user = session.scalar(select(m.User).where(m.User.email == email))
        assert verify_password(user.password_hash, b)
        assert not verify_password(user.password_hash, a)
        assert user.password_hash not in [a, b, c]
        assert session.get(m.User, "user-1").password_hash == normal_hash
    output = capsys.readouterr().out
    assert all(password not in output for password in [a, b, c])


def test_existing_seed_wrong_password_fails_without_mutation(db, client, monkeypatch):
    a, b = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    run_cli(monkeypatch, db, "demo@test.local", a)
    with db() as session:
        before = session.scalar(select(m.User).where(m.User.email == "demo@test.local"))
        original_hash, original_id = before.password_hash, before.id
        patients = list(session.scalars(select(m.Patient.id)))
    with pytest.raises(SystemExit, match="não corresponde"):
        run_cli(monkeypatch, db, "demo@test.local", b)
    with db() as session:
        assert session.get(m.User, original_id).password_hash == original_hash
        assert list(session.scalars(select(m.Patient.id))) == patients
    assert post_login(client, "demo@test.local", a).status_code == 200
    assert post_login(client, "demo@test.local", b).status_code == 401


def test_reset_clears_only_demo_lockout(db, client, monkeypatch):
    a, b = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    email = "demo@test.local"
    run_cli(monkeypatch, db, email, a)
    for _ in range(5):
        assert post_login(client, email, b).status_code == 401
    assert post_login(client, email, a).status_code == 429
    with db() as session:
        session.add(m.LoginAttempt(key=digest("user1@test.local"), count=4))
        session.commit()
    run_cli(monkeypatch, db, email, b, "--reset")
    with db() as session:
        assert session.get(m.LoginAttempt, digest(email)) is None
        assert session.get(m.LoginAttempt, digest("user1@test.local")).count == 4
    assert post_login(client, email, b).status_code == 200


def test_verify_only_reads_without_hash_or_secret_output(
    db, client, monkeypatch, capsys
):
    password = secrets.token_urlsafe(24)
    run_cli(monkeypatch, db, "demo@test.local", password)
    capsys.readouterr()
    with db() as session:
        original = session.scalar(
            select(m.User).where(m.User.email == "demo@test.local")
        )
        session.add(m.LoginAttempt(key=digest(original.email), count=5))
        session.commit()
        original_hash = original.password_hash
    monkeypatch.setattr(settings(), "allow_demo_seed", False)
    monkeypatch.setattr(
        sys, "argv", ["demo_seed", "--email", "demo@test.local", "--verify-only"]
    )
    with pytest.raises(SystemExit) as error:
        demo_seed.main()
    assert error.value.code == 1
    output = capsys.readouterr().out
    data = json.loads(output)
    assert data["status"] == "locked" and data["password_matches"] is True
    assert password not in output and original_hash not in output
    with db() as session:
        assert session.get(m.LoginAttempt, digest(original.email)).count == 5
        assert session.get(m.User, original.id).password_hash == original_hash


@pytest.mark.parametrize(
    "email,status",
    [("missing@test.local", "user_not_found"), ("user1@test.local", "not_demo")],
)
def test_readonly_diagnostic_unknown_and_non_demo(db, email, status):
    result = demo_seed.verify_demo_credentials(db, email, secrets.token_urlsafe(24))
    assert result["status"] == status


def test_empty_environment_password_does_not_fallback_to_prompt(db, monkeypatch):
    def no_prompt(*args):
        raise AssertionError("Empty configured password must be rejected, not replaced")

    monkeypatch.setattr(demo_seed.getpass, "getpass", no_prompt)
    with pytest.raises(SystemExit, match="Dados inválidos"):
        run_cli(monkeypatch, db, "demo@test.local", "")
