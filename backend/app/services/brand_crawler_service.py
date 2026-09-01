import os
import re
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

from app.config import settings
from app.schemas.brand import BrandCatalog
from app.schemas.catalog import VehicleItem, VehicleVariant, DealershipItem

logger = logging.getLogger("brand_crawler_service")

STATIC_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "static",
    "uploads"
)
os.makedirs(STATIC_UPLOAD_DIR, exist_ok=True)

# Curated, verified high-resolution automotive CDN images (all returning HTTP 200)
UNSPLASH_CATEGORY_POOLS: Dict[str, List[str]] = {
    "hypercar": [
        "https://images.unsplash.com/photo-1617788138017-80ad40651399?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544829099-b9a0c07fad1a?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1525609004556-c46c7d6cf023?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=1200&auto=format&fit=crop&q=80",
    ],
    "coupe": [
        "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1603584173870-7f23fdae1b7a?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1200&auto=format&fit=crop&q=80",
    ],
    "suv": [
        "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1508974239320-0a029497e820?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1606016159991-dfe4f2746ad5?w=1200&auto=format&fit=crop&q=80",
    ],
    "electric": [
        "https://images.unsplash.com/photo-1563720223185-11003d516935?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1560958089-b8a1929cea89?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1536700503339-1e4b06520771?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?w=1200&auto=format&fit=crop&q=80",
    ],
    "sedan": [
        "https://images.unsplash.com/photo-1555353540-64580b51c258?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=1200&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1617469767053-d3b523a0b982?w=1200&auto=format&fit=crop&q=80",
    ]
}

