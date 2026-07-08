from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.models import ForecastProduct, ProductStatus
from .server_client import server_client
from .server_runs import parse_run_key

logger = logging.getLogger(__name__)

PRODUCT_ROOT_KEY = "products"
PRODUCT_EXTENSIONS = {".json", ".geojson", ".png", ".csv", ".tif", ".tiff", ".nc"}
SKIP_BASENAMES = {"state.json", "postprocess.json", "product_manifest.json"}
SERVER_PATH_PREFIX = "server:products/"
SUBPATH_PATTERN = re.compile(r"^[^/]+/[^/]+/\d{4}/[^/]+$")
DEFAULT_PORTAL_REGIONS = ["Beijing", "InnerMG", "Shaanxi", "Yulin", "China"]
DEFAULT_PORTAL_SEASONS = ["spring", "autumn"]


@dataclass(frozen=True)
class ProductRef:
    raw: str
    kind: str  # subpath | run_key
    subpath: str | None
    season: str
    region: str
    run_id: str

    @property
    def cache_key(self) -> str:
        return self.subpath or self.raw


def parse_product_ref(ref: str) -> ProductRef:
    normalized = ref.strip().strip("/")
    if not normalized:
        raise ValueError("product ref is required")
    parts = [part for part in normalized.split("/") if part]
    if len(parts) == 4 and parts[2].isdigit() and len(parts[2]) == 4:
        return ProductRef(
            raw=normalized,
            kind="subpath",
            subpath=normalized,
            season=parts[0],
            region=parts[1],
            run_id=parts[3],
        )
    if len(parts) == 3:
        return ProductRef(
            raw=normalized,
            kind="run_key",
            subpath=None,
            season=parts[0],
            region=parts[1],
            run_id=parts[2],
        )
    raise ValueError("ref must be season/region/run_id or season/region/year/day")


def list_products(ref: str) -> list[dict[str, Any]]:
    if not server_client.configured:
        return []
    parsed = parse_product_ref(ref)
    subpath = resolve_subpath(parsed)
    if not subpath:
        return []
    return list_products_at_subpath(subpath, parsed)


def list_run_products(run_key: str) -> list[dict[str, Any]]:
    return list_products(run_key)


