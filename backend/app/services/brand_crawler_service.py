import re
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

from app.config import settings
from app.schemas.brand import BrandCatalog
from app.schemas.catalog import VehicleItem, VehicleVariant, DealershipItem

logger = logging.getLogger("brand_crawler_service")

class BrandCrawlerService:
    @classmethod
    async def crawl_and_extract_catalog(cls, brand_name: str, urls: List[str]) -> BrandCatalog:
        """
        Crawls multiple URLs for a given brand name, extracts DOM text, metadata,
        and high-resolution image candidates, and uses Gemini to synthesize a structured
        Brand Catalog with full vehicle lineup, variants, specs, and hero images.
        """
        logger.info(f"Crawling {len(urls)} URLs for brand '{brand_name}'")
        
        extracted_pages = []
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            }
        ) as client:
            tasks = [cls._fetch_and_parse_page(client, url) for url in urls if url.strip()]
            extracted_pages = await asyncio.gather(*tasks, return_exceptions=True)

        valid_pages = [p for p in extracted_pages if isinstance(p, dict)]
        logger.info(f"Successfully scraped {len(valid_pages)} pages for brand '{brand_name}'")

        # Compile consolidated context for Gemini
        page_summaries = []
        all_candidate_images = []
        brand_logos = []

        for p in valid_pages:
            page_summaries.append({
                "url": p["url"],
                "title": p.get("title", ""),
                "meta_description": p.get("meta_description", ""),
                "headings": p.get("headings", [])[:15],
                "text_snippet": p.get("text_snippet", "")[:2000]
            })
            all_candidate_images.extend(p.get("images", []))
            if p.get("og_image"):
                all_candidate_images.append(p["og_image"])
            if p.get("logo_candidates"):
                brand_logos.extend(p["logo_candidates"])

        # Deduplicate images
        candidate_images = list(dict.fromkeys(all_candidate_images))[:40]
        detected_logo = brand_logos[0] if brand_logos else (candidate_images[0] if candidate_images else "")

        # Synthesize with Gemini
        catalog = await cls._extract_with_gemini(
            brand_name=brand_name,
            urls=urls,
            page_summaries=page_summaries,
            candidate_images=candidate_images,
            detected_logo=detected_logo
        )

        return catalog

    @classmethod
    async def _fetch_and_parse_page(cls, client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
        try:
            resp = await client.get(url)
            if resp.status_code >= 400:
                logger.warning(f"HTTP {resp.status_code} fetching {url}")
                return {"url": url, "error": f"HTTP {resp.status_code}"}

            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"].strip()

            og_image = ""
            og_tag = soup.find("meta", attrs={"property": "og:image"})
            if og_tag and og_tag.get("content"):
                og_image = urljoin(url, og_tag["content"].strip())

            # Headings
            headings = []
            for tag in soup.find_all(["h1", "h2", "h3"]):
                h_text = tag.get_text(strip=True)
                if h_text and len(h_text) < 120 and h_text not in headings:
                    headings.append(h_text)

            # Images
            images = []
            logo_candidates = []
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if not src:
                    continue
                full_src = urljoin(url, src.strip())
                alt = (img.get("alt") or "").lower()
                classes = " ".join(img.get("class") or []).lower()

                # Filter tracking / tiny pixels
                if any(x in full_src.lower() for x in ["icon", "pixel", "analytics", "badge", "tracking", ".svg"]):
                    if "logo" in alt or "logo" in classes or "brand" in classes:
                        logo_candidates.append(full_src)
                    continue

                if "logo" in alt or "logo" in classes:
                    logo_candidates.append(full_src)
                elif any(ext in full_src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    images.append(full_src)

            # Text body snippet
            for s in soup(["script", "style", "nav", "footer", "noscript"]):
                s.decompose()
            body_text = soup.get_text(separator=" ", strip=True)
            body_text = re.sub(r'\s+', ' ', body_text)

            return {
                "url": url,
                "title": title,
                "meta_description": meta_desc,
                "og_image": og_image,
                "headings": headings,
                "images": images[:25],
                "logo_candidates": logo_candidates,
                "text_snippet": body_text[:3000]
            }
        except Exception as e:
            logger.error(f"Error parsing page {url}: {e}")
            return {"url": url, "error": str(e)}

    @classmethod
    async def _extract_with_gemini(
        cls,
        brand_name: str,
        urls: List[str],
        page_summaries: List[Dict[str, Any]],
        candidate_images: List[str],
        detected_logo: str
    ) -> BrandCatalog:
        prompt = f"""You are an elite automotive intelligence and catalog extraction engine.
Given the brand name: "{brand_name}" and the crawled web page summaries and image links below:

Page Data:
{json.dumps(page_summaries, indent=2)}

Candidate Image URLs found on the website:
{json.dumps(candidate_images[:30], indent=2)}

Detected Logo Candidate:
{detected_logo}

Generate a comprehensive, production-ready brand catalog JSON for {brand_name}.
Output strictly a JSON object with this exact schema:
{{
  "id": "slug_id (e.g. tesla, bmw, hyundai, rivian)",
  "name": "Official Brand Display Name",
  "tagline": "Inspiring brand motto or tagline",
  "logo_url": "URL to brand logo from candidates, or empty string",
  "primary_color": "Dominant brand hex color code (e.g. #002c5f, #e82127, #0066b1)",
  "secondary_color": "#0f172a",
  "accent_color": "#38bdf8",
  "avatar_name": "Proposed AI specialist name (e.g. Nova, Aria, Elena, Kabir)",
  "avatar_voice": "Puck (or Aoede, Fenrir, Kore)",
  "vehicles": [
    {{
      "id": "normalized_vehicle_slug",
      "name": "Full Vehicle Model Name",
      "tagline": "Vehicle tagline or catchphrase",
      "category": "Authentic SUV / Tech SUV / Born Electric SUV / Sedan / Coupe / Commercial",
      "price_range": "Price range (e.g. $45,000 - $62,000 or ₹15.00 Lakh - ₹25.00 Lakh)",
      "hero_image": "Best candidate image URL from the list for this vehicle (must use one from candidates if available)",
      "engine_specs": "Engine or motor specs (horsepower, torque, powertrain)",
      "seating_capacity": "5-Seater / 7-Seater",
      "fuel_or_battery": "Electric / Petrol / Diesel / Hybrid",
      "range_or_mileage": "Range or fuel efficiency (e.g. 520 km WLTP or 18.5 km/l)",
      "key_highlights": [
        "Key highlight 1",
        "Key highlight 2",
        "Key highlight 3",
        "Key highlight 4"
      ],
      "usp": "Unique selling proposition of this vehicle",
      "variants": [
        {{
          "name": "Trim Name (e.g. Long Range AWD / Performance / Top Spec)",
          "price_ex_showroom": "Ex-showroom price",
          "engine_or_battery": "Specific powertrain",
          "transmission": "Automatic / Single-Speed / Manual",
          "key_features": ["Feature 1", "Feature 2", "Feature 3"]
        }}
      ]
    }}
  ],
  "dealerships": [
    {{
      "id": "flagship_center_1",
      "name": "{brand_name} Experience Center",
      "address": "Flagship Showroom Avenue, Metro Downtown",
      "city": "Mumbai",
      "phone": "+91 22 4000 8800",
      "rating": 4.9,
      "available_advisors": ["Senior Brand Specialist", "Product Genius"],
      "has_test_drive_home_pickup": true
    }}
  ]
}}

Ensure at least 2 to 6 vehicles are extracted. If the pages mention models, extract all of them accurately. If an image candidate fits a vehicle, assign it to hero_image. Output ONLY raw valid JSON."""

        raw_json_str = ""
        try:
            client = genai.Client(
                vertexai=True,
                project=settings.VERTEX_PROJECT_ID,
                location=settings.VERTEX_LOCATION
            )
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=3000,
                response_mime_type="application/json"
            )
            # Use REST_CHAT_MODEL or gemini-2.5-flash / latest
            model_to_use = getattr(settings, "REST_CHAT_MODEL", "gemini-2.5-flash")
            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=model_to_use,
                contents=prompt,
                config=config
            )
            if resp and resp.text:
                raw_json_str = resp.text.strip()
        except Exception as e:
            logger.warning(f"Vertex AI Gemini extraction notice (using resilient fallback): {e}")

        # Parse JSON
        if raw_json_str:
            try:
                # Strip markdown codeblocks if present
                clean_json = re.sub(r'^```(json)?\n', '', raw_json_str, flags=re.MULTILINE)
                clean_json = re.sub(r'\n```$', '', clean_json, flags=re.MULTILINE).strip()
                data = json.loads(clean_json)
                data["source_urls"] = urls
                data["is_active"] = True
                return BrandCatalog(**data)
            except Exception as pe:
                logger.error(f"Failed to parse Gemini JSON output: {pe}")

        # Resilient Fallback Catalog if Gemini unavailable or failed
        slug = re.sub(r'[^a-z0-9]+', '_', brand_name.lower()).strip('_')
        fallback_vehicles = []
        
        # Build vehicles from page titles or headings
        sample_names = [p.get("title", "").split("|")[0].split("-")[0].strip() for p in page_summaries if p.get("title")]
        if not sample_names:
            sample_names = [f"{brand_name} Model 1", f"{brand_name} Model 2"]

        for i, name in enumerate(sample_names[:4]):
            v_slug = f"{slug}_v{i+1}"
            img = candidate_images[i] if i < len(candidate_images) else ""
            fallback_vehicles.append(VehicleItem(
                id=v_slug,
                name=f"{brand_name} {name}" if brand_name.lower() not in name.lower() else name,
                tagline=f"Experience the excellence of {brand_name}",
                category="Authentic SUV" if "suv" in name.lower() else "Tech SUV",
                price_range="Contact Showroom for Price",
                hero_image=img or "/assets/placeholder-car.png",
                engine_specs="High Performance Powertrain",
                seating_capacity="5-Seater",
                fuel_or_battery="Electric / Hybrid",
                range_or_mileage="Standard Range",
                key_highlights=[
                    "Next-Gen Digital Cockpit",
                    "Advanced Driver Assistance System",
                    "Premium Audio & Luxury Interior"
                ],
                usp=f"Signature engineering and comfort from {brand_name}",
                variants=[
                    VehicleVariant(
                        name="Standard Edition",
                        price_ex_showroom="Official Showroom Quote",
                        engine_or_battery="Standard Powertrain",
                        transmission="Automatic",
                        key_features=["Digital Cluster", "Keyless Entry", "Safety Package"]
                    )
                ],
                is_custom_source_of_truth=False
            ))

        return BrandCatalog(
            id=slug,
            name=brand_name,
            tagline=f"Official {brand_name} Experience Center",
            logo_url=detected_logo,
            primary_color="#002c5f" if "hyundai" in slug else ("#e82127" if "red" in slug else "#1b2028"),
            secondary_color="#0f172a",
            accent_color="#0ea5e9",
            avatar_name="Advisor",
            avatar_voice="Puck",
            source_urls=urls,
            is_active=True,
            vehicles=fallback_vehicles,
            dealerships=[
                DealershipItem(
                    id=f"{slug}_dealership",
                    name=f"{brand_name} Flagship Center",
                    address="Downtown Auto District",
                    city="Mumbai",
                    phone="+91 22 4000 8800",
                    rating=4.9,
                    available_advisors=["Senior Consultant"],
                    has_test_drive_home_pickup=True
                )
            ]
        )
