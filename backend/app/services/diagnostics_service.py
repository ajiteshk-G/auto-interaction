import time
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.claim import InsuranceClaim
from app.schemas.diagnostics import (
    DamageAssessmentRequest,
    DamageAssessmentResponse,
    WarningLightScanRequest,
    WarningLightScanResponse,
    ClaimSubmissionRequest,
    ClaimSubmissionResponse
)

class DiagnosticsService:
    @staticmethod
    def assess_damage(req: DamageAssessmentRequest) -> DamageAssessmentResponse:
        """Processes multimodal vision input to classify exterior damage and map OEM replacement parts."""
        # Simulated Gemini Multimodal Vision Damage Inspection Engine
        mock_type = req.mock_damage_type or "bumper_foglamp"
        
        if mock_type == "bumper_foglamp":
            parts = [
                "Scratches and paint abrasion on front lower bumper valence",
                "Cracked lens and fractured housing on Right Fog Lamp Assembly"
            ]
            part_no = "#TH-88301"
            part_desc = "OEM Thar ROXX Fog Lamp Assembly (RH)"
            part_cost = 3200.0
            labor_cost = 850.0
            summary = "Gemini Vision detected minor surface scrapes on front bumper and impact crack on RH fog lamp. Structural sensors verify zero radiator or chassis misalignment. Safe to drive to workshop."
        elif mock_type == "windshield_chip":
            parts = ["Acoustic front windshield stone chip (12mm diameter)"]
            part_no = "#TH-44102"
            part_desc = "OEM Acoustic Laminated Windshield Glass"
            part_cost = 7400.0
            labor_cost = 1200.0
            summary = "Gemini Vision detected isolated circular rock chip on outer laminate. Resin bonding repair possible or full zero-dep replacement recommended."
        else:
            parts = ["Rear quarter panel scratch and wheel arch cladding scuff"]
            part_no = "#TH-22904"
            part_desc = "OEM Rear Wheel Arch Cladding Black Textured"
            part_cost = 1800.0
            labor_cost = 500.0
            summary = "Gemini Vision identified cosmetic scuffing on composite cladding. No metal denting detected."

        return DamageAssessmentResponse(
            damage_detected=True,
            severity="MINOR",
            detected_parts=parts,
            structural_damage=False,
            recommended_oem_part=part_desc,
            oem_part_number=part_no,
            estimated_part_cost=part_cost,
            estimated_labor_cost=labor_cost,
            estimated_out_of_pocket=0.0, # Zero depreciation
            recommended_workshop="Bayview Mahindra Workshop, Bandra West",
            parts_dispatch_eta="Tomorrow Morning ahead of Saturday Service",
            gemini_vision_summary=summary
        )

    @staticmethod
    def scan_warning_light(req: WarningLightScanRequest) -> WarningLightScanResponse:
        symbol = (req.light_symbol or "engine_oil_pressure").lower()
        if "oil" in symbol:
            return WarningLightScanResponse(
                symbol_name="Engine Oil Viscosity / Service Required (Amber)",
                severity="WARNING",
                explanation="Engine oil sensor detected degraded viscosity after 9,820 km of highway and city driving.",
                recommended_action="Schedule routine 10,000 km oil and filter change within next 200 km.",
                safe_to_drive=True
            )
        elif "tpms" in symbol or "tyre" in symbol or "tire" in symbol:
            return WarningLightScanResponse(
                symbol_name="Tyre Pressure Monitoring System (TPMS Low - Amber)",
                severity="WARNING",
                explanation="Front Right tyre pressure is 28 PSI (recommended: 32 PSI).",
                recommended_action="Inflate front right tyre to 32 PSI at nearest fueling station.",
                safe_to_drive=True
            )
        else:
            return WarningLightScanResponse(
                symbol_name="Intelligent 4XPLOR 4WD Lock Indicator (Green)",
                severity="INFO",
                explanation="4WD Electronic Rear Differential Lock engaged for low-traction surface.",
                recommended_action="Normal off-road operation. Disengage when returning to dry tarmac.",
                safe_to_drive=True
            )

    @staticmethod
    async def file_insurance_claim(db: AsyncSession, customer_db_id: int, req: ClaimSubmissionRequest) -> InsuranceClaim:
        claim_id = f"MH-INS-{int(time.time()) % 100000}"
        claim = InsuranceClaim(
            claim_id=claim_id,
            customer_id=customer_db_id,
            vin=req.vin,
            vehicle_model=req.vehicle_model,
            incident_description=req.incident_description,
            damage_severity="MINOR",
            detected_damages=req.detected_damages,
            oem_part_number=req.oem_part_number,
            oem_part_description="OEM Replacement Assembly",
            estimated_part_cost=3200.0,
            estimated_labor_cost=800.0,
            customer_out_of_pocket=0.0,
            insurer_name="ICICI Lombard General Insurance",
            policy_number="POL-ICICI-MH-2026-99201",
            claim_status="DIGITALLY_APPROVED",
            workshop_name=req.workshop_name,
            parts_delivery_estimate="Tomorrow Morning 9:00 AM"
        )
        db.add(claim)
        await db.commit()
        await db.refresh(claim)
        return claim
