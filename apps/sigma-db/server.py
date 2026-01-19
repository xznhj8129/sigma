"""
Usage:
    python apps/sigma-db/server.py --config configs/sigma-db.sample.json
"""
import argparse
import json
import os
import threading
from pathlib import Path
from typing import Any
from json import JSONDecodeError

from fastapi import Depends, FastAPI, Header, HTTPException, Path as ApiPath, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from tinydb import Query as TinyQuery
from tinydb import TinyDB


class DbConfig(BaseModel):
    host: str
    port: int
    db_dir: str
    allowed_dbs: list[str]
    auth_token: str | None = None

    model_config = ConfigDict(extra="forbid")


class DocumentPayload(BaseModel):
    data: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class UpdatePayload(BaseModel):
    data: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class DbManager:
    def __init__(self, config: DbConfig):
        self.config = config
        self.dbs = self._open_dbs(config)
        self.lock = threading.Lock()

    def _open_dbs(self, config: DbConfig) -> dict[str, TinyDB]:
        root = Path(config.db_dir)
        if not root.exists():
            raise RuntimeError(f"db_dir does not exist: {root}")
        dbs = {}
        for name in config.allowed_dbs:
            dbs[name] = TinyDB(root / f"db_{name}.json")
        return dbs

    def get_db(self, name: str) -> TinyDB:
        db = self.dbs.get(name)
        if db is None:
            raise HTTPException(status_code=404, detail=f"Unknown db '{name}'")
        return db

    def with_db(self, name: str, fn):
        db = self.get_db(name)
        try:
            with self.lock:
                return fn(db)
        except JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"DB file is corrupted: {exc}") from exc


def enforce_auth(expected: str | None, token: str | None):
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def create_app(config: DbConfig) -> FastAPI:
    manager = DbManager(config)
    app = FastAPI()

    def auth_dependency(x_auth_token: str | None = Header(default=None)):
        enforce_auth(config.auth_token, x_auth_token)
        return True

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/{db_name}")
    def list_documents(
        db_name: str = ApiPath(..., description="Database name"),
        key: str | None = Query(default=None),
        value: str | None = Query(default=None),
        _auth: bool = Depends(auth_dependency),
    ):
        def op(db: TinyDB):
            if key is None and value is None:
                return db.all()
            if key is None or value is None:
                raise HTTPException(status_code=400, detail="Both key and value are required when filtering")
            q = TinyQuery()
            return db.search(q[key] == value)

        return manager.with_db(db_name, op)

    @app.post("/api/{db_name}")
    def insert_document(
        payload: DocumentPayload,
        db_name: str = ApiPath(..., description="Database name"),
        _auth: bool = Depends(auth_dependency),
    ):
        def op(db: TinyDB):
            db.insert(payload.data)
            return JSONResponse({"message": "inserted"}, status_code=201)

        return manager.with_db(db_name, op)

    @app.put("/api/{db_name}/{key}/{value}")
    def update_document(
        payload: UpdatePayload,
        db_name: str = ApiPath(..., description="Database name"),
        key: str = ApiPath(...),
        value: str = ApiPath(...),
        _auth: bool = Depends(auth_dependency),
    ):
        def op(db: TinyDB):
            q = TinyQuery()
            updated = db.update(payload.data, q[key] == value)
            return {"updated": len(updated)}

        return manager.with_db(db_name, op)

    @app.delete("/api/{db_name}/{key}/{value}")
    def delete_document(
        db_name: str = ApiPath(..., description="Database name"),
        key: str = ApiPath(...),
        value: str = ApiPath(...),
        _auth: bool = Depends(auth_dependency),
    ):
        def op(db: TinyDB):
            q = TinyQuery()
            removed = db.remove(q[key] == value)
            return {"removed": len(removed)}

        return manager.with_db(db_name, op)

    return app


def load_config(path: Path) -> DbConfig:
    with path.open("r", encoding="utf-8") as file:
        return DbConfig.model_validate_json(file.read())


def main():
    parser = argparse.ArgumentParser(description="Sigma DB server (FastAPI/TinyDB)")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    args = parser.parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    app = create_app(config)
    import uvicorn

    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
