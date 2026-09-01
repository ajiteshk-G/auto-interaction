import os
import time
import asyncio
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("gemini_image_service")

STATIC_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "static",
    "uploads"
)

GENERATE_CLI = "/google/bin/releases/gemini-agents-generate/generate"

class GeminiImageService:
    """
    Generates photorealistic, avant-garde, completely non-proprietary concept vehicle
    images using Gemini's native image generation capabilities (codename 'Nano Banana' / gempix-1).
    Ensures that fictitious brand vehicles do not infringe or resemble proprietary commercial brands.
    """

    @classmethod
    async def generate_concept_car_image(
        cls,
        brand_id: str,
        vehicle_id: str,
        vehicle_name: str,
        category: str,
        styling_notes: Optional[str] = None,
        prompt_override: Optional[str] = None,
        timeout_seconds: int = 40
    ) -> Optional[str]:
        """
        Generates a non-proprietary concept car PNG using Gemini and saves it to static uploads.
        Returns the public URL path: /uploads/{brand_id}/vehicles/{filename}
        """
        b_id = brand_id.lower().strip()
        v_id = vehicle_id.lower().strip()
        dest_dir = os.path.join(STATIC_UPLOAD_DIR, b_id, "vehicles")
        os.makedirs(dest_dir, exist_ok=True)

        filename = f"{v_id}_concept_{int(time.time())}.png"
        dest_path = os.path.join(dest_dir, filename)

        # Build prompt ensuring realistic, normal contemporary production road cars (strictly not futuristic, sci-fi, or far-future concept designs)
        notes_str = f" Features: {styling_notes}." if styling_notes else ""
        prompt = prompt_override or (
            f"A crisp photorealistic photograph of a normal, contemporary production road car: '{vehicle_name}', "
            f"body style: {category}.{notes_str} "
            f"Realistic, standard commercial production car styling as seen driven on real city roads today. "
            f"Believable modern passenger vehicle design, standard production alloy wheels, realistic headlights, real side mirrors, normal door handles, authentic street vehicle proportions. "
            f"Strictly a normal everyday production passenger car — NOT futuristic, NOT a sci-fi vehicle, NOT a spaceship, NOT a far-future prototype concept car. "
            f"Clean unbranded bodywork with no trademarked logos or commercial manufacturer emblems. "
            f"Professional real-world automotive showroom photography, clean showroom floor with gentle natural daylight reflections, 3/4 front angle view, high quality 4k resolution, authentic realistic car finish."
        )

        logger.info(f"Generating realistic normal road car image for {vehicle_name} ({b_id}/{v_id})...")

        if os.path.exists(GENERATE_CLI):
            try:
                proc = await asyncio.create_subprocess_exec(
                    GENERATE_CLI,
                    f"-output={dest_path}",
                    "-timeout=45s",
                    "image",
                    prompt,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)

                if proc.returncode == 0 and os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
                    public_url = f"/uploads/{b_id}/vehicles/{filename}"
                    logger.info(f"Gemini Nano Banana image generated successfully: {public_url} ({os.path.getsize(dest_path)} bytes)")
                    return public_url
                else:
                    err_msg = stderr.decode().strip() if stderr else stdout.decode().strip()
                    logger.warning(f"generate CLI returned code {proc.returncode}: {err_msg}")
            except asyncio.TimeoutError:
                logger.warning(f"Image generation timed out after {timeout_seconds}s for {vehicle_name}")
            except Exception as e:
                logger.warning(f"Failed invoking generate CLI for {vehicle_name}: {e}")

        logger.warning(f"Could not generate AI concept image for {vehicle_name}")
        return None

    @classmethod
    async def generate_images_for_vehicles_batch(
        cls,
        brand_id: str,
        vehicles: List[Dict[str, Any]],
        concurrency: int = 2
    ) -> Dict[str, str]:
        """
        Generates concept car images for a batch of vehicles with bounded concurrency.
        Returns a mapping of vehicle_id -> public_image_url.
        """
        semaphore = asyncio.Semaphore(concurrency)
        results: Dict[str, str] = {}

        async def _worker(v: Dict[str, Any]):
            v_id = v.get("id") or "vehicle"
            v_name = v.get("name") or "Concept Vehicle"
            cat = v.get("category") or "Electric Vehicle"
            usp = v.get("usp") or ""
            async with semaphore:
                url = await cls.generate_concept_car_image(
                    brand_id=brand_id,
                    vehicle_id=v_id,
                    vehicle_name=v_name,
                    category=cat,
                    styling_notes=usp
                )
                if url:
                    results[v_id] = url

        tasks = [_worker(v) for v in vehicles]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results
