import re
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.booking import TestDriveBooking
from app.services.catalog_service import CatalogService

logger = logging.getLogger("checklist_service")

STATIC_VEHICLE_CHECKLISTS: Dict[str, List[str]] = {
    "thar_roxx": [
        "Demonstrate Frequency Selective Damping (FSD) / Ride Pliability on rough patches",
        "Showcase 2.2L mHawk Diesel Throttle Acceleration & 6-Speed AT Smooth Shift Response",
        "Highlight Panoramic Skyroof, Dual 10.25-inch Cockpit Displays & Rear 60:40 Reclining Seats"
    ],
    "scorpio_n": [
        "Demonstrate 4XPLOR Intelligent Terrain Management (Mud, Sand, Snow, Normal Modes)",
        "Showcase Sony 12-Speaker 3D Immersive Sound System with Subwoofer",
        "Highlight Watt's Linkage High-Speed Stability & Commanding Road Presence"
    ],
    "be_6e": [
        "Demonstrate Instant 335 HP EV Acceleration (0-100 in 6.7s) & Multi-level Regenerative Braking",
        "Showcase Triple Panoramic Cockpit Screens, HUD & Panoramic Glass Canopy",
        "Highlight 682 km ARAI Certified Range & 175kW Ultra-Fast DC Charging Capability"
    ],
    "xev_9e": [
        "Demonstrate Triple Integrated 12.3-inch Cockpit Cinema Screens (Driver, Center, Passenger)",
        "Showcase Harman Kardon 16-Speaker Audio with Dolby Atmos & Headrest Audio",
        "Highlight Semi-Active Damping Suspension & Ultra-Luxury Lounge Reclining Seating"
    ],
    "xuv700": [
        "Demonstrate Level 2 ADAS Suite (Adaptive Cruise Control, Lane Keep Assist & Auto Emergency Braking)",
        "Showcase Auto Booster Headlamps (activates >80 km/h) & Dual 10.25-inch Superscreen",
        "Highlight Sony 3D Sound with Sky-Roof & Driver Memory Seat Welcome Function"
    ],
    "xuv_3xo": [
        "Demonstrate Segment-First Level 2 ADAS Radar & Camera Safety Features",
        "Showcase Panoramic Skyroof & Dual 10.25-inch Digital Screen Setup",
        "Highlight 1.2L mStallion TGDi Turbo Petrol Fast Throttle Response"
    ],
    "thar_3door": [
        "Demonstrate Shift-on-the-fly 4x4 Transfer Case with Mechanical Locking Rear Differential (MLD)",
        "Showcase 650mm Water Wading Capability & Washable Interior Floor with Drain Plugs",
        "Highlight Iconic Rugged Go-Anywhere Stance & Roll Cage Safety"
    ],
    "scorpio_classic": [
        "Demonstrate Gen-2 mHawk Diesel Low-End Pull & Instant Torque Response",
        "Showcase Classic Muscular Bonnet Stance & Commanding High Seating Posture",
        "Highlight 7/9-Seater Practical Cabin Space & Low Ownership Maintenance"
    ],
    "bolero_neo": [
        "Demonstrate Multi-Terrain Technology (MTT) Differential Lock on Tough Terrains",
        "Showcase Heavy-Duty Ladder Frame Chassis on Broken Road Conditions",
        "Highlight 7-Seater Space & Rugged Practical Durability"
    ],
    "xuv400_ev": [
        "Demonstrate Instant EV Torque Acceleration & Single-Pedal Driving",
        "Showcase 456 km Driving Range & 10.25-inch Infotainment Display",
        "Highlight All-4 Disc Brakes & 60+ Connected Car Features"
    ]
}

DEFAULT_CHECKLIST = [
    "Demonstrate Vehicle Dynamics, Throttle Acceleration & Brake Feel",
    "Showcase Cockpit Infotainment Display, Audio & Connected Tech",
    "Highlight Cabin Ergonomics, Seating Space & Key Safety Features"
]

