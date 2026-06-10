"""Runtime helpers for Blender Python asset generation.

The module is import-safe outside Blender because bpy is imported only inside
run_blender_asset_plan.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MATERIALS: dict[str, tuple[float, float, float, float]] = {
    "neutral": (0.55, 0.58, 0.54, 1.0),
    "safe": (0.22, 0.58, 0.52, 1.0),
    "hazard": (0.82, 0.18, 0.14, 1.0),
    "objective": (0.92, 0.72, 0.18, 1.0),
    "exit": (0.14, 0.62, 0.34, 1.0),
    "ui": (0.18, 0.38, 0.72, 1.0),
    "door": (0.55, 0.34, 0.22, 1.0),
    "ramp": (0.30, 0.42, 0.62, 1.0),
}

# PBR surface params per material key: (roughness, metallic, emission_strength).
# objective/exit get a slight emission so they read as interactive at a glance.
MATERIAL_PBR: dict[str, tuple[float, float, float]] = {
    "neutral": (0.85, 0.0, 0.0),
    "safe": (0.7, 0.0, 0.0),
    "hazard": (0.5, 0.1, 0.6),
    "objective": (0.4, 0.2, 1.2),
    "exit": (0.45, 0.1, 0.9),
    "ui": (0.6, 0.0, 0.4),
    "door": (0.75, 0.05, 0.0),
    "ramp": (0.8, 0.0, 0.0),
    "collision": (1.0, 0.0, 0.0),
}

DEFAULT_DIMENSIONS_CM: dict[str, tuple[float, float, float]] = {
    "modular_wall": (400.0, 30.0, 300.0),
    "door": (160.0, 24.0, 260.0),
    "ramp": (300.0, 220.0, 120.0),
    "hazard_marker": (110.0, 110.0, 130.0),
    "objective_prop": (120.0, 120.0, 170.0),
    "exit_gate": (240.0, 40.0, 300.0),
    "ui_proxy_mesh": (190.0, 6.0, 110.0),
    "generic_greybox": (100.0, 100.0, 100.0),
}


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "asset"


def _unreal_identifier(value: str) -> str:
    identifier = _slug(value)
    if not identifier[0].isalpha():
        identifier = f"fa_{identifier}"
    return identifier


def _asset_name(job: dict[str, Any]) -> str:
    return _unreal_identifier(str(job["asset_name"]))


def _dimensions(job: dict[str, Any]) -> tuple[float, float, float]:
    kind = str(job.get("asset_kind") or "generic_greybox")
    raw = job.get("dimensions_cm") or DEFAULT_DIMENSIONS_CM.get(kind)
    if not raw or len(raw) != 3:
        raw = DEFAULT_DIMENSIONS_CM["generic_greybox"]
    return (float(raw[0]), float(raw[1]), float(raw[2]))


def _material_key(job: dict[str, Any]) -> str:
    return str(job.get("material_key") or "neutral")


def _collection_name(job: dict[str, Any]) -> str:
    return str(job.get("collection") or "GameplayGreybox")


def _asset_kind(job: dict[str, Any]) -> str:
    return str(job.get("asset_kind") or "generic_greybox")


def _collision_name(job: dict[str, Any]) -> str:
    explicit = job.get("collision_name")
    if explicit:
        collision_name = _unreal_identifier(str(explicit))
    else:
        collision_name = f"ucx_{_asset_name(job)}_00"
    if not collision_name.startswith("ucx_"):
        collision_name = f"ucx_{_asset_name(job)}_00"
    return collision_name.replace("ucx_", "UCX_", 1)


def _ensure_dir(filepath: str) -> None:
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


def _write_manifest(filepath: str, manifest: dict[str, Any]) -> None:
    _ensure_dir(filepath)
    Path(filepath).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def build_import_manifest(plan: dict[str, Any]) -> dict[str, Any]:
    scene_units = str(plan.get("scene_units") or "centimeters")
    assets: list[dict[str, Any]] = []
    for job in plan.get("jobs", []):
        assets.append(
            {
                "asset_name": _asset_name(job),
                "asset_kind": _asset_kind(job),
                "source_file": job["export_path"],
                "destination_path": job.get("unreal_path") or "/Game/Art/Generated",
                "collision_object": _collision_name(job),
                "material_key": _material_key(job),
                "dimensions_cm": list(_dimensions(job)),
                "gameplay_role": job["purpose"],
            }
        )
    return {
        "schema_version": "0.1",
        "generated_by": "fantasy-agent.blender-worker",
        "scene_units": scene_units,
        "import_settings": {
            "combine_meshes": False,
            "generate_missing_collision": False,
            "import_materials": True,
            "import_textures": False,
            "unit_scale": 1.0 if scene_units == "centimeters" else 100.0,
            "normal_import_method": "import_normals",
        },
        "assets": assets,
    }


def run_blender_asset_plan(
    plan: dict[str, Any],
    import_manifest_path: str = "generated/import-manifest.yaml",
) -> dict[str, Any]:
    import bpy  # type: ignore[import-not-found]

    _reset_scene(bpy, str(plan.get("scene_units") or "centimeters"))
    materials = {key: _make_material(bpy, key, color) for key, color in MATERIALS.items()}

    exported: list[str] = []
    for index, job in enumerate(plan.get("jobs", [])):
        export_path = str(job["export_path"])
        _ensure_dir(export_path)
        objects = _create_asset_objects(bpy, job, index, materials)
        _export_asset(bpy, export_path, str(plan.get("export_format") or "fbx"), objects)
        exported.append(export_path)

    manifest = build_import_manifest(plan)
    _write_manifest(import_manifest_path, manifest)
    return {
        "exported_assets": exported,
        "import_manifest": import_manifest_path,
        "assets": manifest["assets"],
    }


def _reset_scene(bpy: Any, scene_units: str) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.01 if scene_units == "centimeters" else 1.0


def _ensure_collection(bpy: Any, name: str) -> Any:
    existing = bpy.data.collections.get(name)
    if existing:
        return existing
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def _link_to_collection(bpy: Any, obj: Any, collection_name: str) -> None:
    collection = _ensure_collection(bpy, collection_name)
    if collection.objects.get(obj.name) is None:
        collection.objects.link(obj)
    for linked_collection in list(obj.users_collection):
        if linked_collection.name != collection.name:
            linked_collection.objects.unlink(obj)


def _make_material(bpy: Any, name: str, color: tuple[float, float, float, float]) -> Any:
    material_name = f"MI_FA_{name}"
    existing = bpy.data.materials.get(material_name)
    if existing is not None:
        return existing
    material = bpy.data.materials.new(material_name)
    material.diffuse_color = color  # viewport / fallback shading
    roughness, metallic, emission = MATERIAL_PBR.get(name, (0.85, 0.0, 0.0))
    # Build a Principled BSDF node tree so the material exports as real PBR.
    try:
        material.use_nodes = True
        nodes = material.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = metallic
            if emission > 0.0:
                # Emission color input name differs across versions; set defensively.
                if "Emission Color" in bsdf.inputs:
                    bsdf.inputs["Emission Color"].default_value = color
                elif "Emission" in bsdf.inputs:
                    bsdf.inputs["Emission"].default_value = color
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = emission
    except Exception:  # noqa: BLE001 - fall back to flat diffuse if nodes unavailable
        material.use_nodes = False
    return material


def _assign_material(obj: Any, material: Any) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)


def _set_active(bpy: Any, obj: Any) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _cube(
    bpy: Any,
    name: str,
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    material: Any,
    collection: str,
) -> Any:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    _set_active(bpy, obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _assign_material(obj, material)
    _link_to_collection(bpy, obj, collection)
    return obj


def _floor_origin(bpy: Any, obj: Any) -> None:
    _set_active(bpy, obj)
    bpy.context.scene.cursor.location = (obj.location.x, obj.location.y, 0.0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")


def _collision_cube(
    bpy: Any,
    job: dict[str, Any],
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    collection: str,
) -> Any:
    material = _make_material(bpy, "collision", (0.0, 0.0, 0.0, 0.12))
    obj = _cube(bpy, _collision_name(job), dimensions, location, material, collection)
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["unreal_collision"] = True
    return obj


def _mark_collision(obj: Any) -> Any:
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj["unreal_collision"] = True
    return obj


def _collision_for_kind(
    bpy: Any,
    job: dict[str, Any],
    kind: str,
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    collection: str,
) -> Any:
    """Collision proxy whose shape matches the visible geometry per kind.

    - ramp: wedge (so the slope is solid, not a tall box)
    - hazard_marker: cylinder (approximates the cone footprint)
    - everything else: box (correct for walls/doors/gates/props/ui)
    """
    material = _make_material(bpy, "collision", (0.0, 0.0, 0.0, 0.12))
    name = _collision_name(job)
    x, y, z = dimensions
    if kind == "ramp":
        obj = _wedge_mesh(bpy, name, dimensions, location, material, collection)
    elif kind == "hazard_marker":
        obj = _cylinder(
            bpy, name, max(x, y) / 2.0, z, (location[0], location[1], z / 2.0), material, collection
        )
    else:
        obj = _cube(bpy, name, dimensions, location, material, collection)
    return _mark_collision(obj)


def _bevel_edges(bpy: Any, obj: Any, width: float = 2.5, segments: int = 2) -> None:
    """Bake a small chamfer onto a mesh's hard corners for a game-ready look.

    Best-effort: a Bevel modifier applied destructively. Never blocks export.
    """
    if getattr(obj, "type", None) != "MESH":
        return
    try:
        _set_active(bpy, obj)
        modifier = obj.modifiers.new(name="FA_Bevel", type="BEVEL")
        modifier.width = width  # centimeters (scene unit)
        modifier.segments = segments
        modifier.limit_method = "ANGLE"
        modifier.angle_limit = 1.05  # ~60deg, only real corners
        bpy.ops.object.modifier_apply(modifier="FA_Bevel")
    except Exception:  # noqa: BLE001 - bevel is cosmetic; never block export
        try:
            if obj.modifiers.get("FA_Bevel") is not None:
                obj.modifiers.remove(obj.modifiers["FA_Bevel"])
        except Exception:  # noqa: BLE001
            pass


def _smart_uv_unwrap(bpy: Any, obj: Any) -> None:
    """Generate non-overlapping UVs for a mesh so textures map predictably."""
    if getattr(obj, "type", None) != "MESH":
        return
    try:
        _set_active(bpy, obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:  # noqa: BLE001 - UV is best-effort; never block export
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:  # noqa: BLE001
            pass


def _wedge_mesh(
    bpy: Any,
    name: str,
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    material: Any,
    collection: str,
) -> Any:
    x, y, z = dimensions
    hx = x / 2.0
    hy = y / 2.0
    verts = [
        (-hx, -hy, 0.0),
        (hx, -hy, 0.0),
        (-hx, hy, 0.0),
        (hx, hy, 0.0),
        (hx, -hy, z),
        (hx, hy, z),
    ]
    faces = [
        (0, 1, 3, 2),
        (1, 4, 5, 3),
        (0, 2, 5, 4, 1),
        (2, 3, 5),
        (0, 4, 5, 2),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    _assign_material(obj, material)
    _link_to_collection(bpy, obj, collection)
    return obj


def _cone(
    bpy: Any,
    name: str,
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    material: Any,
    collection: str,
) -> Any:
    x, y, z = dimensions
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=max(x, y) / 2.0, radius2=12.0, depth=z)
    obj = bpy.context.object
    obj.name = name
    obj.location = location
    _assign_material(obj, material)
    _link_to_collection(bpy, obj, collection)
    return obj


def _cylinder(
    bpy: Any,
    name: str,
    radius: float,
    depth: float,
    location: tuple[float, float, float],
    material: Any,
    collection: str,
) -> Any:
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    _assign_material(obj, material)
    _link_to_collection(bpy, obj, collection)
    return obj


def _create_asset_objects(
    bpy: Any,
    job: dict[str, Any],
    index: int,
    materials: dict[str, Any],
) -> list[Any]:
    asset_name = _asset_name(job)
    kind = _asset_kind(job)
    dims = _dimensions(job)
    material = materials.get(_material_key(job), materials["neutral"])
    collection = _collection_name(job)
    x_offset = index * 520.0
    base = (x_offset, 0.0, 0.0)

    builders = {
        "modular_wall": _asset_modular_wall,
        "door": _asset_door,
        "ramp": _asset_ramp,
        "hazard_marker": _asset_hazard_marker,
        "objective_prop": _asset_objective_prop,
        "exit_gate": _asset_exit_gate,
        "ui_proxy_mesh": _asset_ui_proxy_mesh,
        "generic_greybox": _asset_generic_greybox,
    }
    objects = builders.get(kind, _asset_generic_greybox)(
        bpy, asset_name, dims, base, material, collection
    )
    # Bevel hard corners for a game-ready silhouette, then UV-unwrap (bevel
    # changes topology, so UV must come after). Collision proxies are added
    # afterwards and stay untouched. ui_proxy_mesh stays flat (thin billboard).
    for obj in objects:
        if kind != "ui_proxy_mesh":
            _bevel_edges(bpy, obj)
        _smart_uv_unwrap(bpy, obj)
    objects.append(
        _collision_for_kind(bpy, job, kind, dims, (base[0], base[1], dims[2] / 2.0), collection)
    )
    for obj in objects:
        _floor_origin(bpy, obj)
        obj["fantasy_agent_asset_kind"] = kind
        obj["fantasy_agent_role"] = job["purpose"]
    return objects


def _asset_modular_wall(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    x, y, z = dims
    obj = _cube(bpy, asset_name, dims, (base[0], base[1], z / 2.0), material, collection)
    trim = _cube(
        bpy,
        f"{asset_name}_readability_trim",
        (x, y + 4.0, 18.0),
        (base[0], base[1], z - 24.0),
        material,
        collection,
    )
    return [obj, trim]


def _asset_door(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    x, y, z = dims
    side = 18.0
    header = 22.0
    return [
        _cube(
            bpy,
            asset_name,
            (x * 0.54, y, z * 0.82),
            (base[0], base[1], z * 0.41),
            material,
            collection,
        ),
        _cube(
            bpy,
            f"{asset_name}_frame_l",
            (side, y + 8.0, z),
            (base[0] - x / 2.0, base[1], z / 2.0),
            material,
            collection,
        ),
        _cube(
            bpy,
            f"{asset_name}_frame_r",
            (side, y + 8.0, z),
            (base[0] + x / 2.0, base[1], z / 2.0),
            material,
            collection,
        ),
        _cube(
            bpy,
            f"{asset_name}_frame_top",
            (x + side, y + 8.0, header),
            (base[0], base[1], z - header / 2.0),
            material,
            collection,
        ),
    ]


def _asset_ramp(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    obj = _wedge_mesh(bpy, asset_name, dims, base, material, collection)
    lip = _cube(
        bpy,
        f"{asset_name}_edge_readability",
        (dims[0], 10.0, 12.0),
        (base[0], base[1] + dims[1] / 2.0, 12.0),
        material,
        collection,
    )
    return [obj, lip]


def _asset_hazard_marker(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    x, y, z = dims
    cone = _cone(bpy, asset_name, dims, (base[0], base[1], z / 2.0), material, collection)
    base_plate = _cube(
        bpy,
        f"{asset_name}_base",
        (x * 1.15, y * 1.15, 10.0),
        (base[0], base[1], 5.0),
        material,
        collection,
    )
    return [cone, base_plate]


def _asset_objective_prop(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    x, _y, z = dims
    pedestal = _cylinder(
        bpy, asset_name, x * 0.28, z * 0.45, (base[0], base[1], z * 0.225), material, collection
    )
    beacon = _cube(
        bpy,
        f"{asset_name}_beacon",
        (x * 0.45, x * 0.45, z * 0.30),
        (base[0], base[1], z * 0.67),
        material,
        collection,
    )
    return [pedestal, beacon]


def _asset_exit_gate(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    x, y, z = dims
    post = 24.0
    return [
        _cube(
            bpy,
            asset_name,
            (post, y, z),
            (base[0] - x / 2.0, base[1], z / 2.0),
            material,
            collection,
        ),
        _cube(
            bpy,
            f"{asset_name}_post_r",
            (post, y, z),
            (base[0] + x / 2.0, base[1], z / 2.0),
            material,
            collection,
        ),
        _cube(
            bpy,
            f"{asset_name}_header",
            (x + post, y, 28.0),
            (base[0], base[1], z - 14.0),
            material,
            collection,
        ),
        _cube(
            bpy,
            f"{asset_name}_trigger_plane",
            (x * 0.70, 4.0, z * 0.70),
            (base[0], base[1], z * 0.35),
            material,
            collection,
        ),
    ]


def _asset_ui_proxy_mesh(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    x, y, z = dims
    panel = _cube(bpy, asset_name, dims, (base[0], base[1], z / 2.0), material, collection)
    objective_slot = _cube(
        bpy,
        f"{asset_name}_objective_slot",
        (x * 0.76, y + 2.0, z * 0.16),
        (base[0], base[1] - 4.0, z * 0.68),
        material,
        collection,
    )
    meter = _cube(
        bpy,
        f"{asset_name}_pressure_meter",
        (x * 0.58, y + 2.0, z * 0.10),
        (base[0], base[1] - 4.0, z * 0.34),
        material,
        collection,
    )
    return [panel, objective_slot, meter]


def _asset_generic_greybox(
    bpy: Any,
    asset_name: str,
    dims: tuple[float, float, float],
    base: tuple[float, float, float],
    material: Any,
    collection: str,
) -> list[Any]:
    return [_cube(bpy, asset_name, dims, (base[0], base[1], dims[2] / 2.0), material, collection)]


def _export_asset(bpy: Any, export_path: str, export_format: str, objects: list[Any]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    suffix = Path(export_path).suffix.lower()
    format_key = export_format.lower()
    if suffix == ".glb" or format_key == "glb":
        bpy.ops.export_scene.gltf(
            filepath=export_path,
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_normals=True,
            export_tangents=True,
            export_materials="EXPORT",
            export_vertex_color="MATERIAL",
        )
        return
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=True,
        object_types={"MESH"},
        apply_unit_scale=True,
        add_leaf_bones=False,
        bake_space_transform=False,
        mesh_smooth_type="FACE",
    )
