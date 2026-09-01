from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.customer import (
    CustomerProfileResponse,
    CustomerProfileUpdate,
    CustomerIdentifyRequest,
    CustomerIdentifyResponse,
    SaveTranscriptTurnRequest,
    SaveFullSessionTranscriptRequest,
    InteractionLogSchema,
    ConversationSessionSchema
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customer", tags=["Customer Profile & PreSales Sessions"])

@router.post("/identify", response_model=CustomerIdentifyResponse)
async def identify_or_register_customer(req: CustomerIdentifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Called before starting a PreSales Live Call or Chat.
    Enforces regex validation for Name and Phone.
    Maintains a 1:Many relationship where returning users share a single Customer entry
    with distinct ConversationSession and InteractionLog rows.
    """
    customer, session, is_returning, total_sessions = await CustomerService.identify_or_register_customer(
        db,
        name=req.name,
        phone=req.phone,
        session_type=req.session_type,
        vehicle_id=req.vehicle_id or "thar_roxx"
    )
    
    greeting = (
        f"Namaste {customer.name}! Welcome back to Mahindra. Continuing your exploration of {session.vehicle_id.replace('_', ' ').title()}?"
        if is_returning
        else f"Namaste {customer.name}! Welcome to Mahindra. Which SUV can I help you explore today?"
    )

    return CustomerIdentifyResponse(
        customer_id=customer.customer_id,
        name=customer.name,
        phone=customer.phone,
        is_returning=is_returning,
        session_id=session.session_id,
        greeting=greeting,
        past_session_count=total_sessions,
        interested_vehicle=customer.interested_vehicle_id,
        customer_profile=customer
    )

@router.post("/transcript-turn", response_model=InteractionLogSchema)
async def record_transcript_turn(req: SaveTranscriptTurnRequest, db: AsyncSession = Depends(get_db)):
    """Saves an individual turn of customer or MIA conversation to the session transcript."""
    log = await CustomerService.log_interaction(
        db=db,
        customer_id_str=req.customer_id,
        speaker=req.speaker,
        message=req.message,
        channel=req.channel,
        session_id_str=req.session_id,
        intent=req.extracted_intent,
        tool=req.tool_triggered
    )
    return log

@router.get("/sessions", response_model=List[ConversationSessionSchema])
async def list_customer_sessions(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches all past conversation sessions and their full transcripts (1:Many relationship)."""
    sessions = await CustomerService.get_customer_sessions(db, customer_id)
    return sessions

@router.get("/profile", response_model=CustomerProfileResponse)
async def get_customer_profile(
    customer_id: Optional[str] = None,
    phone: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    if phone:
        customer = await CustomerService.get_customer_by_phone(db, phone)
    elif customer_id:
        customer = await CustomerService.get_customer_by_id(db, customer_id)
    else:
        customer = await CustomerService.get_or_create_default_customer(db)
        
    if not customer:
        customer = await CustomerService.get_or_create_default_customer(db)
    return customer

@router.patch("/profile", response_model=CustomerProfileResponse)
async def update_customer(req: CustomerProfileUpdate, customer_id: str = "CUST-9820155432", db: AsyncSession = Depends(get_db)):
    customer = await CustomerService.get_customer_by_id(db, customer_id)
    if not customer:
        customer = await CustomerService.get_or_create_default_customer(db)
    
    update_data = req.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(customer, k, v)
        
    await db.commit()
    await db.refresh(customer)
    return customer

@router.post("/save-full-transcript")
async def save_full_session_transcript(req: SaveFullSessionTranscriptRequest, db: AsyncSession = Depends(get_db)):
    """Flushes and saves full session messages to the database upon End Call."""
    msg_dicts = [m.model_dump() for m in req.messages]
    sess = await CustomerService.save_full_session_transcript(
        db,
        session_id_str=req.session_id,
        customer_id_str=req.customer_id,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        vehicle_id=req.vehicle_id,
        channel=req.channel or "VOICE_LIVE",
        messages=msg_dicts
    )
    return {"status": "success", "session_id": sess.session_id, "customer_id": sess.customer_id}