# Curated authentic lineups for common automotive brands as resilient fallback
KNOWN_BRAND_PROFILES: Dict[str, Dict[str, Any]] = {
    "bmw": {
        "name": "BMW",
        "tagline": "Sheer Driving Pleasure",
        "primary_color": "#0066b1",
        "secondary_color": "#0f172a",
        "accent_color": "#38bdf8",
        "logo_url": "https://imgd.aeplcdn.com/0x0/n/cw/ec/10/brands/logos/bmw.jpg",
        "avatar_name": "Klaus",
        "avatar_voice": "Puck",
        "vehicles": [
            {
                "id": "bmw_3_series_gl",
                "name": "BMW 3 Series Gran Limousine",
                "tagline": "The Ultimate Luxury Sports Sedan",
                "category": "Sedan",
                "price_range": "₹60.60 Lakh - ₹72.90 Lakh",
                "hero_image": "https://imgd.aeplcdn.com/1056x594/n/cw/ec/140591/3-series-gran-limousine-exterior-right-front-three-quarter-3.jpeg",
                "engine_specs": "2.0L TwinPower Turbo Petrol (258 hp, 400 Nm) / 2.0L Diesel (190 hp)",
                "seating_capacity": "5-Seater",
                "fuel_or_battery": "Petrol / Diesel",
                "range_or_mileage": "15.39 km/l",
                "key_highlights": [
                    "BMW Curved Display with OS 8.5",
                    "Panoramic Glass Sunroof",
                    "Harman Kardon 16-Speaker Surround Sound",
                    "Long-Wheelbase Extra Rear Legroom"
                ],
                "usp": "Long-wheelbase executive comfort fused with BMW's iconic 50:50 weight distribution and dynamic handling.",
                "variants": [
                    {
                        "name": "330Li M Sport",
                        "price_ex_showroom": "₹60,60,000",
                        "engine_or_battery": "2.0L TwinPower Turbo Petrol (258 hp)",
                        "transmission": "8-Speed Steptronic Sport",
                        "key_features": ["M Aerodynamics Package", "Live Cockpit Professional", "Ambient Lighting"]
                    },
                    {
                        "name": "320Ld M Sport",
                        "price_ex_showroom": "₹62,00,000",
                        "engine_or_battery": "2.0L TwinPower Turbo Diesel (190 hp)",
                        "transmission": "8-Speed Steptronic Sport",
                        "key_features": ["Parking Assistant Plus", "Sport Seats", "Wireless Apple CarPlay"]
                    },
                    {
                        "name": "M340i xDrive",
                        "price_ex_showroom": "₹72,90,000",
                        "engine_or_battery": "3.0L Inline-6 Turbo Petrol (374 hp)",
                        "transmission": "8-Speed Steptronic Sport",
                        "key_features": ["xDrive Intelligent AWD", "M Sport Differential", "0-100 km/h in 4.4s"]
                    }
                ]
            },
            {
                "id": "bmw_x5",
                "name": "BMW X5",
                "tagline": "The Boss. Benchmark Luxury SUV",
                "category": "Authentic SUV",
                "price_range": "₹97.00 Lakh - ₹1.11 Crore",
                "hero_image": "https://imgd.aeplcdn.com/1056x594/n/cw/ec/152681/x5-facelift-exterior-right-front-three-quarter-3.jpeg",
                "engine_specs": "3.0L TwinPower Turbo 6-Cylinder 48V Mild-Hybrid (381 hp, 520 Nm)",
                "seating_capacity": "5-Seater",
                "fuel_or_battery": "Petrol / Diesel (Mild-Hybrid)",
                "range_or_mileage": "12.0 km/l",
                "key_highlights": [
                    "Adaptive 2-Axle Air Suspension",
                    "BMW Curved Display (14.9-inch)",
                    "Panoramic Sky Lounge LED Roof",
                    "Active Driving Assistant Professional"
                ],
                "usp": "Supreme commanding road presence, active air suspension ride mastery, and opulent luxury.",
                "variants": [
                    {
                        "name": "xDrive40i xLine",
                        "price_ex_showroom": "₹97,00,000",
                        "engine_or_battery": "3.0L Inline-6 Turbo Petrol Mild-Hybrid",
                        "transmission": "8-Speed Steptronic Sport",
                        "key_features": ["Adaptive Air Suspension", "Comfort Seats", "Harman Kardon Audio"]
                    },
                    {
                        "name": "xDrive40i M Sport",
                        "price_ex_showroom": "₹1,09,00,000",
                        "engine_or_battery": "3.0L Inline-6 Turbo Petrol Mild-Hybrid",
                        "transmission": "8-Speed Steptronic Sport",
                        "key_features": ["M Sport Brakes", "M Aerodynamic Package", "21-inch M Light Alloys"]
                    },
                    {
                        "name": "xDrive30d M Sport",
                        "price_ex_showroom": "₹1,11,00,000",
                        "engine_or_battery": "3.0L Inline-6 Turbo Diesel Mild-Hybrid (286 hp)",
                        "transmission": "8-Speed Steptronic Sport",
                        "key_features": ["650 Nm Torque", "Integral Active Steering", "Parking Assistant Pro"]
                    }
                ]
            },
            {
                "id": "bmw_ix",
                "name": "BMW iX Electric SAV",
                "tagline": "Born Electric. The Pioneer of a New Era",
                "category": "Born Electric SUV",
                "price_range": "₹1.21 Crore - ₹1.40 Crore",
                "hero_image": "https://imgd.aeplcdn.com/1056x594/n/cw/ec/106821/ix-exterior-right-front-three-quarter.jpeg",
                "engine_specs": "Dual Electrically Excited Synchronous Motors (326 - 523 hp)",
                "seating_capacity": "5-Seater",
                "fuel_or_battery": "Electric (111.5 kWh Battery)",
                "range_or_mileage": "630 km WLTP Range",
                "key_highlights": [
                    "630 km WLTP Electric Driving Range",
                    "Electrochromatic Sky Lounge Panoramic Glass Roof",
                    "Carbon Core Architecture",
                    "Bowers & Wilkins 30-Speaker 4D Diamond Audio"
                ],
                "usp": "Ultra-luxury electric flagship crafted with sustainable materials and 195 kW DC fast-charging capability.",
                "variants": [
                    {
                        "name": "xDrive40",
                        "price_ex_showroom": "₹1,21,00,000",
                        "engine_or_battery": "76.6 kWh Dual Motor AWD (326 hp)",
                        "transmission": "Single-Speed",
                        "key_features": ["425 km Range", "Curved Display", "BMW Driving Assistant"]
                    },
                    {
                        "name": "xDrive50",
                        "price_ex_showroom": "₹1,39,50,000",
                        "engine_or_battery": "111.5 kWh Dual Motor AWD (523 hp)",
                        "transmission": "Single-Speed",
                        "key_features": ["630 km Range", "2-Axle Air Suspension", "Integral Active 4-Wheel Steering"]
                    }
                ]
            },
            {
                "id": "bmw_5_series_lwb",
                "name": "BMW 5 Series Long Wheelbase",
                "tagline": "The Business Athlete with Supreme Rear Comfort",
                "category": "Sedan",
                "price_range": "₹72.90 Lakh - ₹82.00 Lakh",
                "hero_image": "https://imgd.aeplcdn.com/1056x594/n/cw/ec/174975/5-series-exterior-right-front-three-quarter.jpeg",
                "engine_specs": "2.0L TwinPower Turbo Petrol with 48V Mild-Hybrid (258 hp, 400 Nm)",
                "seating_capacity": "5-Seater",
                "fuel_or_battery": "Petrol (Mild-Hybrid)",
                "range_or_mileage": "15.7 km/l",
                "key_highlights": [
                    "Extended Long-Wheelbase Rear Executive Cabin",
                    "BMW Interaction Bar with Backlit Ambient Glass",
                    "18-Speaker Bowers & Wilkins Surround Sound",
                    "Level 2+ Driving Assistant"
                ],
                "usp": "India's first right-hand drive Long-Wheelbase 5 Series offering segment-first rear lounge comfort.",
                "variants": [
                    {
                        "name": "530Li M Sport",
                        "price_ex_showroom": "₹72,90,000",
                        "engine_or_battery": "2.0L Turbo Mild-Hybrid",
                        "transmission": "8-Speed Steptronic Sport",
                        "key_features": ["BMW Interaction Bar", "Bowers & Wilkins Audio", "Panoramic Glass Roof"]
                    }
                ]
            }
        ]
    },
    "mercedes": {
        "name": "Mercedes-Benz",
        "tagline": "The Best or Nothing",
        "primary_color": "#000000",
        "secondary_color": "#1e293b",
        "accent_color": "#00a3e0",
        "logo_url": "https://imgd.aeplcdn.com/0x0/n/cw/ec/18/brands/logos/mercedes-benz.jpg",
        "avatar_name": "Mercedes Expert",
        "avatar_voice": "Aoede",
        "vehicles": [
            {
                "id": "mercedes_c_class",
                "name": "Mercedes-Benz C-Class",
                "tagline": "The Baby S-Class with Supreme Tech",
                "category": "Sedan",
                "price_range": "₹61.85 Lakh - ₹69.00 Lakh",
                "hero_image": "https://imgd.aeplcdn.com/1056x594/n/cw/ec/115871/c-class-exterior-right-front-three-quarter-3.jpeg",
                "engine_specs": "2.0L Turbo Mild-Hybrid (204 - 265 hp)",
                "seating_capacity": "5-Seater",
                "fuel_or_battery": "Petrol / Diesel",
                "range_or_mileage": "17.5 km/l",
                "key_highlights": ["11.9-inch Portrait MBUX Display", "Burmester 3D Surround Sound", "Panoramic Sliding Roof"],
                "usp": "S-Class inspired luxury cockpit with biometric fingerprint authentication and EQ Boost mild hybrid.",
                "variants": [
                    {
                        "name": "C 200",
                        "price_ex_showroom": "₹61,85,000",
                        "engine_or_battery": "1.5L Turbo Petrol Mild-Hybrid",
                        "transmission": "9G-TRONIC Automatic",
                        "key_features": ["MBUX Navigation", "Wireless Smartphone Integration", "Active Brake Assist"]
                    },
                    {
                        "name": "C 220d",
                        "price_ex_showroom": "₹63,85,000",
                        "engine_or_battery": "2.0L Turbo Diesel Mild-Hybrid",
                        "transmission": "9G-TRONIC Automatic",
                        "key_features": ["440 Nm Torque", "Ambient Lighting 64 Colors", "LED High Performance Headlamps"]
                    }
                ]
            },
            {
                "id": "mercedes_glc",
                "name": "Mercedes-Benz GLC",
                "tagline": "Ready for Whatever Comes",
                "category": "Authentic SUV",
                "price_range": "₹75.90 Lakh - ₹76.90 Lakh",
                "hero_image": "https://imgd.aeplcdn.com/1056x594/n/cw/ec/144681/glc-exterior-right-front-three-quarter-4.jpeg",
                "engine_specs": "2.0L Turbo with 4MATIC AWD (204 - 258 hp)",
                "seating_capacity": "5-Seater",
                "fuel_or_battery": "Petrol / Diesel",
                "range_or_mileage": "14.7 km/l",
                "key_highlights": ["Transparent Bonnet Off-Road View", "4MATIC All-Wheel Drive", "Digital Light Headlamps"],
                "usp": "Dynamic SUV design with permanent 4MATIC AWD and transparent bonnet camera technology.",
                "variants": [
                    {
                        "name": "GLC 300 4MATIC",
                        "price_ex_showroom": "₹75,90,000",
                        "engine_or_battery": "2.0L Turbo Petrol (258 hp)",
                        "transmission": "9G-TRONIC Automatic",
                        "key_features": ["Panoramic Sunroof", "Burmester Surround Sound", "4MATIC AWD"]
                    },
                    {
                        "name": "GLC 220d 4MATIC",
                        "price_ex_showroom": "₹76,90,000",
                        "engine_or_battery": "2.0L Turbo Diesel (197 hp)",
                        "transmission": "9G-TRONIC Automatic",
                        "key_features": ["440 Nm Torque", "Off-Road Cockpit", "360 Surround View Camera"]
                    }
                ]
            }
        ]
    }
}

