from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.claim import InsuranceClaim
from app.schemas.diagnostics import (
    DamageAssessmentRequest,
    DamageAssessmentResponse,
    WarningLightScanRequest,
    WarningLightScanResponse,
    ClaimSubmissionRequest,
    ClaimSubmissionResponse
)
from app.services.diagnostics_service import DiagnosticsService
from app.services.customer_service import CustomerService
from app.services.brand_service import BrandService

router = APIRouter(prefix="/diagnostics", tags=["Multimodal Vision Diagnostics & Claims"])

@router.post("/assess-damage", response_model=DamageAssessmentResponse)
async def assess_vehicle_damage(req: DamageAssessmentRequest):
    return DiagnosticsService.assess_damage(req)

@router.post("/warning-lights", response_model=WarningLightScanResponse)
async def scan_warning_light(req: WarningLightScanRequest):
    return DiagnosticsService.scan_warning_light(req)

@router.post("/claims", response_model=ClaimSubmissionResponse)
async def submit_insurance_claim(
    req: ClaimSubmissionRequest,
    brand_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    b_id = (brand_id or (BrandService.get_active_brand().id if BrandService.get_active_brand() else "mahindra")).lower()
    customer = await CustomerService.get_customer_by_id(db, req.customer_id, brand_id=b_id)
    if not customer:
        customer = await CustomerService.get_or_create_default_customer(db, brand_id=b_id)
        
    claim = await DiagnosticsService.file_insurance_claim(db, customer.id, req, brand_id=b_id)
    customer.current_phase = "POST_SALES"
    await db.commit()
    return claim

@router.get("/claims/my-claims", response_model=List[ClaimSubmissionResponse])
async def list_customer_claims(
    customer_id: Optional[str] = None,
    brand_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    b_id = (brand_id or (BrandService.get_active_brand().id if BrandService.get_active_brand() else "mahindra")).lower()
    customer = None
    if customer_id:
        customer = await CustomerService.get_customer_by_id(db, customer_id, brand_id=b_id)
    if not customer:
        customer = await CustomerService.get_or_create_default_customer(db, brand_id=b_id)
        
    stmt = (
        select(InsuranceClaim)
        .where(InsuranceClaim.customer_id == customer.id, InsuranceClaim.brand_id == b_id)
        .order_by(InsuranceClaim.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
