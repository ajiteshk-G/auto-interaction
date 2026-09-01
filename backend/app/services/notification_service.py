"""
Omnichannel Notification Service for Mahindra Virtual Showroom & Test Drive Bookings.
Sends live SMS via Twilio API immediately upon test ride confirmation.
"""

import os
import logging
import subprocess
from typing import Optional, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# Cached secrets
_TWILIO_CACHE: Dict[str, Optional[str]] = {
    "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
    "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
    "phone_number": os.getenv("TWILIO_PHONE_NUMBER", "+13369154920"),
    "whatsapp_number": os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
}
_SECRETS_CHECKED = False

def _get_gcp_secret(secret_name: str) -> Optional[str]:
    """Retrieves secret from GCP Secret Manager via gcloud CLI fallback."""
    for project in ["1047195478355", settings.VERTEX_PROJECT_ID, "mb-poc-352009"]:
        try:
            res = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest", f"--secret={secret_name}", f"--project={project}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=1.0
            )
            val = res.stdout.strip()
            if val:
                return val
        except Exception:
            continue
    return None


def get_twilio_credentials() -> Dict[str, Optional[str]]:
    """Resolves Twilio credentials from environment or GCP Secret Manager."""
    global _SECRETS_CHECKED
    if not _SECRETS_CHECKED:
        _SECRETS_CHECKED = True
        if not _TWILIO_CACHE["account_sid"]:
            _TWILIO_CACHE["account_sid"] = _get_gcp_secret("TWILIO_ACCOUNT_SID")
        if not _TWILIO_CACHE["auth_token"]:
            _TWILIO_CACHE["auth_token"] = _get_gcp_secret("TWILIO_AUTH_TOKEN")
    return _TWILIO_CACHE


def clean_recipient_phone(phone: str) -> str:
    """Formats phone number to standard E.164 (e.g. +919819657034)."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        return f"+{digits}"
    elif len(digits) == 10:
        return f"+91{digits}"
    elif phone.startswith("+"):
        return phone.replace(" ", "").replace("-", "")
    return f"+{digits}"


class NotificationService:
    @staticmethod
    async def send_test_drive_confirmation(
        customer_phone: str,
        customer_name: str,
        booking_reference: str,
        vehicle_name: str,
        variant: str,
        slot_date: str,
        slot_time: str,
        dealership_name: str,
        sales_advisor_name: str,
        booking_type: str = "HOME_DOORSTEP",
        delivery_address: Optional[str] = None,
        pin_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches SMS via Twilio API immediately as soon as test ride booking is confirmed.
        """
        creds = get_twilio_credentials()
        account_sid = creds.get("account_sid")
        auth_token = creds.get("auth_token")
        from_phone = creds.get("phone_number") or "+13369154920"

        formatted_phone = clean_recipient_phone(customer_phone)

        address_line = (
            f"📍 Doorstep Address: {delivery_address} (PIN: {pin_code})"
            if booking_type == "HOME_DOORSTEP" and delivery_address
            else f"🏢 Showroom Visit: {dealership_name}"
        )

        message_body = (
            f"🚗 Namaste {customer_name}! Your Mahindra Test Ride is CONFIRMED.\n\n"
            f"📋 Booking ID: {booking_reference}\n"
            f"🚘 Vehicle: {vehicle_name}\n"
            f"⚙️ Variant: {variant}\n"
            f"🗓️ Date & Slot: {slot_date} at {slot_time}\n"
            f"🏢 Dealership: {dealership_name}\n"
            f"{address_line}\n"
            f"👨‍💼 Specialist: {sales_advisor_name}\n\n"
            f"Thank you for choosing Mahindra & Mahindra!"
        )

        result: Dict[str, Any] = {
            "success": False,
            "channel": "SMS",
            "recipient": formatted_phone,
            "message_body": message_body,
            "sms_sid": None,
            "status": "INITIATED"
        }

        # Chargeable SMS Guard: Disabled by default via config
        if not settings.ENABLE_SMS_DISPATCH:
            logger.info(f"[SMS DISABLED BY CONFIG] Live chargeable SMS dispatch skipped for {formatted_phone}. Simulated successfully.")
            result["status"] = "SIMULATED_CONFIG_OFF"
            result["success"] = True
            return result

        if account_sid and auth_token:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        url,
                        auth=(account_sid, auth_token),
                        data={
                            "From": from_phone,
                            "To": formatted_phone,
                            "Body": message_body
                        }
                    )
                    resp_data = resp.json() if resp.status_code in [200, 201] else {}
                    if resp.status_code in [200, 201]:
                        sms_sid = resp_data.get("sid")
                        logger.info(f"Twilio SMS dispatched successfully to {formatted_phone} (SID: {sms_sid})")
                        result["success"] = True
                        result["sms_sid"] = sms_sid
                        result["status"] = resp_data.get("status", "queued")
                    else:
                        err_msg = resp.text
                        logger.warning(f"Twilio SMS API error ({resp.status_code}): {err_msg}")
                        result["error"] = err_msg
                        result["status"] = "API_ERROR"
            except Exception as ex:
                logger.error(f"Failed to dispatch Twilio SMS: {ex}")
                result["error"] = str(ex)
                result["status"] = "DISPATCH_FAILED"
        else:
            logger.info(f"[SIMULATED SMS] Sent to {formatted_phone}:\n{message_body}")
            result["status"] = "SIMULATED"
            result["success"] = True

        return result
