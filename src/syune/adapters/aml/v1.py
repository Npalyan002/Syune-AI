"""Minimal Agent Memory Leaderboard Textual Memory Add/Search adapter."""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

from syune import AddMessage, BatchAddRequest, RecallRequest, Syune, SyuneError
from syune.product.config import load_config
from syune.product.state import initialize_state


_OPERATIONS_LOG = logging.getLogger("syune.aml.operations")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AMLMessage(_StrictModel):
    role: Literal["user", "assistant"]
    content: StrictStr = Field(min_length=1)
    timestamp: StrictInt | None = None

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("blank content")
        return value


class AMLAddRequest(_StrictModel):
    request_id: StrictStr = Field(min_length=1, max_length=256)
    messages: list[AMLMessage] = Field(min_length=1, max_length=20)
    user_id: StrictStr = Field(min_length=1, max_length=256)
    session_id: StrictStr = Field(min_length=1, max_length=256)

    @field_validator("request_id", "user_id", "session_id")
    @classmethod
    def identifiers_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("blank identifier")
        return value


class AMLSearchRequest(_StrictModel):
    query: StrictStr = Field(min_length=1)
    user_id: StrictStr = Field(min_length=1, max_length=256)
    top_k: StrictInt = Field(ge=1, le=100)
    options: list[StrictStr] | None = None

    @field_validator("query", "user_id")
    @classmethod
    def search_values_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("blank search value")
        return value

    @field_validator("options")
    @classmethod
    def options_not_blank(cls, value: list[str] | None):
        if value is not None and any(not item.strip() for item in value):
            raise ValueError("blank option")
        return value


class AMLAddResponse(_StrictModel):
    success: Literal[True]
    request_id: str
    user_id: str
    session_id: str


class AMLSearchItem(_StrictModel):
    id: str
    content: str
    score: float
    created_at: str


class AMLSearchResponse(_StrictModel):
    data: list[AMLSearchItem]


@dataclass(frozen=True, slots=True)
class AdapterSettings:
    state_root: Path
    bearer_token: str
    max_body_bytes: int = 1_048_576
    max_concurrency: int = 4
    queue_wait_seconds: float = 1.0
    min_free_bytes: int = 1_073_741_824

    def __post_init__(self) -> None:
        root = Path(self.state_root)
        if not root.is_absolute():
            raise ValueError("AML state_root must be absolute")
        if not self.bearer_token or len(self.bearer_token) > 4096:
            raise ValueError("AML bearer token must be nonempty")
        if type(self.max_body_bytes) is not int or self.max_body_bytes < 1024:
            raise ValueError("max_body_bytes must be at least 1024")
        if type(self.max_concurrency) is not int or self.max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        if type(self.queue_wait_seconds) not in (int, float) or self.queue_wait_seconds <= 0:
            raise ValueError("queue_wait_seconds must be positive")
        if type(self.min_free_bytes) is not int or self.min_free_bytes < 0:
            raise ValueError("min_free_bytes must be nonnegative")


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") not in ("/add", "/search"):
            await self.app(scope, receive, send)
            return
        content_length = dict(scope.get("headers", ())).get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await JSONResponse({"detail": {"reason": "request body too large"}}, 413)(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse({"detail": {"reason": "invalid content length"}}, 400)(scope, receive, send)
                return
        chunks = []
        total = 0
        more = True
        while more:
            message = await receive()
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_bytes:
                await JSONResponse({"detail": {"reason": "request body too large"}}, 413)(scope, receive, send)
                return
            chunks.append(chunk)
            more = message.get("more_body", False)
        body = b"".join(chunks)
        delivered = False
        async def replay_receive():
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        await self.app(scope, replay_receive, send)


def _prepare_state(root: Path) -> Path:
    root = root.resolve(strict=False)
    marker = root / "metadata" / ".syune-aml-evaluation"
    if root.exists() and any(root.iterdir()) and not marker.is_file():
        # A brand-new adapter root may contain only the config written below.
        if {item.name for item in root.iterdir()} != {"config.toml"}:
            raise ValueError("refusing non-dedicated state root without AML evaluation marker")
    root.mkdir(parents=True, exist_ok=True)
    config_path = root / "config.toml"
    if not config_path.exists():
        config_path.write_text("[retrieval]\nmax_results=100\n", encoding="utf-8")
    config = load_config(cli_state_root=root, cli_config=config_path)
    if config.retrieval.max_results != 100:
        raise ValueError("AML evaluation state must configure retrieval.max_results=100")
    initialize_state(config)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch(exist_ok=True)
    return root


def _readiness_check(root: Path, min_free_bytes: int) -> bool:
    """Verify local infrastructure without returning implementation details."""
    marker = root / "metadata" / ".syune-aml-evaluation"
    database = root / "memory" / "memory.sqlite3"
    if not marker.is_file() or not database.is_file():
        return False
    if shutil.disk_usage(root).free < min_free_bytes:
        return False
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".ready-", dir=cache):
        pass
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=rw", uri=True, timeout=1.0)
    try:
        connection.execute("SELECT 1").fetchone()
    finally:
        connection.close()
    return True


