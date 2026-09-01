import asyncio
import logging
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models.dealership import Dealership
from app.models.booking import PublicHoliday, SlotConfig

logger = logging.getLogger("seed_dealerships")

PUBLIC_HOLIDAYS_DATA = [
    {"date": "2026-01-26", "name": "Republic Day", "state": "ALL"},
    {"date": "2026-03-03", "name": "Holi (Festival of Colours)", "state": "ALL"},
    {"date": "2026-03-20", "name": "Eid-ul-Fitr", "state": "ALL"},
    {"date": "2026-04-14", "name": "Dr. Ambedkar Jayanti", "state": "ALL"},
    {"date": "2026-05-01", "name": "Maharashtra Day / May Day", "state": "Maharashtra"},
    {"date": "2026-08-15", "name": "Independence Day", "state": "ALL"},
    {"date": "2026-09-04", "name": "Janmashtami", "state": "ALL"},
    {"date": "2026-10-02", "name": "Mahatma Gandhi Jayanti", "state": "ALL"},
    {"date": "2026-10-20", "name": "Dussehra (Vijayadashami)", "state": "ALL"},
    {"date": "2026-11-08", "name": "Diwali (Deepavali)", "state": "ALL"},
    {"date": "2026-11-09", "name": "Govardhan Puja", "state": "ALL"},
    {"date": "2026-11-24", "name": "Guru Nanak Jayanti", "state": "ALL"},
    {"date": "2026-12-25", "name": "Christmas Day", "state": "ALL"}
]

SLOT_CONFIGS_DATA = [
    {"slot_time": "09:00 AM", "order": 1},
    {"slot_time": "10:00 AM", "order": 2},
    {"slot_time": "11:00 AM", "order": 3},
    {"slot_time": "12:00 PM", "order": 4},
    {"slot_time": "01:00 PM", "order": 5},
    {"slot_time": "02:00 PM", "order": 6},
    {"slot_time": "03:00 PM", "order": 7},
    {"slot_time": "04:00 PM", "order": 8},
    {"slot_time": "05:00 PM", "order": 9}
]