FEATURE_KEYWORDS: List[Dict[str, Any]] = [
    {
        "keywords": ["fsd", "suspension", "pothole", "bump", "ride", "comfort", "bounce", "stability", "pliant"],
        "item": {
            "thar_roxx": "Demonstrate Frequency Selective Damping (FSD) Suspension & Penta-Link Rear on rough patches",
            "scorpio_n": "Demonstrate Watt's Linkage Rear Suspension & High-Speed Highway Stability",
            "xev_9e": "Demonstrate Semi-Active Smart Suspension with Continuous Damping Control",
            "default": "Demonstrate Vehicle Suspension Compliance & Cabin Stability over rough surfaces"
        }
    },
    {
        "keywords": ["sunroof", "skyroof", "moonroof", "glass roof", "panoramic"],
        "item": {
            "thar_roxx": "Showcase Panoramic Skyroof with One-Touch Operation & UV Tint Glass",
            "be_6e": "Showcase Panoramic Glass Canopy with Ambient Mood Lighting",
            "xuv700": "Showcase Panoramic Skyroof (Largest in Segment) with Anti-Pinch",
            "xuv_3xo": "Showcase Segment-First Panoramic Skyroof & Ambient Lighting",
            "default": "Showcase Electric Sunroof & Cabin Airiness"
        }
    },
    {
        "keywords": ["adas", "safety", "cruise", "autonomous", "lane", "collision", "braking", "brake assist", "emergency brake"],
        "item": {
            "thar_roxx": "Demonstrate Level 2 ADAS (Adaptive Cruise Control, Lane Keep Assist & Auto Emergency Braking)",
            "xuv700": "Demonstrate Level 2 ADAS (Adaptive Cruise, Lane Keep & Smart Pilot Assist)",
            "be_6e": "Demonstrate Level 2+ Autonomous Driving & 360 Automated Parking Assist",
            "xuv_3xo": "Demonstrate Segment-First Level 2 ADAS Suite with Radar & Camera Fusion",
            "default": "Demonstrate Advanced Driver Assistance & Active Safety Features"
        }
    },
    {
        "keywords": ["sound", "audio", "speaker", "speakers", "music", "sony", "harman", "dolby", "kardon", "bass", "subwoofer", "sound system", "audio system", "tweeter"],
        "item": {
            "thar_roxx": "Showcase Harman Kardon 9-Speaker Audio System with QuantumLogic Surround Sound",
            "scorpio_n": "Showcase Sony 12-Speaker 3D Immersive Audio with Subwoofer",
            "xev_9e": "Showcase Harman Kardon 16-Speaker Audio with Dolby Atmos & Headrest Speakers",
            "xuv700": "Showcase Sony 12-Speaker 3D Surround Sound with Ceiling Mounted Speakers",
            "default": "Showcase Premium Immersive Sound System & Acoustic Cabin Tuning"
        }
    },
    {
        "keywords": ["4x4", "4wd", "offroad", "off-road", "terrain", "mud", "sand", "snow", "diff", "differential", "water wading", "crawl"],
        "item": {
            "thar_roxx": "Demonstrate 4XPLOR All-Terrain Modes, CrawlSmart Assist & Electronic Locking Differential",
            "scorpio_n": "Demonstrate 4XPLOR Intelligent Terrain Management (Mud, Sand, Snow, Normal)",
            "thar_3door": "Demonstrate Shift-on-the-fly 4x4 Low Range & Mechanical Locking Differential (MLD)",
            "bolero_neo": "Demonstrate Multi-Terrain Technology (MTT) Mechanical Locking Differential",
            "default": "Demonstrate All-Terrain Capability, Ground Clearance & Traction Modes"
        }
    },
    {
        "keywords": ["charging", "charge", "battery", "range", "kwh", "fast charger", "ev", "electric", "regen"],
        "item": {
            "be_6e": "Demonstrate 682 km Long-Range Efficiency, 20-min 175kW DC Fast Charging & Paddle Regen",
            "xev_9e": "Demonstrate 656 km Driving Range, 175kW Ultra-Fast DC Charging & Bi-Directional V2L Power",
            "xuv400_ev": "Demonstrate 456 km Range, Fast DC Charging & Multi-level Regenerative Braking",
            "default": "Demonstrate Electric Range, Charging Convenience & Regenerative Braking"
        }
    },
    {
        "keywords": ["screen", "display", "digital display", "twin screen", "dual screen", "cockpit", "touchscreen", "apple", "carplay", "android", "infotainment", "navigation", "instrument cluster", "superscreen", "cluster", "dashboard screen"],
        "item": {
            "thar_roxx": "Demonstrate Dual 10.25-inch HD Cockpit Displays with Wireless Apple CarPlay & Android Auto",
            "be_6e": "Demonstrate Triple Horizon Cockpit Displays, AR Head-Up Display & AdrenoX OS",
            "xev_9e": "Demonstrate Triple Integrated 12.3-inch Cockpit Cinema Screens (Driver, Center, Passenger)",
            "xuv700": "Demonstrate Dual 10.25-inch Supercreen HD Digital Cluster & Infotainment",
            "default": "Demonstrate High-Definition Touchscreen, Navigation & Smartphone Connectivity"
        }
    },
    {
        "keywords": ["seat", "ventilated", "cooling", "recline", "legroom", "comfort", "space", "under-thigh", "row", "boot", "luggage"],
        "item": {
            "thar_roxx": "Highlight Ventilated Front Seats, 60:40 Rear Seat Recline & 644L Deep Boot Space",
            "scorpio_n": "Highlight Captain Seats / 7-Seater Space, Second-Row Recline & High Seating Posture",
            "xev_9e": "Highlight Ultra-Luxury Lounge Seating with Powered Ottoman & Ventilated Cushions",
            "xuv700": "Highlight Driver Memory Seat with Welcome Retract & 7-Seater Ergonomic Seating",
            "default": "Highlight Seating Comfort, Cabin Space, Legroom & Luggage Capacity"
        }
    },
    {
        "keywords": ["camera", "parking", "360", "blind spot", "sensor", "park assist"],
        "item": {
            "thar_roxx": "Demonstrate 360-Degree Surround View Camera & Blind View Monitor on Turn Indicators",
            "xuv700": "Demonstrate 360-Degree Camera with 3D View & Blind View Monitor in Cluster",
            "be_6e": "Demonstrate 360 Surround View with Automated Intelligent Parking Assist",
            "default": "Demonstrate 360-Degree Camera View & Dynamic Parking Guidelines"
        }
    },
    {
        "keywords": ["engine", "power", "torque", "mhawk", "mstallion", "diesel", "petrol", "acceleration", "pickup", "speed", "transmission", "automatic", "gearbox"],
        "item": {
            "thar_roxx": "Showcase 2.2L mHawk Diesel (175 PS / 370 Nm) Power Delivery & Smooth 6-Speed Automatic",
            "scorpio_n": "Showcase 203 PS mStallion Petrol / 175 PS mHawk Diesel 400Nm Punchy Acceleration",
            "be_6e": "Showcase Instant 335 HP EV Torque (0-100 km/h in 6.7 seconds) & Boost Mode",
            "xuv700": "Showcase 200 PS mStallion Turbo Petrol / 185 PS mHawk Diesel High-Speed Refinement",
            "default": "Showcase Engine Power Response, Throttle Pickup & Smooth Gear Shifts"
        }
    },
    {
        "keywords": ["price", "cost", "emi", "loan", "finance", "offer", "discount", "booking", "delivery", "waiting"],
        "item": {
            "default": "Walk through Official Ex-Showroom Pricing, Instant 8.15% Pre-Approved Loan & Fast 12-Day Allocation"
        }
    }
]

