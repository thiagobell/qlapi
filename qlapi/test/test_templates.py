from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from qlapi.app import app
from qlapi import templates


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolate template storage to a per-test tmp dir so tests never touch the
    # real data/templates directory.
    monkeypatch.setattr(templates, "DATA_DIR", tmp_path)
    with TestClient(app) as c:
        yield c


def _body(name="mylabel", identifier="62", canvas=None):
    return {"name": name, "label_identifier": identifier, "canvas": canvas or {"objects": []}}


def test_template_crud_roundtrip(client):
    # create
    r = client.post("/templates", json=_body())
    assert r.status_code == HTTPStatus.OK
    created = r.json()
    template_id = created["id"]
    assert created["name"] == "mylabel"
    assert created["label_identifier"] == "62"
    assert created["canvas"] == {"objects": []}
    assert created["created_at"] == created["updated_at"]

    # get
    r = client.get(f"/templates/{template_id}")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["id"] == template_id

    # list includes it
    r = client.get("/templates")
    assert r.status_code == HTTPStatus.OK
    ids = [t["id"] for t in r.json()]
    assert template_id in ids
    # metadata only -- no canvas payload
    assert all("canvas" not in t for t in r.json())

    # update
    r = client.post(f"/templates/{template_id}", json=_body(name="renamed", canvas={"objects": [1]}))
    assert r.status_code == HTTPStatus.OK
    updated = r.json()
    assert updated["name"] == "renamed"
    assert updated["canvas"] == {"objects": [1]}
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] != created["updated_at"]

    # delete
    r = client.delete(f"/templates/{template_id}")
    assert r.status_code == HTTPStatus.NO_CONTENT

    # get after delete -> 404
    r = client.get(f"/templates/{template_id}")
    assert r.status_code == HTTPStatus.NOT_FOUND


def test_unknown_template_404s(client):
    assert client.get("/templates/nope").status_code == HTTPStatus.NOT_FOUND
    assert client.post("/templates/nope", json=_body()).status_code == HTTPStatus.NOT_FOUND
    assert client.delete("/templates/nope").status_code == HTTPStatus.NOT_FOUND
