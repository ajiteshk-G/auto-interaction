from typing import List
from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/diagnostics", tags=["Multimodal Vision Diagnostics & Claims"])

@router.post("/assess-damage", response_model=DamageAssessmentResponse)
async def assess_vehicle_damage(req: DamageAssessmentRequest):
    return DiagnosticsService.assess_damage(req)

@router.post("/warning-lights", response_model=WarningLightScanResponse)
async def scan_warning_light(req: WarningLightScanRequest):
    return DiagnosticsService.scan_warning_light(req)

@router.post("/claims", response_model=ClaimSubmissionResponse)
async def submit_insurance_claim(req: ClaimSubmissionRequest, db: AsyncSession = Depends(get_db)):
    customer = await CustomerService.get_customer_by_id(db, req.customer_id)
    if not customer:
        customer = await CustomerService.get_or_create_default_customer(db)
        
    claim = await DiagnosticsService.file_insurance_claim(db, customer.id, req)
    customer.current_phase = "POST_SALES"
    await db.commit()
    return claim

@router.get("/claims/my-claims", response_model=List[ClaimSubmissionResponse])
async def list_customer_claims(customer_id: str = "CUST-AARAV-001", db: AsyncSession = Depends(get_db)):
    customer = await CustomerService.get_customer_by_id(db, customer_id)
    if not customer:
        customer = await CustomerService.get_or_create_default_customer(db)
        
    stmt = select(InsuranceClaim).where(InsuranceClaim.customer_id == customer.id).order_by(InsuranceClaim.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()
