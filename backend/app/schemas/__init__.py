from app.schemas.customer import (
    CustomerProfileBase,
    CustomerProfileCreate,
    CustomerProfileUpdate,
    CustomerProfileResponse,
    InteractionLogSchema
)
from app.schemas.catalog import (
    VehicleItem,
    VehicleVariant,
    VehicleComparisonRequest,
    DealershipItem
)
from app.schemas.booking import (
    TestDriveBookingCreate,
    TestDriveBookingResponse
)
from app.schemas.diagnostics import (
    DamageAssessmentRequest,
    DamageAssessmentResponse,
    WarningLightScanRequest,
    WarningLightScanResponse,
    ClaimSubmissionRequest,
    ClaimSubmissionResponse
)
from app.schemas.outbound_call import (
    OutboundCallTriggerRequest,
    OutboundDialogueTurnRequest,
    OutboundDialogueTurnResponse,
    OutboundCallInsightsResponse
)
