import json
from pathlib import Path
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from ..core.database import get_db
from ..core.config import settings
from ..core.security import require_admin
from ..models.models import ForecastProduct
from ..schemas.schemas import ForecastProductCreate, ForecastProductPublishRequest, ForecastProductResponse

router = APIRouter()

@router.get("/", response_model=List[ForecastProductResponse])
def get_products(
    skip: int = 0,
    limit: int = 20,
    region: Optional[str] = None,
    pollen_type: Optional[str] = None,
    run_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
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

@router.get("/{product_id}", response_model=ForecastProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{product_id}/download")
def download_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    path = Path(product.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Product file not found")
    return FileResponse(path, filename=path.name)

@router.get("/{product_id}/content")
def get_product_content(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    path = Path(product.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Product file not found")
    if path.suffix.lower() not in {".json", ".geojson"}:
        raise HTTPException(status_code=415, detail="Only JSON/GeoJSON products can be read inline")
    if path.stat().st_size > int(settings.PRODUCT_INLINE_MAX_MB * 1024 * 1024):
        raise HTTPException(status_code=413, detail="Product file is too large for inline content")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON product: {exc}") from exc
    media_type = "application/geo+json" if path.suffix.lower() == ".geojson" else "application/json"
    return JSONResponse(content=payload, media_type=media_type)

@router.post("/", response_model=ForecastProductResponse)
def create_product(product: ForecastProductCreate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    db_product = ForecastProduct(**product.model_dump())
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