def _load_bearer_token() -> str:
    direct = os.environ.get("SYUNE_AML_BEARER_TOKEN")
    token_file = os.environ.get("SYUNE_AML_BEARER_TOKEN_FILE")
    if bool(direct) == bool(token_file):
        raise RuntimeError(
            "configure exactly one of SYUNE_AML_BEARER_TOKEN or SYUNE_AML_BEARER_TOKEN_FILE"
        )
    if direct:
        return direct
    path = Path(token_file or "")
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError("SYUNE_AML_BEARER_TOKEN_FILE must be an absolute regular file")
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError("unable to read SYUNE_AML_BEARER_TOKEN_FILE") from exc
    if not token or len(token) > 4096:
        raise RuntimeError("bearer token file must contain one nonempty token")
    return token


def _unix_ms(value: int | None) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("timestamp is outside the supported Unix-millisecond range") from exc


def _content(fields: dict) -> str | None:
    for name in ("content", "statement", "label", "description", "display_name"):
        value = fields.get(name)
        if isinstance(value, str) and value:
            return value
    steps = fields.get("steps")
    if isinstance(steps, list) and steps:
        return "\n".join(str(item) for item in steps)
    return None


def create_app(settings: AdapterSettings) -> FastAPI:
    state_root = _prepare_state(Path(settings.state_root))
    executor = ThreadPoolExecutor(max_workers=settings.max_concurrency, thread_name_prefix="syune-aml")
    slots = asyncio.Semaphore(settings.max_concurrency)
    open_lock = threading.Lock()

    def open_client() -> Syune:
        # Runtime startup atomically replaces one shared metadata file. Serialize
        # this short section so Windows and concurrent requests cannot race it.
        with open_lock:
            for attempt in range(6):
                try:
                    return Syune.open(state_root=state_root)
                except PermissionError:
                    # Windows scanners can briefly hold the destination of an
                    # atomic replace. Runtime.open closes partial resources.
                    if attempt == 5:
                        raise
                    time.sleep(0.02 * (2 ** attempt))
        raise RuntimeError("unreachable")
    @asynccontextmanager
    async def lifespan(_app):
        try:
            yield
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
    app = FastAPI(title="SYUNE AML Textual Adapter", version="1", docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_bytes)

    @app.middleware("http")
    async def structured_operations_log(request: Request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            # Deliberately omit headers, query strings, identities, and bodies.
            _OPERATIONS_LOG.info(json.dumps({
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }, separators=(",", ":")))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError):
        return JSONResponse({"detail": {"reason": "invalid request schema"}}, 422)

    @app.exception_handler(Exception)
    async def internal_error(_request: Request, _exc: Exception):
        return JSONResponse({"detail": {"reason": "internal service error"}}, 500)

    async def authenticated(authorization: str | None = Header(default=None)) -> None:
        scheme, _, supplied = authorization.partition(" ") if authorization else ("", "", "")
        valid = scheme == "Bearer" and bool(supplied) and hmac.compare_digest(
            supplied.encode("utf-8"), settings.bearer_token.encode("utf-8"))
        if not valid:
            raise HTTPException(401, detail={"reason": "authentication failed"},
                                headers={"WWW-Authenticate": "Bearer"})

    async def run_bounded(function):
        try:
            await asyncio.wait_for(slots.acquire(), timeout=settings.queue_wait_seconds)
        except TimeoutError:
            raise HTTPException(503, detail={"reason": "service capacity exhausted"}) from None
        try:
            return await asyncio.get_running_loop().run_in_executor(executor, function)
        finally:
            slots.release()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        try:
            is_ready = await run_bounded(
                lambda: _readiness_check(state_root, settings.min_free_bytes)
            )
        except (HTTPException, OSError, sqlite3.Error):
            is_ready = False
        if not is_ready:
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return {"status": "ready"}

    @app.post("/add", response_model=AMLAddResponse, dependencies=[Depends(authenticated)])
    async def add(payload: AMLAddRequest):
        def execute():
            messages = tuple(AddMessage(index, message.content, _unix_ms(message.timestamp),
                                        source_name=f"{payload.session_id}:{message.role}")
                             for index, message in enumerate(payload.messages))
            with open_client() as client:
                client.add_batch(BatchAddRequest(payload.request_id, payload.user_id,
                                                 payload.session_id, messages),
                                 global_request_id=True)
            return {"success": True, "request_id": payload.request_id,
                    "user_id": payload.user_id, "session_id": payload.session_id}
        try:
            return await run_bounded(execute)
        except SyuneError as exc:
            if exc.code == "IDEMPOTENCY_CONFLICT":
                raise HTTPException(409, detail={"reason": "request_id conflict"}) from None
            raise HTTPException(500, detail={"reason": "durable ingestion failed"}) from None
        except ValueError:
            raise HTTPException(422, detail={"reason": "invalid timestamp"}) from None

    @app.post("/search", response_model=AMLSearchResponse, dependencies=[Depends(authenticated)])
    async def search(payload: AMLSearchRequest):
        def execute():
            with open_client() as client:
                recalled = client.recall(RecallRequest(
                    cue=payload.query, max_results=payload.top_k, user_id=payload.user_id))
                data = []
                for candidate in recalled.data["candidates"][:payload.top_k]:
                    typed_id = candidate["entity_id"]
                    memory = client.memory_get(typed_id, user_id=payload.user_id).data
                    fields = memory["fields"]
                    content = _content(fields)
                    if not content:
                        continue
                    created_at = fields.get("observed_at") or fields.get("created_at") or fields.get("registered_at")
                    data.append({"id": typed_id, "content": content,
                                 "score": float(candidate["score"]),
                                 "created_at": created_at})
            return {"data": data}
        try:
            return await run_bounded(execute)
        except SyuneError:
            raise HTTPException(500, detail={"reason": "search failed"}) from None

    return app