DEALERSHIPS_DATA = [
    # MUMBAI
    {
        "id": "mumbai_nbs_chowpatty",
        "name": "Mahindra NBS International Ltd - Chowpatty",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Chowpatty Sea Face",
        "address": "Fulchand Niwas, Ground Floor, Chowpatty Sea Face, Marine Drive, Mumbai",
        "pin_code": "400007",
        "phone": "+91 22 2363 4500",
        "email": "chowpatty@nbsmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+NBS+Chowpatty+Mumbai",
        "rating": 4.9,
        "available_advisors": ["Rajesh Varma (Senior SUV Specialist)", "Pooja Hegde (EV Consultant)", "Aarav Mehta"]
    },
    {
        "id": "mumbai_modi_worli",
        "name": "Mahindra Modi Arnav Automobiles - Worli",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Worli",
        "address": "Ground Floor, Dr. Annie Besant Road, Near Nehru Centre, Worli, Mumbai",
        "pin_code": "400018",
        "phone": "+91 22 6610 8800",
        "email": "worli@modiauto.in",
        "map_url": "https://maps.google.com/?q=Mahindra+Modi+Worli+Mumbai",
        "rating": 4.8,
        "available_advisors": ["Vikram Sethi (Off-Road Lead)", "Ananya Roy (Born EV Specialist)"]
    },
    {
        "id": "mumbai_bayview_bandra",
        "name": "Mahindra Bayview Motors - Bandra West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Bandra West",
        "address": "Plot 42, Linking Road, Near Bandra Station & Sea Link Entry, Bandra West, Mumbai",
        "pin_code": "400050",
        "phone": "+91 22 2640 1200",
        "email": "bandra@bayviewmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Bandra+West+Mumbai",
        "rating": 4.9,
        "available_advisors": ["Rajesh Varma", "Siddharth Deshmukh", "Meera Sen"]
    },
    {
        "id": "mumbai_nbs_andheri_west",
        "name": "Mahindra NBS International Ltd - Andheri West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Andheri West",
        "address": "Showroom 4, New Link Road, Opposite Infinity Mall, Andheri West, Mumbai",
        "pin_code": "400053",
        "phone": "+91 22 4099 7700",
        "email": "andheri.west@nbsmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+NBS+Andheri+West",
        "rating": 4.8,
        "available_advisors": ["Karan Singhania", "Riya Sen"]
    },
    {
        "id": "mumbai_randhawa_andheri_east",
        "name": "Mahindra Randhawa Motors - Andheri East",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Andheri East",
        "address": "Randhawa House, Sir M V Road, Near Western Express Highway Metro, Andheri East, Mumbai",
        "pin_code": "400069",
        "phone": "+91 22 6788 9900",
        "email": "andheri.east@randhawamotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Randhawa+Andheri+East",
        "rating": 4.7,
        "available_advisors": ["Gurpreet Randhawa", "Amit Sawant"]
    },
    {
        "id": "mumbai_salasar_thane",
        "name": "Mahindra Salasar Autocrafts - Thane West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Thane West",
        "address": "Ghodbunder Road, Near Viviana Mall, Kapurbawdi Junction, Thane West, Mumbai MMR",
        "pin_code": "400607",
        "phone": "+91 22 2545 3300",
        "email": "thane@salasarauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Salasar+Thane",
        "rating": 4.8,
        "available_advisors": ["Sameer Kulkarni", "Neha Patil"]
    },
    {
        "id": "mumbai_nbs_kandivali",
        "name": "Mahindra NBS International Ltd - Kandivali West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Kandivali West",
        "address": "SV Road, Near Poisar Depot, Kandivali West, Mumbai",
        "pin_code": "400067",
        "phone": "+91 22 2801 5500",
        "email": "kandivali@nbsmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+NBS+Kandivali",
        "rating": 4.7,
        "available_advisors": ["Manish Joshi", "Kavita Shah"]
    },
    {
        "id": "mumbai_g3_vashi",
        "name": "Mahindra G3 Motors - Navi Mumbai",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Vashi",
        "address": "Sector 19D, Palm Beach Road, Near Vashi Flyover, Navi Mumbai",
        "pin_code": "400705",
        "phone": "+91 22 2789 4400",
        "email": "vashi@g3motors.in",
        "map_url": "https://maps.google.com/?q=Mahindra+G3+Motors+Vashi",
        "rating": 4.8,
        "available_advisors": ["Nikhil Gade", "Priyanka More"]
    },

    # PUNE
    {
        "id": "pune_silver_jubilee_camp",
        "name": "Mahindra Silver Jubilee Motors - Camp",
        "city": "Pune",
        "state": "Maharashtra",
        "area": "Camp",
        "address": "12, Moledina Road, Near Pune Railway Station, Camp, Pune",
        "pin_code": "411001",
        "phone": "+91 20 2613 3300",
        "email": "camp@silverjubileemotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Silver+Jubilee+Camp+Pune",
        "rating": 4.9,
        "available_advisors": ["Sunil Jadhav (4x4 Specialist)", "Tanvi Kulkarni (Born EV Advisor)"]
    },
    {
        "id": "pune_sahyadri_baner",
        "name": "Mahindra Sahyadri Motors - Baner",
        "city": "Pune",
        "state": "Maharashtra",
        "area": "Baner",
        "address": "Survey No 84, Baner Road, Near High Street & Balewadi Stadium, Baner, Pune",
        "pin_code": "411045",
        "phone": "+91 20 6790 1100",
        "email": "baner@sahyadrimotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Sahyadri+Baner+Pune",
        "rating": 4.9,
        "available_advisors": ["Rohan Shinde", "Aishwarya Deshpande"]
    },
    {
        "id": "pune_kundan_wakad",
        "name": "Mahindra Kundan Cars - Wakad & Pimpri",
        "city": "Pune",
        "state": "Maharashtra",
        "area": "Wakad / Pimpri",
        "address": "Old Pune-Mumbai Highway, Near Wakad Flyover, Pimpri-Chinchwad, Pune",
        "pin_code": "411018",
        "phone": "+91 20 6633 4400",
        "email": "wakad@kundancars.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Kundan+Wakad+Pune",
        "rating": 4.8,
        "available_advisors": ["Mahesh Patil", "Pooja Gaikwad"]
    },
    {
        "id": "pune_unnati_viman_nagar",
        "name": "Mahindra Unnati Motors - Viman Nagar",
        "city": "Pune",
        "state": "Maharashtra",
        "area": "Viman Nagar / Nagar Road",
        "address": "Nagar Road, Near Phoenix Marketcity Mall, Viman Nagar, Pune",
        "pin_code": "411014",
        "phone": "+91 20 4140 2200",
        "email": "vimannagar@unnatimotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Unnati+Viman+Nagar+Pune",
        "rating": 4.8,
        "available_advisors": ["Aditya Chavan", "Shreya Joshi"]
    },
    {
        "id": "pune_silver_jubilee_hadapsar",
        "name": "Mahindra Silver Jubilee Motors - Hadapsar",
        "city": "Pune",
        "state": "Maharashtra",
        "area": "Hadapsar",
        "address": "Pune-Solapur Road, Near Magarpatta City & Cybercity, Hadapsar, Pune",
        "pin_code": "411013",
        "phone": "+91 20 2687 1100",
        "email": "hadapsar@silverjubileemotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Hadapsar+Pune",
        "rating": 4.7,
        "available_advisors": ["Prashant Salunke", "Deepali More"]
    },
    {
        "id": "pune_bu_bhandari_kothrud",
        "name": "Mahindra B.U. Bhandari Auto - Kothrud",
        "city": "Pune",
        "state": "Maharashtra",
        "area": "Kothrud",
        "address": "Paud Road, Near Vanaz Metro Station, Kothrud, Pune",
        "pin_code": "411038",
        "phone": "+91 20 2544 8800",
        "email": "kothrud@bubhandari.com",
        "map_url": "https://maps.google.com/?q=Mahindra+BU+Bhandari+Kothrud+Pune",
        "rating": 4.8,
        "available_advisors": ["Ganesh Gokhale", "Smita Joshi"]
    },

    # DELHI / NCR
    {
        "id": "delhi_koncept_mathura_rd",
        "name": "Mahindra Koncept Automobiles - Mathura Road",
        "city": "Delhi",
        "state": "Delhi",
        "area": "Mohan Cooperative",
        "address": "A-Block, Mohan Cooperative Industrial Estate, Mathura Road, New Delhi",
        "pin_code": "110044",
        "phone": "+91 11 4188 5500",
        "email": "mathuraroad@konceptmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Koncept+Mathura+Road+Delhi",
        "rating": 4.9,
        "available_advisors": ["Harish Rawat (Senior Advisor)", "Divya Sharma (EV Lead)"]
    },
    {
        "id": "delhi_indraprastha_rama_rd",
        "name": "Mahindra Indraprastha Automobiles - Rama Road",
        "city": "Delhi",
        "state": "Delhi",
        "area": "Moti Nagar / Rama Road",
        "address": "B-12, Rama Road Industrial Area, Near Moti Nagar Metro Station, New Delhi",
        "pin_code": "110015",
        "phone": "+91 11 4545 7700",
        "email": "ramard@indraprasthaauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Indraprastha+Rama+Road+Delhi",
        "rating": 4.8,
        "available_advisors": ["Karan Bhasin", "Simran Kaur"]
    },
    {
        "id": "delhi_koncept_green_park",
        "name": "Mahindra Koncept Automobiles - South Delhi",
        "city": "Delhi",
        "state": "Delhi",
        "area": "Green Park",
        "address": "G-4, Green Park Main Market, Near Aurobindo Marg, New Delhi",
        "pin_code": "110016",
        "phone": "+91 11 2686 4400",
        "email": "greenpark@konceptmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Koncept+Green+Park+Delhi",
        "rating": 4.9,
        "available_advisors": ["Varun Malhotra", "Anjali Malik"]
    },
    {
        "id": "delhi_shiva_patparganj",
        "name": "Mahindra Shiva Automobiles - East Delhi",
        "city": "Delhi",
        "state": "Delhi",
        "area": "Patparganj",
        "address": "Plot 28, Patparganj Industrial Area, Near Anand Vihar, East Delhi",
        "pin_code": "110092",
        "phone": "+91 11 4300 2200",
        "email": "patparganj@shivaauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Shiva+Patparganj+Delhi",
        "rating": 4.7,
        "available_advisors": ["Manish Tyagi", "Rachna Gupta"]
    },
    {
        "id": "delhi_koncept_gurugram",
        "name": "Mahindra Koncept Automobiles - Gurugram",
        "city": "Delhi",
        "state": "Delhi",
        "area": "Sector 18 Gurugram",
        "address": "Old Delhi-Gurgaon Road, Near Maruti Plant, Sector 18, Gurugram, NCR",
        "pin_code": "122015",
        "phone": "+91 124 456 7800",
        "email": "gurugram@konceptmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Koncept+Gurugram",
        "rating": 4.9,
        "available_advisors": ["Ashok Yadav", "Pooja Ahluwalia"]
    },
    {
        "id": "delhi_dynamic_noida",
        "name": "Mahindra Dynamic Motors - Noida",
        "city": "Delhi",
        "state": "Delhi",
        "area": "Sector 63 Noida",
        "address": "D-Block, Sector 63, Near Electronic City Metro, Noida, NCR",
        "pin_code": "201301",
        "phone": "+91 120 488 9900",
        "email": "noida@dynamicmahindra.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Dynamic+Motors+Noida",
        "rating": 4.8,
        "available_advisors": ["Rahul Chauhan", "Swati Saxena"]
    },

    # BANGALORE
    {
        "id": "bangalore_sireesh_hosur_rd",
        "name": "Mahindra Sireesh Auto - Hosur Road",
        "city": "Bangalore",
        "state": "Karnataka",
        "area": "Madiwala / Koramangala",
        "address": "No. 120/1, Hosur Main Road, Near Silk Board Junction, Madiwala, Bengaluru",
        "pin_code": "560068",
        "phone": "+91 80 4032 5500",
        "email": "hosur@sireeshauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Sireesh+Auto+Hosur+Road+Bangalore",
        "rating": 4.9,
        "available_advisors": ["Suresh Gowda (SUV Lead)", "Deepa Murthy (EV Specialist)"]
    },
    {
        "id": "bangalore_anant_bannerghatta",
        "name": "Mahindra Anant Cars - Bannerghatta Road",
        "city": "Bangalore",
        "state": "Karnataka",
        "area": "JP Nagar / Bannerghatta",
        "address": "No. 44, Bannerghatta Main Road, Opposite IIM-B, JP Nagar, Bengaluru",
        "pin_code": "560076",
        "phone": "+91 80 4344 7700",
        "email": "bannerghatta@anantcars.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Anant+Cars+Bannerghatta+Bangalore",
        "rating": 4.8,
        "available_advisors": ["Karthik Reddy", "Pavithra Rao"]
    },
    {
        "id": "bangalore_sireesh_marathahalli",
        "name": "Mahindra Sireesh Auto - Marathahalli",
        "city": "Bangalore",
        "state": "Karnataka",
        "area": "Marathahalli / Outer Ring Road",
        "address": "Outer Ring Road, Near Marathahalli Bridge & Prestige Tech Park, Bengaluru",
        "pin_code": "560037",
        "phone": "+91 80 6766 8800",
        "email": "marathahalli@sireeshauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Sireesh+Marathahalli+Bangalore",
        "rating": 4.8,
        "available_advisors": ["Vinod Hegde", "Lavanya Nair"]
    },
    {
        "id": "bangalore_india_garage_vasanth",
        "name": "Mahindra India Garage - Central Bengaluru",
        "city": "Bangalore",
        "state": "Karnataka",
        "area": "Vasanth Nagar / Palace Road",
        "address": "No. 1, Palace Cross Road, Near Mount Carmel College, Vasanth Nagar, Bengaluru",
        "pin_code": "560020",
        "phone": "+91 80 2235 6600",
        "email": "palace@indiagarage.com",
        "map_url": "https://maps.google.com/?q=Mahindra+India+Garage+Palace+Road+Bangalore",
        "rating": 4.9,
        "available_advisors": ["Vijay Raghavan", "Ananya Bhat"]
    },
    {
        "id": "bangalore_anant_mysore_rd",
        "name": "Mahindra Anant Cars - Mysore Road",
        "city": "Bangalore",
        "state": "Karnataka",
        "area": "Nayandahalli",
        "address": "No. 88, Mysore Main Road, Near Nayandahalli Metro Station, Bengaluru",
        "pin_code": "560039",
        "phone": "+91 80 2860 3300",
        "email": "mysoreroad@anantcars.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Anant+Cars+Mysore+Road+Bangalore",
        "rating": 4.7,
        "available_advisors": ["Chetan Kumar", "Meghana Raj"]
    },
    {
        "id": "bangalore_sireesh_yelahanka",
        "name": "Mahindra Sireesh Auto - North Bengaluru",
        "city": "Bangalore",
        "state": "Karnataka",
        "area": "Yelahanka / Hebbal",
        "address": "Bellary Main Road, Near Esteem Mall & Yelahanka Bypass, Bengaluru",
        "pin_code": "560064",
        "phone": "+91 80 4911 2200",
        "email": "yelahanka@sireeshauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Sireesh+Yelahanka+Bangalore",
        "rating": 4.8,
        "available_advisors": ["Pradeep Nayak", "Bhavana Swamy"]
    },

    # CHENNAI
    {
        "id": "chennai_mpl_anna_salai",
        "name": "Mahindra MPL Automobiles - Mount Road",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "area": "Nandanam / Anna Salai",
        "address": "No. 498, Anna Salai (Mount Road), Near Nandanam Signal, Chennai",
        "pin_code": "600035",
        "phone": "+91 44 2434 5500",
        "email": "mountroad@mplauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+MPL+Anna+Salai+Chennai",
        "rating": 4.9,
        "available_advisors": ["Ravi Chandran (Chief SUV Consultant)", "Lakshmi Narayanan (EV Specialist)"]
    },
    {
        "id": "chennai_zulaikha_ambattur",
        "name": "Mahindra Zulaikha Motors - Ambattur",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "area": "Ambattur Industrial Estate",
        "address": "Plot 58, South Phase, Ambattur Industrial Estate, Chennai",
        "pin_code": "600058",
        "phone": "+91 44 4390 1100",
        "email": "ambattur@zulaikhamotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Zulaikha+Ambattur+Chennai",
        "rating": 4.8,
        "available_advisors": ["Senthil Nathan", "Divya Krishnan"]
    },
    {
        "id": "chennai_vst_kilpauk",
        "name": "Mahindra VST Motors - Central Chennai",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "area": "Kilpauk / Poonamallee",
        "address": "No. 144, Poonamallee High Road, Near Kilpauk Medical College, Chennai",
        "pin_code": "600010",
        "phone": "+91 44 2836 7700",
        "email": "kilpauk@vstmotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+VST+Kilpauk+Chennai",
        "rating": 4.8,
        "available_advisors": ["Karthik Sundaram", "Sneha Ram"]
    },
    {
        "id": "chennai_mpl_omr",
        "name": "Mahindra MPL Automobiles - OMR IT Corridor",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "area": "Perungudi / OMR",
        "address": "Rajiv Gandhi Salai (OMR), Near Perungudi Toll Plaza & RMZ Millenia, Chennai",
        "pin_code": "600096",
        "phone": "+91 44 6655 4400",
        "email": "omr@mplauto.com",
        "map_url": "https://maps.google.com/?q=Mahindra+MPL+OMR+Chennai",
        "rating": 4.9,
        "available_advisors": ["Venkatesh Babu", "Archana Murugan"]
    },
    {
        "id": "chennai_zulaikha_chromepet",
        "name": "Mahindra Zulaikha Motors - South Chennai",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "area": "Chromepet / GST Road",
        "address": "No. 22, Grand Southern Trunk (GST) Road, Near Chromepet Railway Station, Chennai",
        "pin_code": "600044",
        "phone": "+91 44 2241 8800",
        "email": "chromepet@zulaikhamotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+Zulaikha+Chromepet+Chennai",
        "rating": 4.7,
        "available_advisors": ["Balaji Raman", "Swetha Natarajan"]
    },
    {
        "id": "chennai_vst_velachery",
        "name": "Mahindra VST Motors - Velachery",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "area": "Velachery",
        "address": "No. 76, Velachery Main Road, Near Phoenix Marketcity, Chennai",
        "pin_code": "600042",
        "phone": "+91 44 4299 3300",
        "email": "velachery@vstmotors.com",
        "map_url": "https://maps.google.com/?q=Mahindra+VST+Velachery+Chennai",
        "rating": 4.8,
        "available_advisors": ["Dinesh Kumar", "Keerthana Selvam"]
    }
]