class BrandCrawlerService:
    @classmethod
    def _generate_brand_vector_logo(cls, brand_id: str, brand_name: str, primary_color: str) -> str:
        """
        Creates an ultra-modern geometric automotive crest SVG for fictional or URL-less brands
        and saves it to the static uploads directory.
        """
        dest_dir = os.path.join(STATIC_UPLOAD_DIR, brand_id.lower(), "logos")
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, "logo.svg")

        clean_words = [w for w in brand_name.split() if w]
        initials = "".join(w[0].upper() for w in clean_words[:2]) if clean_words else "AI"
        color = primary_color if (primary_color and primary_color.startswith("#")) else "#0ea5e9"
        display_name = brand_name.upper()[:16]

        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 54" width="220" height="54">
  <defs>
    <linearGradient id="crestGrad_{brand_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color}" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
  </defs>
  <!-- Modern Geometric Automotive Crest -->
  <polygon points="8,14 32,8 44,24 28,38 6,24" fill="url(#crestGrad_{brand_id})" stroke="{color}" stroke-width="1.5" />
  <polygon points="24,22 38,18 46,28 34,40 20,32" fill="{color}" opacity="0.35" />
  <polyline points="4,28 18,44 48,16" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" />
  <!-- Monogram -->
  <text x="26" y="27" fill="#ffffff" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="13" text-anchor="middle" letter-spacing="1">{initials}</text>
  <!-- Brand Display Name -->
  <text x="56" y="28" fill="#0f172a" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="15" letter-spacing="1.5">{display_name}</text>
  <text x="56" y="41" fill="{color}" font-family="system-ui, -apple-system, sans-serif" font-weight="700" font-size="7.5" letter-spacing="2.5">INTELLIGENT PERFORMANCE</text>