def app_from_environment() -> FastAPI:
    """Uvicorn factory using explicit evaluation-only environment settings."""
    raw_root = os.environ.get("SYUNE_AML_STATE_ROOT")
    if not raw_root:
        raise RuntimeError("SYUNE_AML_STATE_ROOT is required")
    token = _load_bearer_token()
    return create_app(AdapterSettings(
        Path(raw_root), token,
        max_body_bytes=int(os.environ.get("SYUNE_AML_MAX_BODY_BYTES", "1048576")),
        max_concurrency=int(os.environ.get("SYUNE_AML_MAX_CONCURRENCY", "4")),
        queue_wait_seconds=float(os.environ.get("SYUNE_AML_QUEUE_WAIT_SECONDS", "1")),
        min_free_bytes=int(os.environ.get("SYUNE_AML_MIN_FREE_BYTES", "1073741824")),
    ))


def cleanup_evaluation_state(state_root: Path, *, confirm_root: str) -> None:
    """Delete one explicitly confirmed, marked AML evaluation state tree."""
    root = Path(state_root)
    if not root.is_absolute() or root.is_symlink():
        raise ValueError("cleanup requires an absolute non-symlink evaluation root")
    resolved = root.resolve(strict=True)
    if len(resolved.parts) < 3 or resolved == Path(resolved.anchor):
        raise ValueError("cleanup refuses broad filesystem roots")
    if str(resolved) != confirm_root:
        raise ValueError("cleanup confirmation must exactly match the resolved evaluation root")
    marker = resolved / "metadata" / ".syune-aml-evaluation"
    if not marker.is_file() or marker.is_symlink():
        raise ValueError("cleanup requires the AML evaluation ownership marker")
    shutil.rmtree(resolved)


__all__ = ["AdapterSettings", "app_from_environment", "cleanup_evaluation_state", "create_app"]