def list_latest_portal_bundles(
    *,
    regions: list[str] | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    if not server_client.configured:
        return []
    target_regions = regions or DEFAULT_PORTAL_REGIONS
    seasons = [season.lower()] if season else DEFAULT_PORTAL_SEASONS
    bundles: list[dict[str, Any]] = []
    for region in target_regions:
        bundle = latest_region_bundle(region, seasons)
        if bundle:
            bundles.append(bundle)
    return bundles


def latest_region_bundle(region: str, seasons: list[str]) -> dict[str, Any] | None:
    candidates: list[tuple[str, str, str, str]] = []
    region_key = region.lower()
    for season_name in seasons:
        for year in sorted(_directory_names(f"{season_name}/{region_key}"), reverse=True):
            for day in sorted(_directory_names(f"{season_name}/{region_key}/{year}"), reverse=True):
                if not re.fullmatch(r"\d{4}", day):
                    continue
                subpath = f"{season_name}/{region_key}/{year}/{day}"
                if load_manifest_products(subpath):
                    candidates.append((year, day, season_name, subpath))
                    break
            if candidates and candidates[-1][2] == season_name:
                break
    if not candidates:
        return None
    _, day, season_name, subpath = sorted(candidates, reverse=True)[0]
    parsed = parse_product_ref(subpath)
    products = list_products_at_subpath(subpath, parsed)
    release_time = max((item.get("release_time") or "" for item in products), default="")
    return {
        "region": region,
        "region_key": region_key,
        "season": season_name,
        "subpath": subpath,
        "day": day,
        "release_time": release_time,
        "products": products,
    }


def _directory_names(path: str) -> list[str]:
    try:
        entries = server_client.list_directory(PRODUCT_ROOT_KEY, path)
    except HTTPException:
        return []
    return [
        str(item.get("name"))
        for item in entries
        if item.get("type") == "directory" and item.get("name")
    ]


def sync_products(db: Session, ref: str) -> dict[str, Any]:
    if not server_client.configured:
        raise HTTPException(status_code=503, detail="SERVER_API_BASE_URL is not configured")

    parsed = parse_product_ref(ref)
    subpath = resolve_subpath(parsed)
    if not subpath:
        raise HTTPException(status_code=404, detail=f"无法定位产品目录: {ref}")

    files = collect_product_files(subpath)
    manifest_products = load_manifest_products(subpath)
    candidates = manifest_products or files
    if not candidates:
        return {
            "ref": ref,
            "subpath": subpath,
            "indexed_count": 0,
            "downloaded_count": 0,
            "message": "未找到可索引的产品文件",
        }

    cache_root = Path(settings.LOCAL_PRODUCTS_DIR) / sanitize_path(parsed.cache_key)
    cache_root.mkdir(parents=True, exist_ok=True)

    indexed_count = 0
    downloaded_count = 0
    for item in candidates:
        rel_path = item["path"]
        local_path = cache_root / PurePosixPath(rel_path.replace("\\", "/"))
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if not local_path.is_file():
            try:
                dl_timeout = (
                    float(settings.SERVER_PRODUCT_DOWNLOAD_TIMEOUT)
                    if "pollen_map_forecast" in rel_path.replace("\\", "/")
                    else None
                )
                content = server_client.download_file(PRODUCT_ROOT_KEY, rel_path, timeout=dl_timeout)
                local_path.write_bytes(content)
                downloaded_count += 1
            except HTTPException as exc:
                logger.warning("product download failed for %s: %s", rel_path, exc.detail)
                continue

        product_name = f"{parsed.raw}:{PurePosixPath(rel_path).name}"
        metadata = classify_product_file(rel_path, item.get("manifest"))
        existing = (
            db.query(ForecastProduct)
            .filter(ForecastProduct.product_name == product_name)
            .first()
        )
        if item.get("mtime"):
            release_time = datetime.fromtimestamp(item["mtime"], tz=timezone.utc)
        else:
            release_time = datetime.now(tz=timezone.utc)

        payload = {
            "product_name": product_name,
            "product_type": metadata["product_type"],
            "status": ProductStatus.READY,
            "region": parsed.region,
            "pollen_type": metadata.get("pollen_type") or parsed.region,
            "resolution": metadata.get("resolution") or "native",
            "workflow_node": "postprocess",
            "workflow_version": parsed.run_id,
            "file_path": str(local_path),
            "subtype": metadata.get("subtype"),
            "variable": metadata.get("variable"),
            "unit": metadata.get("unit"),
            "bounds_json": metadata.get("bounds_json"),
            "lead_time": metadata.get("lead_time"),
            "source_run_id": parsed.run_id,
            "capability_status": metadata.get("capability_status"),
            "release_time": release_time,
            "is_published": True,
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(ForecastProduct(**payload))
        indexed_count += 1

    db.commit()
    return {
        "ref": ref,
        "subpath": subpath,
        "indexed_count": indexed_count,
        "downloaded_count": downloaded_count,
        "source": "server",
    }


def sync_run_products(db: Session, run_key: str) -> dict[str, Any]:
    result = sync_products(db, run_key)
    result["run_key"] = run_key
    return result


def resolve_subpath(parsed: ProductRef) -> str | None:
    if parsed.subpath and subpath_exists(parsed.subpath):
        return parsed.subpath
    if parsed.kind == "subpath":
        return parsed.subpath

    detail = None
    run_root = ""
    try:
        detail = server_client.run_detail_live(parsed.season, parsed.region, parsed.run_id)
        run_root = (detail.data or {}).get("run_root") or ""
    except HTTPException:
        pass

    return resolve_products_subpath(run_root, parsed.season, parsed.region, parsed.run_id)


def subpath_exists(subpath: str) -> bool:
    try:
        entries = server_client.list_directory(PRODUCT_ROOT_KEY, subpath)
    except HTTPException:
        return False
    return bool(entries)


def resolve_products_subpath(run_root: str, season: str, region: str, run_id: str) -> str | None:
    normalized = run_root.replace("\\", "/")
    marker = "output/predict/"
    if marker in normalized:
        candidate = normalized.split(marker, 1)[1].strip("/")
        if subpath_exists(candidate):
            return candidate

    match = re.match(r"^(\d{8})(pre\d+)", run_id)
    if not match:
        return None
    start_date, pre = match.group(1), match.group(2)
    variant_suffix = "_caoditu" if "_caoditu" in run_id.lower() else ""
    year = start_date[:4]
    mmdd = start_date[4:8]
    region_variants = {region, region.lower(), region.capitalize()}
    season_variants = {season, season.lower()}
    candidates: list[str] = []
    for season_name in season_variants:
        for region_name in region_variants:
            candidates.extend(
                [
                    f"{season_name}/{region_name}/{year}/{mmdd}{variant_suffix}",
                    f"{season_name}/{region_name}/{year}/{mmdd}",
                    f"{season_name}/{region_name}/{year}/{run_id}",
                    f"{season_name}/{region_name}/{year}/{start_date}{pre}",
                ]
            )

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if subpath_exists(candidate):
            return candidate
    return None


def list_products_at_subpath(subpath: str, parsed: ProductRef) -> list[dict[str, Any]]:
    files = collect_product_files(subpath)
    manifest_products = load_manifest_products(subpath)
    indexed = manifest_products or files
    return [
        serialize_server_product(
            item,
            ref=parsed.raw,
            season=parsed.season,
            region=parsed.region,
            run_id=parsed.run_id,
        )
        for item in indexed
    ]


def collect_product_files(subpath: str) -> list[dict[str, Any]]:
    try:
        tree = server_client.file_tree(PRODUCT_ROOT_KEY, subpath, depth=4)
    except HTTPException as exc:
        raise HTTPException(status_code=502, detail=f"读取服务器产品目录失败: {exc.detail}") from exc

    files: list[dict[str, Any]] = []
    _walk_tree(tree, files)
    return files


def load_manifest_products(subpath: str) -> list[dict[str, Any]] | None:
    manifest_names = [
        f"{subpath}/products/product_manifest.json",
        f"{subpath}/product_manifest.json",
    ]
    for manifest_path in manifest_names:
        try:
            raw = server_client.download_file(PRODUCT_ROOT_KEY, manifest_path)
            payload = json.loads(raw.decode("utf-8"))
        except (HTTPException, json.JSONDecodeError, UnicodeDecodeError):
            continue
        entries = normalize_manifest(payload)
        if not entries:
            continue
        products: list[dict[str, Any]] = []
        for entry in entries:
            rel = entry.get("path") or entry.get("file") or entry.get("name")
            if not rel:
                continue
            rel_path = str(PurePosixPath(subpath) / PurePosixPath(str(rel).replace("\\", "/")))
            products.append(
                {
                    "path": rel_path,
                    "mtime": entry.get("mtime"),
                    "manifest": entry,
                }
            )
        return products
    return None


def normalize_manifest(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("products"), list):
            return payload["products"]
        if isinstance(payload.get("items"), list):
            return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def _walk_tree(node: dict[str, Any], files: list[dict[str, Any]]) -> None:
    node_type = node.get("type")
    rel_path = str(node.get("path") or "")
    if node_type == "file":
        if is_product_file(rel_path):
            files.append({"path": rel_path, "mtime": node.get("mtime")})
        return
    for child in node.get("children") or []:
        _walk_tree(child, files)


def is_product_file(path: str) -> bool:
    name = PurePosixPath(path.replace("\\", "/")).name
    if name in SKIP_BASENAMES:
        return False
    suffix = PurePosixPath(path).suffix.lower()
    if suffix not in PRODUCT_EXTENSIONS:
        return False
    lowered = path.lower()
    if "/logs/" in lowered or name.startswith("rsl."):
        return False
    return True


def classify_product_file(path: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest or {}
    lowered = path.lower()
    name = PurePosixPath(path).name.lower()
    product_type = manifest.get("type") or manifest.get("product_type") or "artifact"
    subtype = manifest.get("subtype")
    variable = manifest.get("variable")
    unit = manifest.get("unit")
    lead_time = manifest.get("lead_time")
    capability_status = manifest.get("capability_status")
    bounds_json = None
    if manifest.get("bounds"):
        bounds_json = json.dumps(manifest["bounds"])

    if name == "city_forecast.json" or product_type == "city_forecast":
        product_type = "city_forecast"
    elif name == "pollen_map_animation.json" or product_type == "pollen_map_animation":
        product_type = "pollen_map_animation"
    elif name == "pollen_map_forecast.json" or product_type == "pollen_map_forecast":
        product_type = "pollen_map_forecast"
    elif name.endswith(".png"):
        product_type = "map_png" if "/plots/" in lowered else "png_overlay"
    elif name.endswith(".overlay.json") or product_type in {"png_overlay", "png_overlay_metadata"}:
        product_type = "png_overlay_metadata"
    elif name.endswith(".geojson") or product_type == "geojson":
        product_type = "geojson"
    elif name.startswith("wrfout"):
        product_type = "wrfout"
    elif name.endswith(".json"):
        product_type = manifest.get("type") or "json"

    pollen_type = manifest.get("pollen_type") or manifest.get("region") or "pollen"
    resolution = manifest.get("resolution") or ("plot" if "/plots/" in lowered else "native")
    return {
        "product_type": product_type,
        "subtype": subtype,
        "variable": variable,
        "unit": unit,
        "lead_time": lead_time,
        "capability_status": capability_status,
        "bounds_json": bounds_json,
        "pollen_type": pollen_type,
        "resolution": resolution,
    }


def serialize_server_product(
    item: dict[str, Any],
    *,
    ref: str,
    season: str,
    region: str,
    run_id: str,
) -> dict[str, Any]:
    rel_path = item["path"]
    metadata = classify_product_file(rel_path, item.get("manifest"))
    release_time = None
    if item.get("mtime"):
        release_time = datetime.fromtimestamp(item["mtime"], tz=timezone.utc).isoformat()
    return {
        "id": None,
        "product_name": f"{ref}:{PurePosixPath(rel_path).name}",
        "product_type": metadata["product_type"],
        "status": "ready",
        "region": region,
        "pollen_type": metadata.get("pollen_type") or region,
        "resolution": metadata.get("resolution") or "native",
        "workflow_node": "postprocess",
        "workflow_version": run_id,
        "file_path": f"{SERVER_PATH_PREFIX}{rel_path}",
        "subtype": metadata.get("subtype"),
        "variable": metadata.get("variable"),
        "unit": metadata.get("unit"),
        "bounds_json": metadata.get("bounds_json"),
        "lead_time": metadata.get("lead_time"),
        "source_run_id": run_id,
        "capability_status": metadata.get("capability_status"),
        "is_published": True,
        "release_time": release_time,
        "created_at": release_time,
        "server_path": rel_path,
        "download_url": build_server_download_url(rel_path),
    }


def fetch_server_json(path: str) -> Any:
    if ".." in path.replace("\\", "/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    cache_path = _server_json_cache_path(path)
    if cache_path.is_file():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("stale server json cache ignored: %s", cache_path)

    timeout = float(settings.SERVER_PRODUCT_DOWNLOAD_TIMEOUT)
    raw = server_client.download_file(PRODUCT_ROOT_KEY, path, timeout=timeout)
    max_bytes = int(settings.PRODUCT_INLINE_MAX_MB * 1024 * 1024)
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Product file exceeds inline limit ({settings.PRODUCT_INLINE_MAX_MB}MB)",
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON product: {exc}") from exc

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(raw)
    except OSError as exc:
        logger.warning("failed to cache server json %s: %s", path, exc)
    return payload


def _server_json_cache_path(path: str) -> Path:
    return Path(settings.LOCAL_PRODUCTS_DIR) / "_server_cache" / f"{sanitize_path(path)}.json"


def build_server_download_url(rel_path: str) -> str:
    encoded = urllib_parse_quote_path(rel_path)
    return f"{settings.API_V1_STR}/products/server/download?path={encoded}"


def urllib_parse_quote_path(path: str) -> str:
    import urllib.parse

    return urllib.parse.quote(path.replace("\\", "/"), safe="/")


def resolve_server_file_path(file_path: str) -> tuple[str, str] | None:
    if not file_path.startswith(SERVER_PATH_PREFIX):
        return None
    return PRODUCT_ROOT_KEY, file_path[len(SERVER_PATH_PREFIX) :]


def sanitize_path(value: str) -> str:
    return value.replace("\\", "_").replace("/", "__")


def merge_db_and_server_products(db_products: list[ForecastProduct], server_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for product in server_products:
        merged[product["product_name"]] = product
    for product in db_products:
        serialized = serialize_db_product(product)
        merged[product.product_name] = serialized
    return sorted(merged.values(), key=lambda item: item.get("release_time") or "", reverse=True)


def serialize_db_product(product: ForecastProduct) -> dict[str, Any]:
    release_time = product.release_time.isoformat() if product.release_time else None
    data = {
        "id": product.id,
        "product_name": product.product_name,
        "product_type": product.product_type,
        "status": product.status.value if hasattr(product.status, "value") else product.status,
        "region": product.region,
        "pollen_type": product.pollen_type,
        "resolution": product.resolution,
        "workflow_node": product.workflow_node,
        "workflow_version": product.workflow_version,
        "file_path": product.file_path,
        "subtype": product.subtype,
        "variable": product.variable,
        "unit": product.unit,
        "bounds_json": product.bounds_json,
        "lead_time": product.lead_time,
        "source_run_id": product.source_run_id,
        "capability_status": product.capability_status,
        "is_published": product.is_published,
        "release_time": release_time,
        "created_at": product.created_at.isoformat() if product.created_at else release_time,
        "download_url": f"{settings.API_V1_STR}/products/{product.id}/download",
    }
    if product.file_path.startswith(SERVER_PATH_PREFIX):
        resolved = resolve_server_file_path(product.file_path)
        if resolved:
            data["download_url"] = build_server_download_url(resolved[1])
            data["server_path"] = resolved[1]
    elif not Path(product.file_path).is_file():
        server_path = infer_server_path_from_product_name(product.product_name)
        if server_path:
            data["server_path"] = server_path
            data["download_url"] = build_server_download_url(server_path)
    return data


def infer_server_path_from_product_name(product_name: str) -> str | None:
    separator = product_name.find(":")
    if separator <= 0:
        return None
    ref = product_name[:separator]
    filename = product_name[separator + 1 :]
    try:
        parsed = parse_product_ref(ref)
    except ValueError:
        return None
    subpath = parsed.subpath or resolve_products_subpath("", parsed.season, parsed.region, parsed.run_id)
    if not subpath:
        return None
    if filename.lower().endswith(".png"):
        return f"{subpath}/plots/{filename}"
    return f"{subpath}/products/{filename}"
