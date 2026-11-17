"""Frozen, strict records for dataset references.

A scene reference or reference asset is never a purchasable product, a catalog
record or a product binding. Identifiers are namespaced by source so SSR, MIDI and
FUTURE records cannot collide with each other or with ABO product IDs.
"""

import math
import re
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictInt,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0.0"

MAX_ASSET_BYTES = 15 * 1024 * 1024
MAX_ASSET_TRIANGLES = 100_000
MAX_TEXTURE_PX = 2048

_WINDOWS_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.I)


def _single_line(value: str) -> str:
    if value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Text must be trimmed and single-line")
    return value


def check_relative_path(value: str) -> str:
    """Accept only portable, relative, forward-slash paths that stay in their root."""
    if not value or len(value) > 240:
        raise ValueError("Path must be 1-240 characters")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ValueError("Path must be relative and use forward slashes")
    for part in value.split("/"):
        if part in ("", ".", ".."):
            raise ValueError("Path has an empty, '.' or '..' component")
        if part != part.rstrip(" .") or _WINDOWS_RESERVED.match(part):
            raise ValueError("Path component is not portable")
        if any(ord(c) < 32 or c in '<>"|?*' for c in part):
            raise ValueError("Path component has a forbidden character")
    return value


Text = Annotated[
    str, Field(min_length=1, max_length=2048), AfterValidator(_single_line)
]
Identifier = Annotated[
    str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Version = Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
UtcTimestamp = Annotated[
    str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
]
RelPath = Annotated[str, AfterValidator(check_relative_path)]
Meters = Annotated[FiniteFloat, Field(gt=0, le=1000)]
Vec3 = tuple[FiniteFloat, FiniteFloat, FiniteFloat]
Quat = tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]

SourceId = Literal["ssr_3dfront", "midi_3dfront", "future_3d"]
Permission = Literal["allowed", "denied", "unknown"]
Split = Literal["train", "val", "test", "unknown"]
Tier = Literal["canonical", "reference_only"]
CheckStatus = Literal["PASS", "FAIL", "NOT_VERIFIABLE"]
ExclusionCode = Literal[
    "irregular_room",
    "non_planar_floor_or_ceiling",
    "invalid_dimensions",
    "duplicate_identity",
    "unmapped_category",
    "tilted_object",
    "non_quarter_turn_rotation",
    "unknown_pivot_or_scale",
    "outside_room",
    "collision",
    "missing_dependency",
    "unsafe_payload",
    "budget_exceeded",
    "unresolved_join",
    "malformed_record",
]

_NAMESPACE = {"ssr_3dfront": "ssr", "midi_3dfront": "midi", "future_3d": "future"}


