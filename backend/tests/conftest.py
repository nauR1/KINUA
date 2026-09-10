import os
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_test_dir = tempfile.TemporaryDirectory(prefix="biometria-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_dir.name) / "bootstrap.db")
os.environ["STORAGE_DIR"] = str(Path(_test_dir.name) / "media")
from app import models as m  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hasher  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db(tmp_path):
    test_url = os.environ.get("TEST_DATABASE_URL")
    admin_engine = None
    schema = "test_" + uuid.uuid4().hex
    if test_url:
        from sqlalchemy.schema import CreateSchema

        admin_engine = create_engine(test_url)
        with admin_engine.begin() as conn:
            conn.execute(CreateSchema(schema))
        engine = create_engine(
            test_url, connect_args={"options": "-csearch_path=" + schema}
        )
    else:
        engine = create_engine(
            "sqlite:///" + str(tmp_path / "test.db"),
            connect_args={"check_same_thread": False},
        )
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def keys(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        for index in (1, 2):
            clinic = m.Clinic(id=f"clinic-{index}", name=f"Clinic {index}")
            session.add(clinic)
            session.flush()
            session.add(
                m.User(
                    id=f"user-{index}",
                    clinic_id=clinic.id,
                    name=f"Professional {index}",
                    email=f"user{index}@test.local",
                    password_hash=hasher.hash("Test-password-123"),
                    role="admin" if index == 1 else "physiotherapist",
                )
            )
        session.commit()

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()
    if admin_engine:
        from sqlalchemy.schema import DropSchema

        with admin_engine.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()


@pytest.fixture
def client(db):
    with TestClient(
        app,
        headers={"X-Requested-With": "Biometria", "Origin": "http://localhost:3000"},
    ) as client:
        yield client


@pytest.fixture
def auth(client):
    r = client.post(
        "/auth/login",
        json={"email": "user1@test.local", "password": "Test-password-123"},
    )
    assert r.status_code == 200
    return client


@pytest.fixture
def landmarks():
    positions = {
        "nose": (0.5, 0.08),
        "left_ear": (0.46, 0.1),
        "right_ear": (0.54, 0.1),
        "left_shoulder": (0.3, 0.25),
        "right_shoulder": (0.7, 0.25),
        "left_hip": (0.4, 0.5),
        "right_hip": (0.6, 0.5),
        "left_knee": (0.4, 0.7),
        "right_knee": (0.6, 0.7),
        "left_ankle": (0.4, 0.9),
        "right_ankle": (0.6, 0.9),
        "left_foot_index": (0.4, 0.94),
        "right_foot_index": (0.6, 0.94),
    }
    return [
        {"name": n, "x": p[0], "y": p[1], "visibility": 0.99, "z": 0}
        for n, p in positions.items()
    ]


@pytest.fixture
def video(tmp_path):
    import cv2
    import numpy as np

    path = tmp_path / "fixture.webm"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"VP80"), 10, (640, 480))
    assert writer.isOpened()
    for _ in range(20):
        writer.write(np.full((480, 640, 3), 180, dtype=np.uint8))
    writer.release()
    return path
