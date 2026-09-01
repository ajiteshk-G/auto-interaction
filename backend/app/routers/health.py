from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "service": "Mahindra Intelligent Assistant (MIA) Omnichannel Backend",
        "version": "2.0.0",
        "gemini_multimodal_live_ready": True
    }