class Frozen(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @field_validator("*", mode="after")
    @classmethod
    def _finite_and_clean(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite number")
        if isinstance(value, str):
            _single_line(value)
        return value


def namespaced(source: SourceId, *parts: str) -> str:
    """Build ``<namespace>:<part>:<part>`` identifiers, e.g. ``ssr:<scene>:<room>``."""
    return ":".join((_NAMESPACE[source], *parts))


class PermissionRecord(Frozen):
    """Per-use permission. ``unknown`` is treated exactly like ``denied``."""

    local_research: Permission
    derived_metadata: Permission
    public_geometry: Permission
    public_images: Permission
    provider_disclosure: Permission
    evidence: Text
    decided_by: Text
    decided_utc: UtcTimestamp

    def allows(self, *uses: str) -> bool:
        return all(getattr(self, use) == "allowed" for use in uses)


class SourceFile(Frozen):
    path: RelPath
    size_bytes: StrictInt = Field(ge=0)
    sha256: Digest


class SourceManifest(Frozen):
    schema_version: Version = SCHEMA_VERSION
    source: SourceId
    origin_url: Annotated[str, Field(pattern=r"^https://[^\s]+$", max_length=512)]
    revision: Annotated[str, Field(min_length=7, max_length=64)]
    retrieved_utc: UtcTimestamp
    files: tuple[SourceFile, ...]
    permission: PermissionRecord

    @model_validator(mode="after")
    def _unique_sorted_files(self) -> Self:
        paths = [f.path for f in self.files]
        if paths != sorted(paths) or len({p.casefold() for p in paths}) != len(paths):
            raise ValueError(
                "Source files must be unique (case-insensitive) and sorted"
            )
        return self


class RoomExtent(Frozen):
    width_m: Meters
    depth_m: Meters
    height_m: Meters


class Footprint(Frozen):
    """Canonical lower-left footprint after the recorded basis transform."""

    x_m: FiniteFloat
    y_m: FiniteFloat
    width_m: Meters
    depth_m: Meters
    height_m: Meters
    yaw_quarter_turns: Literal[0, 1, 2, 3]


class SceneObject(Frozen):
    source_object_id: Identifier
    jid: Identifier | None = None
    raw_category: Text
    category: Identifier | None = None
    size_raw: Vec3
    position_raw: Vec3
    rotation_raw_xyzw: Quat
    footprint: Footprint | None = None
    exclusion: ExclusionCode | None = None

    @model_validator(mode="after")
    def _admitted_or_excluded(self) -> Self:
        admitted = self.footprint is not None and self.category is not None
        if admitted == (self.exclusion is not None):
            raise ValueError("Object needs a footprint and category, or an exclusion")
        return self


class CheckResult(Frozen):
    name: Identifier
    status: CheckStatus
    detail: Text | None = None


class SceneReference(Frozen):
    schema_version: Version = SCHEMA_VERSION
    reference_id: Identifier
    source: Literal["ssr_3dfront", "midi_3dfront"]
    source_revision: Annotated[str, Field(min_length=7, max_length=64)]
    source_sha256: Digest
    split: Split
    source_scene_id: Identifier
    source_room_id: Identifier
    tier: Tier
    room: RoomExtent
    openings: Literal["known", "unknown"]
    objects: tuple[SceneObject, ...] = Field(min_length=1, max_length=64)
    checks: tuple[CheckResult, ...]
    transform_version: Version
    category_map_version: Version

    @model_validator(mode="after")
    def _identity_and_tier(self) -> Self:
        expected = namespaced(self.source, self.source_scene_id, self.source_room_id)
        if self.reference_id != expected:
            raise ValueError("reference_id must be the namespaced scene/room identity")
        ids = [o.source_object_id for o in self.objects]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate object identity in scene")
        admitted = [o for o in self.objects if o.exclusion is None]
        if not admitted:
            raise ValueError("A scene reference needs at least one admitted object")
        if self.tier == "canonical" and (
            len(admitted) != len(self.objects)
            or any(o.footprint.yaw_quarter_turns != 0 for o in admitted)
        ):
            raise ValueError(
                "Canonical tier requires every object admitted at zero yaw"
            )
        names = [c.name for c in self.checks]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate check name")
        if self.openings == "unknown" and any(
            c.status == "PASS" and c.name.startswith(("door", "circulation"))
            for c in self.checks
        ):
            raise ValueError(
                "Door/circulation checks cannot pass with unknown openings"
            )
        return self


class ExclusionRecord(Frozen):
    schema_version: Version = SCHEMA_VERSION
    source: SourceId
    source_id: Identifier
    reason: ExclusionCode
    detail: Text


class ReferenceAsset(Frozen):
    """A visual reference mesh. Never a catalog product or product binding."""

    schema_version: Version = SCHEMA_VERSION
    asset_id: Identifier
    version: Version
    source_jid: Identifier
    source_files: tuple[SourceFile, ...] = Field(min_length=1)
    glb: SourceFile
    triangles: StrictInt = Field(gt=0, le=MAX_ASSET_TRIANGLES)
    max_texture_px: StrictInt = Field(ge=0, le=MAX_TEXTURE_PX)
    bounds_m: tuple[Meters, Meters, Meters]
    scale_evidence: Text
    converter: Text
    attribution: Text

    @model_validator(mode="after")
    def _identity_and_budget(self) -> Self:
        if self.asset_id != namespaced("future_3d", self.source_jid):
            raise ValueError("asset_id must be future:<jid>")
        if self.glb.size_bytes > MAX_ASSET_BYTES:
            raise ValueError("GLB exceeds the per-asset byte ceiling")
        if not self.glb.path.startswith("assets/") or not self.glb.path.endswith(
            ".glb"
        ):
            raise ValueError("GLB must live under assets/ with a .glb suffix")
        return self


PackFileKind = Literal["scenes", "exclusions", "assets", "glb", "sources"]


class PackFile(Frozen):
    path: RelPath
    kind: PackFileKind
    size_bytes: StrictInt = Field(ge=0)
    sha256: Digest
    records: StrictInt | None = Field(default=None, ge=0)


class PackManifest(Frozen):
    schema_version: Version = SCHEMA_VERSION
    pack_id: Identifier
    audience: Literal["local", "public"]
    created_utc: UtcTimestamp
    builder: Text
    transform_version: Version
    category_map_version: Version
    files: tuple[PackFile, ...]
    snapshot_id: Digest

    @model_validator(mode="after")
    def _files_unique_sorted(self) -> Self:
        paths = [f.path for f in self.files]
        if paths != sorted(paths) or len({p.casefold() for p in paths}) != len(paths):
            raise ValueError("Pack files must be unique (case-insensitive) and sorted")
        return self
