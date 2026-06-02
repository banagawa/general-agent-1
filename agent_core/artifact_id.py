from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ArtifactKind = Literal["FILE", "MODULE", "FUNC", "TEST"]

_PATH_KINDS = {"FILE", "MODULE"}
_SYMBOL_KINDS = {"FUNC", "TEST"}
_ALL_KINDS = _PATH_KINDS | _SYMBOL_KINDS


@dataclass(frozen=True)
class ArtifactID:
    kind: ArtifactKind
    path: str
    symbol: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in _ALL_KINDS:
            raise ValueError(f"unsupported artifact kind: {self.kind}")
        _validate_repo_path(self.path, "path")
        if self.kind in _PATH_KINDS:
            if self.symbol is not None:
                raise ValueError(f"{self.kind} artifact must not include symbol")
        else:
            if not isinstance(self.symbol, str) or not self.symbol.strip():
                raise ValueError(f"{self.kind} artifact requires non-empty symbol")
            if "::" in self.symbol or "/" in self.symbol or "\\" in self.symbol:
                raise ValueError("symbol must not contain separators")

    def __str__(self) -> str:
        if self.symbol is None:
            return f"{self.kind}::{self.path}"
        return f"{self.kind}::{self.path}::{self.symbol}"

    @classmethod
    def parse(cls, value: str) -> "ArtifactID":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("artifact id must be non-empty string")
        parts = value.split("::")
        if len(parts) == 2:
            kind, path = parts
            return cls(kind=kind, path=path)  # type: ignore[arg-type]
        if len(parts) == 3:
            kind, path, symbol = parts
            return cls(kind=kind, path=path, symbol=symbol)  # type: ignore[arg-type]
        raise ValueError("artifact id must have 2 or 3 parts")


def _validate_repo_path(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty string")
    if "\x00" in value:
        raise ValueError(f"{field_name} must not contain null bytes")
    normalized = value.replace("\\", "/")
    if value.startswith(("/", "\\")):
        raise ValueError(f"{field_name} must be workspace-relative")
    if len(value) >= 2 and value[1] == ":":
        raise ValueError(f"{field_name} must not include drive letters")
    if normalized.startswith("//"):
        raise ValueError(f"{field_name} must not be UNC path")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{field_name} must not contain empty, dot, or parent parts")


def artifact_for_file(path: str) -> ArtifactID:
    return ArtifactID("FILE", _normalize_relative_path(path))


def artifact_for_module(path: str) -> ArtifactID:
    return ArtifactID("MODULE", _normalize_relative_path(path))


def artifact_for_function(path: str, symbol: str) -> ArtifactID:
    return ArtifactID("FUNC", _normalize_relative_path(path), symbol)


def artifact_for_test(path: str, test_name: str) -> ArtifactID:
    return ArtifactID("TEST", _normalize_relative_path(path), test_name)


def _normalize_relative_path(path: str) -> str:
    _validate_repo_path(path, "path")
    return path.replace("\\", "/")


def resolve_artifact_path(artifact: ArtifactID | str, workspace_root: Path) -> Path:
    parsed = ArtifactID.parse(artifact) if isinstance(artifact, str) else artifact
    root = workspace_root.resolve()
    candidate = (root / parsed.path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("artifact path resolves outside workspace")
    return candidate
