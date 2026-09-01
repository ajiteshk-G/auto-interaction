from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.sales_recording import (
    TestRideRecordingUploadRequest,
    TestRideInsightResponse,
    TestRideLeadItem
)
from app.services.sales_recording_service import SalesRecordingService

router = APIRouter(prefix="/sales", tags=["Sales Advisor Mobile App & Test Ride"])

@router.get("/leads", response_model=List[TestRideLeadItem])
async def get_sales_leads(
    dealership_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Fetch qualified leads from Pre-sales virtual showroom for the Sales Mobile App, optionally filtered by showroom and brand."""
    return await SalesRecordingService.get_sales_leads(db, dealership_id=dealership_id, brand_id=brand_id)

@router.post("/test-ride/upload-recording", response_model=TestRideInsightResponse)
async def upload_test_ride_recording(
    req: TestRideRecordingUploadRequest,
    db: AsyncSession = Depends(get_db)
):
    """Uploads/dumps mobile test ride audio recording to GCS and executes multi-dimensional AI insights."""
    recording = await SalesRecordingService.process_and_store_recording(db, req)
    return recording

@router.get("/test-ride/latest", response_model=Optional[TestRideInsightResponse])
async def get_latest_test_ride(
    customer_id: Optional[str] = None,
    booking_reference: Optional[str] = None,
    phone: Optional[str] = None,
    brand_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve the latest persisted AI insights for a customer or booking reference."""
    insights = await SalesRecordingService.get_latest_test_ride(
        db,
        customer_id=customer_id,
        booking_reference=booking_reference,
        phone=phone,
        brand_id=brand_id
    )
    return insights

@router.get("/test-ride/insights/{session_id}", response_model=TestRideInsightResponse)
async def get_test_ride_insights(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve AI-analyzed insights, STT transcript, and objection analysis for a test ride session."""
    insights = await SalesRecordingService.get_test_ride_insights(db, session_id)
    if not insights:
        raise HTTPException(status_code=404, detail="Test ride session not found")
    return insights

@router.get("/test-ride/all", response_model=List[TestRideInsightResponse])
async def get_all_test_rides(
    brand_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await SalesRecordingService.get_all_test_rides(db, brand_id=brand_id)
