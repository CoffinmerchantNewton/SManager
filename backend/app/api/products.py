import json
from pathlib import Path
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from ..core.database import get_db
from ..core.config import settings
from ..core.security import require_admin
from ..models.models import ForecastProduct
from ..schemas.schemas import ForecastProductCreate, ForecastProductPublishRequest, ForecastProductResponse
from ..services.server_client import server_client

router = APIRouter()

@router.get("/")
def get_products(
    skip: int = 0,
    limit: int = 20,
    region: Optional[str] = None,
    pollen_type: Optional[str] = None,
    run_id: Optional[str] = None,
    subpath: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    ref = (subpath or run_id or "").strip()
    if ref and server_client.configured and "/" in ref:
        from ..services.server_products import list_products, merge_db_and_server_products, serialize_db_product

        db_products = (
            db.query(ForecastProduct)
            .filter(ForecastProduct.product_name.like(f"{ref}:%"))
            .order_by(ForecastProduct.release_time.desc())
            .all()
        )
        try:
            server_products = list_products(ref)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        merged = merge_db_and_server_products(db_products, server_products)
        if status:
            merged = [item for item in merged if item.get("status") == status]
        return merged[skip : skip + limit]

    query = db.query(ForecastProduct)

    if region:
        query = query.filter(ForecastProduct.region == region)
    if pollen_type:
        query = query.filter(ForecastProduct.pollen_type == pollen_type)
    if run_id:
        query = query.filter(ForecastProduct.product_name.like(f"{run_id}:%"))
    if status:
        query = query.filter(ForecastProduct.status == status)

    products = query.order_by(ForecastProduct.release_time.desc()).offset(skip).limit(limit).all()
    return products

@router.get("/server/download")
def download_server_product(path: str = Query(..., min_length=1)):
    from ..services.server_products import PRODUCT_ROOT_KEY

    if ".." in path.replace("\\", "/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    content = server_client.download_file(
        PRODUCT_ROOT_KEY,
        path,
        timeout=float(settings.SERVER_PRODUCT_DOWNLOAD_TIMEOUT),
    )
    filename = path.replace("\\", "/").split("/")[-1]
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/server/content")
def get_server_product_content(path: str = Query(..., min_length=1)):
    from ..services.server_products import fetch_server_json

    payload = fetch_server_json(path)
    suffix = Path(path).suffix.lower()
    media_type = "application/geo+json" if suffix == ".geojson" else "application/json"
    return JSONResponse(content=payload, media_type=media_type)


@router.get("/server/latest")
def get_latest_server_product_bundles(
    season: str | None = Query(default=None),
    regions: list[str] | None = Query(default=None),
):
    from ..services.server_products import list_latest_portal_bundles

    return {
        "bundles": list_latest_portal_bundles(regions=regions, season=season),
        "source": "server",
    }


@router.post("/sync")
def sync_products_by_ref(
    subpath: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    from ..services.server_products import sync_products

    ref = (subpath or run_id or "").strip()
    if not ref:
        raise HTTPException(status_code=400, detail="subpath or run_id is required")
    try:
        return sync_products(db, ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/{product_id}", response_model=ForecastProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{product_id}/download")
def download_product(product_id: int, db: Session = Depends(get_db)):
    from ..services.server_products import resolve_server_file_path

    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    server_ref = resolve_server_file_path(product.file_path)
    if server_ref:
        root_key, rel_path = server_ref
        content = server_client.download_file(root_key, rel_path)
        filename = rel_path.replace("\\", "/").split("/")[-1]
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    path = Path(product.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Product file not found")
    return FileResponse(path, filename=path.name)

@router.get("/{product_id}/content")
def get_product_content(product_id: int, db: Session = Depends(get_db)):
    from ..services.server_products import resolve_server_file_path

    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    server_ref = resolve_server_file_path(product.file_path)
    if server_ref:
        root_key, rel_path = server_ref
        raw = server_client.download_file(root_key, rel_path)
        path = Path(rel_path)
    else:
        path = Path(product.file_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Product file not found")
        raw = path.read_bytes()

    if path.suffix.lower() not in {".json", ".geojson"}:
        raise HTTPException(status_code=415, detail="Only JSON/GeoJSON products can be read inline")
    if len(raw) > int(settings.PRODUCT_INLINE_MAX_MB * 1024 * 1024):
        raise HTTPException(status_code=413, detail="Product file is too large for inline content")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON product: {exc}") from exc
    media_type = "application/geo+json" if path.suffix.lower() == ".geojson" else "application/json"
    return JSONResponse(content=payload, media_type=media_type)

@router.post("/", response_model=ForecastProductResponse)
def create_product(product: ForecastProductCreate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    db_product = ForecastProduct(**product.model_dump(exclude={"bounds"}))
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.patch("/{product_id}/publish")
def toggle_publish(
    product_id: int,
    payload: ForecastProductPublishRequest | None = Body(default=None),
    is_published: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    next_status = payload.is_published if payload else is_published
    if next_status is None:
        raise HTTPException(status_code=400, detail="is_published is required")
    product.is_published = next_status
    db.commit()
    return {"message": "Product publish status updated"}

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}
