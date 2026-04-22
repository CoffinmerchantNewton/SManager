from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..core.database import get_db
from ..models.models import ForecastProduct
from ..schemas.schemas import ForecastProductCreate, ForecastProductResponse

router = APIRouter()

@router.get("/", response_model=List[ForecastProductResponse])
def get_products(
    skip: int = 0,
    limit: int = 20,
    region: Optional[str] = None,
    pollen_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ForecastProduct)

    if region:
        query = query.filter(ForecastProduct.region == region)
    if pollen_type:
        query = query.filter(ForecastProduct.pollen_type == pollen_type)
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

@router.post("/", response_model=ForecastProductResponse)
def create_product(product: ForecastProductCreate, db: Session = Depends(get_db)):
    db_product = ForecastProduct(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.patch("/{product_id}/publish")
def toggle_publish(product_id: int, is_published: bool, db: Session = Depends(get_db)):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_published = is_published
    db.commit()
    return {"message": "Product publish status updated"}

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ForecastProduct).filter(ForecastProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}