</svg>'''
        try:
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            return f"/uploads/{brand_id.lower()}/logos/logo.svg"
        except Exception as e:
            logger.warning(f"Notice: Failed to write SVG logo: {e}")
            return ""

    @classmethod
    async def crawl_and_extract_catalog(cls, brand_name: str, urls: List[str]) -> BrandCatalog:
        clean_urls = [u.strip() for u in (urls or []) if u and u.strip()]
        if not clean_urls:
            logger.info(f"No URLs provided for brand '{brand_name}'. Synthesizing catalog directly using automotive intelligence.")
            return await cls._extract_with_gemini(
                brand_name=brand_name,
                urls=[],
                page_summaries=[],
                candidate_images=[],
                detected_logo=""
            )

        logger.info(f"Crawling {len(clean_urls)} URLs for brand '{brand_name}'")
        
        extracted_pages = []
        async with httpx.AsyncClient(
            timeout=5.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        ) as client:
            tasks = [cls._fetch_and_parse_page(client, url) for url in clean_urls]
            extracted_pages = await asyncio.gather(*tasks, return_exceptions=True)

        valid_pages = [p for p in extracted_pages if isinstance(p, dict) and "error" not in p]
        logger.info(f"Successfully scraped {len(valid_pages)} / {len(clean_urls)} pages for brand '{brand_name}'")

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

        candidate_images = list(dict.fromkeys(all_candidate_images))[:40]
        detected_logo = brand_logos[0] if brand_logos else (candidate_images[0] if candidate_images else "")

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

            headings = []
            for tag in soup.find_all(["h1", "h2", "h3"]):
                h_text = tag.get_text(strip=True)
                if h_text and len(h_text) < 120 and h_text not in headings:
                    headings.append(h_text)

            images = []
            logo_candidates = []
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if not src:
                    continue
                full_src = urljoin(url, src.strip())
                alt = (img.get("alt") or "").lower()
                classes = " ".join(img.get("class") or []).lower()

                if any(x in full_src.lower() for x in ["icon", "pixel", "analytics", "badge", "tracking", ".svg"]):
                    if "logo" in alt or "logo" in classes or "brand" in classes:
                        logo_candidates.append(full_src)
                    continue

                if "logo" in alt or "logo" in classes:
                    logo_candidates.append(full_src)
                elif any(ext in full_src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    images.append(full_src)

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
            logger.warning(f"Notice: Page {url} could not be scraped ({type(e).__name__}). Proceeding with automotive domain extraction.")
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
Target Brand: "{brand_name}"
Source URLs: {json.dumps(urls)}

Crawled Web Page Summaries:
{json.dumps(page_summaries, indent=2)}

Candidate Image URLs found on the website:
{json.dumps(candidate_images[:30], indent=2)}

Detected Logo Candidate:
{detected_logo}

Instructions:
1. Synthesize a comprehensive, production-ready brand catalog JSON for {brand_name}.
2. REAL-WORLD BRANDS: If this is an existing automotive brand (e.g. BMW, Audi, Mercedes, Tesla, Porsche, Toyota, Kia, Tata, etc.), generate its authentic production vehicle lineup with genuine models, real specifications, ex-showroom pricing, trims, key highlights, and USPs.
3. FICTIONAL / NEW BRANDS / NO URLS: If this is a new, fictional, or custom brand (e.g. "Apex Motors", "Vertex Auto", "Nova Mobility", "Atlas Auto") or no URLs were provided, create a realistic, contemporary automotive brand catalog with NORMAL, production-ready road cars as driven on roads today (e.g. Compact SUV, Mid-size Authentic SUV, Family 7-Seater, Executive Sedan, Premium Hatchback, Electric Crossover).
   - CRITICAL: Keep them as NORMAL, standard production cars — strictly NOT futuristic, NOT a sci-fi vehicle, NOT a spaceship, and NOT a far-future concept prototype.
   - Use realistic contemporary ex-showroom pricing in INR Lakhs (e.g. ₹11.00 Lakh - ₹24.00 Lakh or ₹35.00 Lakh - ₹55.00 Lakh), realistic engine/battery specs, practical seating capacities (5-Seater / 7-Seater), and everyday consumer features (Touchscreen Infotainment, Sunroof, ADAS Level 2, Wireless Android Auto / Apple CarPlay, 360 Camera).
4. Set an appropriate primary_color hex code (e.g. #0066b1, #e11d48, #0ea5e9, #f59e0b, #10b981), secondary_color ("#0f172a"), accent_color, avatar_name ("Kavya"), and avatar_voice ("Aoede").
5. Extract between 4 to 6 vehicles. Each vehicle must include realistic variants (trims) with pricing and powertrain details.
6. Output STRICTLY a valid JSON object matching this exact schema:
{{
  "id": "slug_id (e.g. apex_motors, vertex_auto, bmw)",
  "name": "Brand Display Name",
  "tagline": "Inspiring brand motto or tagline",
  "logo_url": "URL to brand logo, or empty string",
  "primary_color": "#0ea5e9",
  "secondary_color": "#0f172a",
  "accent_color": "#38bdf8",
  "avatar_name": "Kavya",
  "avatar_voice": "Aoede",
  "vehicles": [
    {{
      "id": "normalized_vehicle_slug",
      "name": "Full Vehicle Model Name",
      "tagline": "Vehicle tagline or catchphrase",
      "category": "Compact SUV / Authentic SUV / Family 7-Seater / Sedan / Premium Hatchback / Electric Crossover",
      "price_range": "Price range (e.g. ₹12.00 Lakh - ₹18.50 Lakh or ₹35.00 Lakh - ₹48.00 Lakh)",
      "hero_image": "Hero image URL or empty string",
      "engine_specs": "Engine/motor specs (e.g. Tri-Motor AWD 1020 hp or 3.0L Twin-Turbo 380 hp)",
      "seating_capacity": "2-Seater / 4-Seater / 5-Seater / 7-Seater",
      "fuel_or_battery": "Electric / Petrol / Hybrid",
      "range_or_mileage": "Range or fuel efficiency (e.g. 620 km WLTP or 14.5 km/l)",
      "key_highlights": [
        "Highlight 1",
        "Highlight 2",
        "Highlight 3",
        "Highlight 4"
      ],
      "usp": "Unique selling proposition of this vehicle",
      "variants": [
        {{
          "name": "Trim Name (e.g. Dynamic Edition, Track Performance)",
          "price_ex_showroom": "Ex-showroom price",
          "engine_or_battery": "Powertrain description",
          "transmission": "Automatic / Direct Drive / Dual-Clutch",
          "key_features": ["Feature 1", "Feature 2", "Feature 3"]
        }}
      ]
    }}
  ],
  "dealerships": [
    {{
      "id": "flagship_center_1",
      "name": "{brand_name} Experience Center",
      "address": "Flagship Showroom Avenue, Worli",
      "city": "Mumbai",
      "phone": "+91 22 4000 8800",
      "rating": 4.9,
      "available_advisors": ["Senior Brand Specialist", "Product Genius"],
      "has_test_drive_home_pickup": true
    }}
  ]
}}

Output ONLY raw valid JSON without wrapping in markdown codeblocks if possible."""

        raw_json_str = ""
        try:
            client = genai.Client(
                vertexai=True,
                project=settings.VERTEX_PROJECT_ID,
                location=settings.VERTEX_LOCATION
            )
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )
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
            logger.warning(f"Vertex AI Gemini extraction notice (falling back to domain catalog): {e}")

        # Parse & Sanitize Gemini JSON output
        if raw_json_str:
            try:
                clean_json = raw_json_str.strip()
                if clean_json.startswith("```"):
                    clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                    clean_json = re.sub(r"\s*```$", "", clean_json)
                
                start_idx = clean_json.find('{')
                end_idx = clean_json.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    clean_json = clean_json[start_idx:end_idx+1]

                clean_json = re.sub(r',\s*([\]}])', r'\1', clean_json)

                data = json.loads(clean_json)

                slug = data.get("id") or re.sub(r'[^a-z0-9]+', '_', brand_name.lower()).strip('_')
                data["id"] = slug
                data["name"] = data.get("name") or brand_name
                data["tagline"] = data.get("tagline") or f"Official {brand_name} Experience Center"
                primary_color = data.get("primary_color") or "#0ea5e9"
                data["primary_color"] = primary_color

                # Generate or assign logo
                logo_url = data.get("logo_url") or detected_logo or ""
                if not logo_url or not logo_url.strip() or "placeholder" in logo_url:
                    logo_url = cls._generate_brand_vector_logo(slug, data["name"], primary_color)
                data["logo_url"] = logo_url

                data["source_urls"] = urls
                data["is_active"] = True

                # For fictional brands (no URLs provided), schedule non-proprietary concept car image
                # generation with Gemini Nano Banana in the background so HTTP onboarding responds immediately (<3s)
                # without tripping frontend or proxy gateway timeouts.
                if not urls:
                    try:
                        raw_vehicles_payload = [
                            {"id": v.get("id") or f"{slug}_v{i+1}", "name": v.get("name") or f"{brand_name} Model {i+1}", "category": v.get("category", "Authentic SUV")}
                            for i, v in enumerate(data.get("vehicles", [])) if isinstance(v, dict)
                        ]
                        asyncio.create_task(
                            cls._generate_concept_images_background(slug, raw_vehicles_payload)
                        )
                    except Exception as bg_err:
                        logger.warning(f"Background concept generation task schedule notice: {bg_err}")

                sanitized_vehicles = []
                for idx, v in enumerate(data.get("vehicles", [])):
                    if not isinstance(v, dict):
                        continue
                    v_id = v.get("id") or f"{slug}_v{idx+1}"
                    v_name = v.get("name") or f"{brand_name} Model {idx+1}"
                    
                    hero_img = cls._resolve_vehicle_hero_image(
                        brand_name=brand_name,
                        vehicle_name=v_name,
                        category=v.get("category", ""),
                        proposed_image=v.get("hero_image", ""),
                        candidate_images=candidate_images,
                        idx=idx
                    )
                    is_custom = False
                    
                    sanitized_variants = []
                    for var in v.get("variants", []):
                        if isinstance(var, dict):
                            sanitized_variants.append(VehicleVariant(
                                name=var.get("name") or "Standard Edition",
                                price_ex_showroom=var.get("price_ex_showroom") or v.get("price_range", "Official Quote"),
                                engine_or_battery=var.get("engine_or_battery") or v.get("engine_specs", "Standard Powertrain"),
                                transmission=var.get("transmission") or "Automatic",
                                key_features=var.get("key_features") if isinstance(var.get("key_features"), list) else ["Digital Cockpit", "Smart Keyless Entry"]
                            ))
                    if not sanitized_variants:
                        sanitized_variants.append(VehicleVariant(
                            name="Standard Edition",
                            price_ex_showroom=v.get("price_range", "Official Quote"),
                            engine_or_battery=v.get("engine_specs", "Standard Powertrain"),
                            transmission="Automatic",
                            key_features=["Digital Cockpit", "Smart Keyless Entry", "Safety Package"]
                        ))

                    sanitized_vehicles.append(VehicleItem(
                        id=v_id,
                        name=v_name,
                        tagline=v.get("tagline") or f"Experience the excellence of {v_name}",
                        category=v.get("category") or "Authentic SUV",
                        price_range=v.get("price_range") or "Contact Showroom",
                        hero_image=hero_img,
                        engine_specs=v.get("engine_specs") or "High Performance Powertrain",
                        seating_capacity=v.get("seating_capacity") or "5-Seater",
                        fuel_or_battery=v.get("fuel_or_battery") or "Petrol / Hybrid",
                        range_or_mileage=v.get("range_or_mileage") or "Standard Efficiency",
                        key_highlights=v.get("key_highlights") if isinstance(v.get("key_highlights"), list) else ["Digital Cockpit", "ADAS Safety", "Connected Car Tech"],
                        usp=v.get("usp") or f"Signature engineering and comfort from {brand_name}",
                        variants=sanitized_variants,
                        is_custom_source_of_truth=is_custom,
                        uploaded_image_url=hero_img if is_custom else None
                    ))

                if sanitized_vehicles:
                    data["vehicles"] = sanitized_vehicles
                else:
                    data["vehicles"] = cls._build_domain_fallback_vehicles(brand_name, candidate_images)

                sanitized_dealerships = []
                for d in data.get("dealerships", []):
                    if isinstance(d, dict):
                        sanitized_dealerships.append(DealershipItem(
                            id=d.get("id") or f"{slug}_dealer",
                            name=d.get("name") or f"{brand_name} Experience Center",
                            address=d.get("address") or "Flagship Auto Boulevard",
                            city=d.get("city") or "Mumbai",
                            phone=d.get("phone") or "+91 22 4000 8800",
                            rating=float(d.get("rating", 4.9)),
                            available_advisors=d.get("available_advisors") if isinstance(d.get("available_advisors"), list) else ["Senior Brand Consultant", "Product Genius"],
                            has_test_drive_home_pickup=bool(d.get("has_test_drive_home_pickup", True))
                        ))
                if not sanitized_dealerships:
                    sanitized_dealerships = [DealershipItem(
                        id=f"{slug}_flagship",
                        name=f"{brand_name} Flagship Center",
                        address="Auto Boulevard, Flagship District",
                        city="Mumbai",
                        phone="+91 22 4000 8800",
                        rating=4.9,
                        available_advisors=["Senior Brand Consultant", "Product Genius"],
                        has_test_drive_home_pickup=True
                    )]
                data["dealerships"] = sanitized_dealerships

                return BrandCatalog(**data)
            except Exception as pe:
                logger.error(f"Failed to parse Gemini JSON output: {pe}")

        return cls._build_domain_fallback_catalog(brand_name, urls, candidate_images, detected_logo)

    @classmethod
    async def _generate_concept_images_background(cls, brand_id: str, vehicles: List[Dict[str, Any]]):
        """
        Background task to generate non-proprietary concept car images with Gemini Nano Banana
        without holding up the HTTP onboarding request. Updates BrandService disk cache as each finishes.
        """
        try:
            from app.services.gemini_image_service import GeminiImageService
            from app.services.brand_service import BrandService
            logger.info(f"Background AI concept car image generation started for brand '{brand_id}' ({len(vehicles)} vehicles)...")
            ai_generated_images = await GeminiImageService.generate_images_for_vehicles_batch(
                brand_id=brand_id,
                vehicles=vehicles,
                concurrency=2
            )
            for v_id, img_url in ai_generated_images.items():
                if img_url:
                    BrandService.update_vehicle_image(brand_id, v_id, img_url)
            logger.info(f"Background AI concept car image generation completed for brand '{brand_id}'.")
        except Exception as e:
            logger.warning(f"Background AI concept image generation notice: {e}")

    @classmethod
    def _resolve_vehicle_hero_image(
        cls,
        brand_name: str,
        vehicle_name: str,
        category: str,
        proposed_image: str,
        candidate_images: List[str],
        idx: int
    ) -> str:
        # 1. If proposed_image was actually scraped from candidate_images and is valid, use it
        if proposed_image and proposed_image in candidate_images:
            return proposed_image

        b_key = brand_name.lower().strip()
        v_key = vehicle_name.lower().strip()

        # 2. Curated model images for popular brands
        curated_models = [
            # BMW
            ("bmw", "3 series", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/140591/3-series-gran-limousine-exterior-right-front-three-quarter-3.jpeg"),
            ("bmw", "330", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/140591/3-series-gran-limousine-exterior-right-front-three-quarter-3.jpeg"),
            ("bmw", "m340", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/140591/3-series-gran-limousine-exterior-right-front-three-quarter-3.jpeg"),
            ("bmw", "x1", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/140589/x1-exterior-right-front-three-quarter-7.jpeg"),
            ("bmw", "x5", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/152681/x5-facelift-exterior-right-front-three-quarter-3.jpeg"),
            ("bmw", "ix", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/106821/ix-exterior-right-front-three-quarter.jpeg"),
            ("bmw", "5 series", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/174975/5-series-exterior-right-front-three-quarter.jpeg"),
            ("bmw", "7 series", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/132513/7-series-exterior-right-front-three-quarter-3.jpeg"),
            ("bmw", "i7", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/132513/7-series-exterior-right-front-three-quarter-3.jpeg"),
            ("bmw", "x3", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/110233/x3-exterior-right-front-three-quarter.jpeg"),
            ("bmw", "x7", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/137685/x7-exterior-right-front-three-quarter-2.jpeg"),
            ("bmw", "m2", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/149863/m2-exterior-right-front-three-quarter-2.jpeg"),
            ("bmw", "z4", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/147349/z4-exterior-right-front-three-quarter-2.jpeg"),
            # Mercedes
            ("mercedes", "c-class", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/115871/c-class-exterior-right-front-three-quarter-3.jpeg"),
            ("mercedes", "e-class", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/176377/e-class-exterior-right-front-three-quarter-3.jpeg"),
            ("mercedes", "glc", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/144681/glc-exterior-right-front-three-quarter-4.jpeg"),
            ("mercedes", "gle", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/161427/gle-facelift-exterior-right-front-three-quarter-2.jpeg"),
            ("mercedes", "eqs", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/124141/eqs-exterior-right-front-three-quarter-3.jpeg"),
            # Audi
            ("audi", "a4", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/51909/a4-exterior-right-front-three-quarter-2.jpeg"),
            ("audi", "a6", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/39467/a6-exterior-right-front-three-quarter-4.jpeg"),
            ("audi", "q3", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/125195/q3-exterior-right-front-three-quarter-2.jpeg"),
            ("audi", "q5", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/53591/q5-exterior-right-front-three-quarter-36.jpeg"),
            ("audi", "q7", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/106515/q7-exterior-right-front-three-quarter-2.jpeg"),
            ("audi", "e-tron", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/54609/e-tron-exterior-right-front-three-quarter-3.jpeg"),
            # Tata
            ("tata", "nexon", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/141867/nexon-exterior-right-front-three-quarter-71.jpeg"),
            ("tata", "harrier", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/154573/harrier-facelift-exterior-right-front-three-quarter-2.jpeg"),
            ("tata", "safari", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/154575/safari-facelift-exterior-right-front-three-quarter-3.jpeg"),
            ("tata", "curvv", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/139651/curvv-exterior-right-front-three-quarter.jpeg"),
            ("tata", "punch", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/168435/punch-ev-exterior-right-front-three-quarter-3.jpeg"),
            # Toyota
            ("toyota", "fortuner", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/44709/fortuner-exterior-right-front-three-quarter-20.jpeg"),
            ("toyota", "innova", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/115025/innova-hycross-exterior-right-front-three-quarter-3.jpeg"),
            ("toyota", "hyryder", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/124021/hyryder-exterior-right-front-three-quarter-72.jpeg"),
            ("toyota", "camry", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/110233/camry-exterior-right-front-three-quarter-2.jpeg"),
            # Kia
            ("kia", "seltos", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/136420/seltos-facelift-exterior-right-front-three-quarter-4.jpeg"),
            ("kia", "sonet", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/165151/sonet-facelift-exterior-right-front-three-quarter-2.jpeg"),
            ("kia", "ev6", "https://imgd.aeplcdn.com/1056x594/n/cw/ec/115867/ev6-exterior-right-front-three-quarter-2.jpeg"),
        ]
        for b_match, v_match, img_url in curated_models:
            if b_match in b_key and v_match in v_key:
                return img_url

        # 3. If candidate images has valid items
        if candidate_images:
            return candidate_images[idx % len(candidate_images)]

        # 4. If proposed_image is an external non-hallucinated URL (no content/dam)
        if proposed_image and proposed_image.startswith("http") and "content/dam" not in proposed_image and "unsplash.com" in proposed_image:
            return proposed_image

        # 5. Dynamically assign category-matched verified high-resolution Unsplash automotive photo
        cat_lower = f"{category.lower()} {vehicle_name.lower()}"
        target_pool_key = "sedan"
        if any(w in cat_lower for w in ["hyper", "supercar", "track", "gt", "apex"]):
            target_pool_key = "hypercar"
        elif any(w in cat_lower for w in ["coupe", "sport", "convertible", "roadster"]):
            target_pool_key = "coupe"
        elif any(w in cat_lower for w in ["electric", "ev", "born electric", "battery", "tesla", "cyber"]):
            target_pool_key = "electric"
        elif any(w in cat_lower for w in ["suv", "crossover", "4x4", "terrain", "all-terrain"]):
            target_pool_key = "suv"
        elif any(w in cat_lower for w in ["sedan", "limousine", "saloon", "executive", "luxury"]):
            target_pool_key = "sedan"
        else:
            pool_keys = ["hypercar", "suv", "electric", "coupe", "sedan"]
            target_pool_key = pool_keys[idx % len(pool_keys)]

        pool = UNSPLASH_CATEGORY_POOLS.get(target_pool_key, UNSPLASH_CATEGORY_POOLS["hypercar"])
        return pool[idx % len(pool)]

    @classmethod
    def _build_domain_fallback_vehicles(cls, brand_name: str, candidate_images: List[str]) -> List[VehicleItem]:
        clean_key = brand_name.lower().strip()
        for k, profile in KNOWN_BRAND_PROFILES.items():
            if k in clean_key:
                vehicles = []
                for idx, v in enumerate(profile["vehicles"]):
                    img = candidate_images[idx] if idx < len(candidate_images) else v.get("hero_image")
                    variants = [VehicleVariant(**var) for var in v.get("variants", [])]
                    vehicles.append(VehicleItem(
                        id=v["id"],
                        name=v["name"],
                        tagline=v["tagline"],
                        category=v["category"],
                        price_range=v["price_range"],
                        hero_image=img or "/assets/placeholder-car.svg",
                        engine_specs=v["engine_specs"],
                        seating_capacity=v["seating_capacity"],
                        fuel_or_battery=v["fuel_or_battery"],
                        range_or_mileage=v["range_or_mileage"],
                        key_highlights=v["key_highlights"],
                        usp=v["usp"],
                        variants=variants,
                        is_custom_source_of_truth=False
                    ))
                return vehicles

        slug = re.sub(r'[^a-z0-9]+', '_', brand_name.lower()).strip('_')
        archetypes = [
            ("Apex Hyper-GT", "Hypercar", "Aerodynamic Tri-Motor Mastery", "₹1.20 Crore - ₹1.65 Crore", "Tri-Motor AWD (1,020 hp, 0-100 in 2.1s)", "Electric (105 kWh)", "620 km WLTP"),
            ("Vanguard Horizon SUV", "Authentic SUV", "Commanding All-Terrain Luxury", "₹75.00 Lakh - ₹92.00 Lakh", "3.5L Twin-Turbo V6 Hybrid (435 hp)", "Petrol / Hybrid", "13.4 km/l"),
            ("Spectre Cyber Coupe", "Coupe", "Raw Precision Track-Tuned Performance", "₹85.00 Lakh - ₹1.10 Crore", "4.0L Biturbo V8 (580 hp)", "Petrol", "10.5 km/l"),
            ("Quantum Electra", "Born Electric SUV", "Zero Emissions, Infinite Architecture", "₹68.00 Lakh - ₹88.00 Lakh", "Dual Ultra-Torque Motors (536 hp)", "Electric (90 kWh)", "580 km WLTP"),
            ("Elysium Limousine", "Sedan", "Ultra-Executive Chauffeur Lounge", "₹95.00 Lakh - ₹1.35 Crore", "Twin-Turbo V6 Plug-in Hybrid (450 hp)", "Plug-in Hybrid", "18.2 km/l")
        ]
        vehicles = []
        for i, (model_suffix, cat, tag, price, engine, fuel, eff) in enumerate(archetypes):
            img = cls._resolve_vehicle_hero_image(
                brand_name=brand_name,
                vehicle_name=f"{brand_name} {model_suffix}",
                category=cat,
                proposed_image="",
                candidate_images=candidate_images,
                idx=i
            )
            vehicles.append(VehicleItem(
                id=f"{slug}_v{i+1}",
                name=f"{brand_name} {model_suffix}",
                tagline=f"Experience {brand_name} {tag}",
                category=cat,
                price_range=price,
                hero_image=img,
                engine_specs=engine,
                seating_capacity="5-Seater",
                fuel_or_battery=fuel,
                range_or_mileage=eff,
                key_highlights=[
                    "Next-Generation Panoramic Cockpit Display",
                    "Advanced Driver Assistance System (ADAS Level 2+)",
                    "Active Adaptive Suspension with Dynamic Dampers",
                    "Acoustic Glass with Immersive Spatial Audio"
                ],
                usp=f"Precision engineering, refined luxury, and class-leading dynamics from {brand_name}.",
                variants=[
                    VehicleVariant(
                        name="Dynamic Edition",
                        price_ex_showroom=price.split(" - ")[0],
                        engine_or_battery=engine,
                        transmission="Automatic",
                        key_features=["Digital Instrument Cluster", "Smart Keyless Entry", "Dynamic Stability Control"]
                    ),
                    VehicleVariant(
                        name="Performance Luxury",
                        price_ex_showroom=price.split(" - ")[-1],
                        engine_or_battery=engine,
                        transmission="Automatic Sport",
                        key_features=["Panoramic Glass Roof", "Ventilated Leather Seats", "Adaptive Air Suspension"]
                    )
                ],
                is_custom_source_of_truth=False
            ))
        return vehicles

    @classmethod
    def _build_domain_fallback_catalog(
        cls,
        brand_name: str,
        urls: List[str],
        candidate_images: List[str],
        detected_logo: str
    ) -> BrandCatalog:
        clean_key = brand_name.lower().strip()
        slug = re.sub(r'[^a-z0-9]+', '_', clean_key).strip('_')
        
        for k, profile in KNOWN_BRAND_PROFILES.items():
            if k in clean_key:
                vehicles = cls._build_domain_fallback_vehicles(brand_name, candidate_images)
                return BrandCatalog(
                    id=slug,
                    name=profile["name"],
                    tagline=profile["tagline"],
                    logo_url=detected_logo or profile.get("logo_url", ""),
                    primary_color=profile.get("primary_color", "#0066b1"),
                    secondary_color=profile.get("secondary_color", "#0f172a"),
                    accent_color=profile.get("accent_color", "#38bdf8"),
                    avatar_name=profile.get("avatar_name", "Kavya"),
                    avatar_voice=profile.get("avatar_voice", "Aoede"),
                    source_urls=urls,
                    is_active=True,
                    vehicles=vehicles,
                    dealerships=[
                        DealershipItem(
                            id=f"{slug}_flagship",
                            name=f"{profile['name']} Flagship Center",
                            address="Auto Boulevard, Downtown District",
                            city="Mumbai",
                            phone="+91 22 4000 8800",
                            rating=4.9,
                            available_advisors=["Senior Brand Consultant", "Product Genius"],
                            has_test_drive_home_pickup=True
                        )
                    ]
                )

        vehicles = cls._build_domain_fallback_vehicles(brand_name, candidate_images)
        primary_color = "#0ea5e9"
        logo = detected_logo
        if not logo or not logo.strip():
            logo = cls._generate_brand_vector_logo(slug, brand_name, primary_color)

        return BrandCatalog(
            id=slug,
            name=brand_name,
            tagline=f"Official {brand_name} Experience Center",
            logo_url=logo,
            primary_color=primary_color,
            secondary_color="#0f172a",
            accent_color="#38bdf8",
            avatar_name="Kavya",
            avatar_voice="Aoede",
            source_urls=urls,
            is_active=True,
            vehicles=vehicles,
            dealerships=[
                DealershipItem(
                    id=f"{slug}_dealership",
                    name=f"{brand_name} Flagship Center",
                    address="Downtown Auto District",
                    city="Mumbai",
                    phone="+91 22 4000 8800",
                    rating=4.9,
                    available_advisors=["Senior Consultant", "Product Genius"],
                    has_test_drive_home_pickup=True
                )
            ]
        )
