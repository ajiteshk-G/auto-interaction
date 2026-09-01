from app.models.customer import Customer, InteractionLog
from app.models.booking import TestDriveBooking, TestDriveSlot, PublicHoliday, SlotConfig
from app.models.dealership import Dealership
from app.models.claim import InsuranceClaim
from app.models.sales_ride import TestRideRecording, OutboundCallLog

__all__ = [
    "Customer",
    "InteractionLog",
    "TestDriveBooking",
    "TestDriveSlot",
    "PublicHoliday",
    "SlotConfig",
    "Dealership",
    "InsuranceClaim",
    "TestRideRecording",
    "OutboundCallLog"
]