async def seed_dealerships():
    async with AsyncSessionLocal() as db:
        # 1. Seed Public Holidays
        h_res = await db.execute(select(PublicHoliday))
        existing_holidays = {h.holiday_date: h for h in h_res.scalars().all()}
        for h in PUBLIC_HOLIDAYS_DATA:
            if h["date"] not in existing_holidays:
                holiday = PublicHoliday(
                    holiday_date=h["date"],
                    holiday_name=h["name"],
                    state=h.get("state", "ALL"),
                    is_active=1
                )
                db.add(holiday)

        # 2. Seed Slot Configs
        s_res = await db.execute(select(SlotConfig))
        existing_slots = {s.slot_time: s for s in s_res.scalars().all()}
        for s in SLOT_CONFIGS_DATA:
            if s["slot_time"] not in existing_slots:
                cfg = SlotConfig(
                    slot_time=s["slot_time"],
                    display_order=s["order"],
                    is_active=1
                )
                db.add(cfg)

        # 3. Seed Dealerships
        d_res = await db.execute(select(Dealership))
        existing_dealerships = {d.id: d for d in d_res.scalars().all()}
        
        for item in DEALERSHIPS_DATA:
            if item["id"] not in existing_dealerships:
                d = Dealership(
                    id=item["id"],
                    name=item["name"],
                    city=item["city"],
                    state=item["state"],
                    area=item["area"],
                    address=item["address"],
                    pin_code=item["pin_code"],
                    phone=item["phone"],
                    email=item["email"],
                    map_url=item["map_url"],
                    rating=item["rating"],
                    available_advisors=item["available_advisors"],
                    is_active=True
                )
                db.add(d)
            else:
                d = existing_dealerships[item["id"]]
                d.name = item["name"]
                d.city = item["city"]
                d.state = item["state"]
                d.area = item["area"]
                d.address = item["address"]
                d.pin_code = item["pin_code"]
                d.phone = item["phone"]
                d.email = item["email"]
                d.map_url = item["map_url"]
                d.rating = item["rating"]
                d.available_advisors = item["available_advisors"]

        await db.commit()
        logger.info("Dealership, Holiday and Slot Config Database Seed Complete.")

if __name__ == "__main__":
    asyncio.run(seed_dealerships())