class ChecklistService:
    @staticmethod
    def get_static_checklist(vehicle_id: Optional[str] = None) -> List[str]:
        """Returns default static demo checklist tailored for the vehicle model."""
        if not vehicle_id:
            return DEFAULT_CHECKLIST
        normalized = vehicle_id.strip().lower()
        return STATIC_VEHICLE_CHECKLISTS.get(normalized, DEFAULT_CHECKLIST)

    @staticmethod
    def extract_checklist_items(
        customer_text: str,
        vehicle_id: str = "thar_roxx",
        existing_items: Optional[List[str]] = None
    ) -> List[str]:
        """
        Intelligently identifies customer asks/inquiries from conversation
        and generates corresponding actionable demonstration items tailored for the vehicle.
        """
        lower_text = customer_text.lower()
        items = list(existing_items or [])
        veh_key = vehicle_id.lower() if vehicle_id else "thar_roxx"

        for entry in FEATURE_KEYWORDS:
            if any(kw in lower_text for kw in entry["keywords"]):
                item_map = entry["item"]
                matched_item = item_map.get(veh_key) or item_map.get("default")
                if matched_item and matched_item not in items:
                    items.append(matched_item)

        # Cap at 5 key checklist items
        if len(items) > 5:
            items = items[:5]

        return items

    @staticmethod
    async def update_customer_and_booking_checklist(
        db: AsyncSession,
        customer_id_str: str,
        vehicle_id: str,
        new_items: List[str]
    ) -> List[str]:
        """Persists updated checklist items to the Customer and active TestDriveBooking records in DB."""
        if not new_items:
            return []

        stmt = select(Customer).where(
            (Customer.customer_id == customer_id_str) | (Customer.phone == customer_id_str)
        ).options(selectinload(Customer.bookings))
        res = await db.execute(stmt)
        customer = res.scalars().first()

        if not customer:
            return new_items

        # Merge existing checklist
        current_list = list(customer.advisor_checklist or [])
        for item in new_items:
            if item not in current_list:
                current_list.append(item)
        current_list = current_list[:5]

        from sqlalchemy.orm.attributes import flag_modified
        customer.advisor_checklist = list(current_list)
        flag_modified(customer, "advisor_checklist")

        # Also update any active bookings for this customer
        for b in customer.bookings:
            if b.status in ["CONFIRMED", "PENDING", "RESERVED"]:
                b.advisor_checklist = list(current_list)
                flag_modified(b, "advisor_checklist")

        db.add(customer)
        await db.commit()
        return current_list
