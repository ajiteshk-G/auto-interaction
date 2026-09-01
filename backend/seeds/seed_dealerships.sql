-- ==============================================================================
-- Mahindra Official Dealerships, Public Holidays & Operational Timings Database Seed
-- Source: https://dealers-auto.mahindra.com/location/maharashtra & official Mahindra networks
-- ==============================================================================

-- 1. Dealerships Table
CREATE TABLE IF NOT EXISTS dealerships (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    city VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL,
    area VARCHAR(128),
    address TEXT NOT NULL,
    pin_code VARCHAR(16) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    email VARCHAR(128),
    map_url VARCHAR(256),
    rating FLOAT DEFAULT 4.8,
    available_advisors JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Public Holidays Table (Stored in Database)
CREATE TABLE IF NOT EXISTS public_holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holiday_date VARCHAR(16) UNIQUE NOT NULL,
    holiday_name VARCHAR(128) NOT NULL,
    state VARCHAR(64) DEFAULT 'ALL',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Slot Configurations Table (9:00 AM - 6:00 PM Stored in Database)
CREATE TABLE IF NOT EXISTS slot_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_time VARCHAR(32) UNIQUE NOT NULL,
    display_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Test Drive Slots (Reserved Slots in Database)
CREATE TABLE IF NOT EXISTS test_drive_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_date VARCHAR(32) NOT NULL,
    slot_time VARCHAR(32) NOT NULL,
    dealership_id VARCHAR(64) DEFAULT 'mumbai_bayview_bandra',
    vehicle_id VARCHAR(64),
    status VARCHAR(32) DEFAULT 'AVAILABLE',
    customer_id INTEGER,
    customer_name VARCHAR(128),
    customer_phone VARCHAR(32),
    booking_reference VARCHAR(64),
    booking_type VARCHAR(32) DEFAULT 'HOME_DOORSTEP',
    delivery_address TEXT,
    pin_code VARCHAR(16),
    notes TEXT,
    reserved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SEED PUBLIC HOLIDAYS (2026 Indian Gazetted Holidays)
INSERT OR REPLACE INTO public_holidays (holiday_date, holiday_name, state, is_active)
VALUES
('2026-01-26', 'Republic Day', 'ALL', 1),
('2026-03-03', 'Holi (Festival of Colours)', 'ALL', 1),
('2026-03-20', 'Eid-ul-Fitr', 'ALL', 1),
('2026-04-14', 'Dr. Ambedkar Jayanti', 'ALL', 1),
('2026-05-01', 'Maharashtra Day / May Day', 'Maharashtra', 1),
('2026-08-15', 'Independence Day', 'ALL', 1),
('2026-09-04', 'Janmashtami', 'ALL', 1),
('2026-10-02', 'Mahatma Gandhi Jayanti', 'ALL', 1),
('2026-10-20', 'Dussehra (Vijayadashami)', 'ALL', 1),
('2026-11-08', 'Diwali (Deepavali)', 'ALL', 1),
('2026-11-09', 'Govardhan Puja', 'ALL', 1),
('2026-11-24', 'Guru Nanak Jayanti', 'ALL', 1),
('2026-12-25', 'Christmas Day', 'ALL', 1);

-- SEED OPERATIONAL TIME SLOTS (Strictly 9:00 AM - 6:00 PM)
INSERT OR REPLACE INTO slot_configs (slot_time, display_order, is_active)
VALUES
('09:00 AM', 1, 1),
('10:00 AM', 2, 1),
('11:00 AM', 3, 1),
('12:00 PM', 4, 1),
('01:00 PM', 5, 1),
('02:00 PM', 6, 1),
('03:00 PM', 7, 1),
('04:00 PM', 8, 1),
('05:00 PM', 9, 1);

-- SEED DEALERSHIPS: MUMBAI
INSERT OR REPLACE INTO dealerships (id, name, city, state, area, address, pin_code, phone, email, map_url, rating, available_advisors, is_active)
VALUES 
('mumbai_nbs_chowpatty', 'Mahindra NBS International Ltd - Chowpatty', 'Mumbai', 'Maharashtra', 'Chowpatty Sea Face', 'Fulchand Niwas, Ground Floor, Chowpatty Sea Face, Marine Drive, Mumbai', '400007', '+91 22 2363 4500', 'chowpatty@nbsmahindra.com', 'https://maps.google.com/?q=Mahindra+NBS+Chowpatty+Mumbai', 4.9, '["Rajesh Varma (Senior SUV Specialist)", "Pooja Hegde (EV Consultant)", "Aarav Mehta"]', 1),
('mumbai_modi_worli', 'Mahindra Modi Arnav Automobiles - Worli', 'Mumbai', 'Maharashtra', 'Worli', 'Ground Floor, Dr. Annie Besant Road, Near Nehru Centre, Worli, Mumbai', '400018', '+91 22 6610 8800', 'worli@modiauto.in', 'https://maps.google.com/?q=Mahindra+Modi+Worli+Mumbai', 4.8, '["Vikram Sethi (Off-Road Lead)", "Ananya Roy (Born EV Specialist)"]', 1),
('mumbai_bayview_bandra', 'Mahindra Bayview Motors - Bandra West', 'Mumbai', 'Maharashtra', 'Bandra West', 'Plot 42, Linking Road, Near Bandra Station & Sea Link Entry, Bandra West, Mumbai', '400050', '+91 22 2640 1200', 'bandra@bayviewmahindra.com', 'https://maps.google.com/?q=Mahindra+Bandra+West+Mumbai', 4.9, '["Rajesh Varma", "Siddharth Deshmukh", "Meera Sen"]', 1),
('mumbai_nbs_andheri_west', 'Mahindra NBS International Ltd - Andheri West', 'Mumbai', 'Maharashtra', 'Andheri West', 'Showroom 4, New Link Road, Opposite Infinity Mall, Andheri West, Mumbai', '400053', '+91 22 4099 7700', 'andheri.west@nbsmahindra.com', 'https://maps.google.com/?q=Mahindra+NBS+Andheri+West', 4.8, '["Karan Singhania", "Riya Sen"]', 1),
('mumbai_randhawa_andheri_east', 'Mahindra Randhawa Motors - Andheri East', 'Mumbai', 'Maharashtra', 'Andheri East', 'Randhawa House, Sir M V Road, Near Western Express Highway Metro, Andheri East, Mumbai', '400069', '+91 22 6788 9900', 'andheri.east@randhawamotors.com', 'https://maps.google.com/?q=Mahindra+Randhawa+Andheri+East', 4.7, '["Gurpreet Randhawa", "Amit Sawant"]', 1),
('mumbai_salasar_thane', 'Mahindra Salasar Autocrafts - Thane West', 'Mumbai', 'Maharashtra', 'Thane West', 'Ghodbunder Road, Near Viviana Mall, Kapurbawdi Junction, Thane West, Mumbai MMR', '400607', '+91 22 2545 3300', 'thane@salasarauto.com', 'https://maps.google.com/?q=Mahindra+Salasar+Thane', 4.8, '["Sameer Kulkarni", "Neha Patil"]', 1),
('mumbai_nbs_kandivali', 'Mahindra NBS International Ltd - Kandivali West', 'Mumbai', 'Maharashtra', 'Kandivali West', 'SV Road, Near Poisar Depot, Kandivali West, Mumbai', '400067', '+91 22 2801 5500', 'kandivali@nbsmahindra.com', 'https://maps.google.com/?q=Mahindra+NBS+Kandivali', 4.7, '["Manish Joshi", "Kavita Shah"]', 1),
('mumbai_g3_vashi', 'Mahindra G3 Motors - Navi Mumbai', 'Mumbai', 'Maharashtra', 'Vashi', 'Sector 19D, Palm Beach Road, Near Vashi Flyover, Navi Mumbai', '400705', '+91 22 2789 4400', 'vashi@g3motors.in', 'https://maps.google.com/?q=Mahindra+G3+Motors+Vashi', 4.8, '["Nikhil Gade", "Priyanka More"]', 1);

-- SEED DEALERSHIPS: PUNE
INSERT OR REPLACE INTO dealerships (id, name, city, state, area, address, pin_code, phone, email, map_url, rating, available_advisors, is_active)
VALUES
('pune_silver_jubilee_camp', 'Mahindra Silver Jubilee Motors - Camp', 'Pune', 'Maharashtra', 'Camp', '12, Moledina Road, Near Pune Railway Station, Camp, Pune', '411001', '+91 20 2613 3300', 'camp@silverjubileemotors.com', 'https://maps.google.com/?q=Mahindra+Silver+Jubilee+Camp+Pune', 4.9, '["Sunil Jadhav (4x4 Specialist)", "Tanvi Kulkarni (Born EV Advisor)"]', 1),
('pune_sahyadri_baner', 'Mahindra Sahyadri Motors - Baner', 'Pune', 'Maharashtra', 'Baner', 'Survey No 84, Baner Road, Near High Street & Balewadi Stadium, Baner, Pune', '411045', '+91 20 6790 1100', 'baner@sahyadrimotors.com', 'https://maps.google.com/?q=Mahindra+Sahyadri+Baner+Pune', 4.9, '["Rohan Shinde", "Aishwarya Deshpande"]', 1),
('pune_kundan_wakad', 'Mahindra Kundan Cars - Wakad & Pimpri', 'Pune', 'Maharashtra', 'Wakad / Pimpri', 'Old Pune-Mumbai Highway, Near Wakad Flyover, Pimpri-Chinchwad, Pune', '411018', '+91 20 6633 4400', 'wakad@kundancars.com', 'https://maps.google.com/?q=Mahindra+Kundan+Wakad+Pune', 4.8, '["Mahesh Patil", "Pooja Gaikwad"]', 1),
('pune_unnati_viman_nagar', 'Mahindra Unnati Motors - Viman Nagar', 'Pune', 'Maharashtra', 'Viman Nagar / Nagar Road', 'Nagar Road, Near Phoenix Marketcity Mall, Viman Nagar, Pune', '411014', '+91 20 4140 2200', 'vimannagar@unnatimotors.com', 'https://maps.google.com/?q=Mahindra+Unnati+Viman+Nagar+Pune', 4.8, '["Aditya Chavan", "Shreya Joshi"]', 1),
('pune_silver_jubilee_hadapsar', 'Mahindra Silver Jubilee Motors - Hadapsar', 'Pune', 'Maharashtra', 'Hadapsar', 'Pune-Solapur Road, Near Magarpatta City & Cybercity, Hadapsar, Pune', '411013', '+91 20 2687 1100', 'hadapsar@silverjubileemotors.com', 'https://maps.google.com/?q=Mahindra+Hadapsar+Pune', 4.7, '["Prashant Salunke", "Deepali More"]', 1),
('pune_bu_bhandari_kothrud', 'Mahindra B.U. Bhandari Auto - Kothrud', 'Pune', 'Maharashtra', 'Kothrud', 'Paud Road, Near Vanaz Metro Station, Kothrud, Pune', '411038', '+91 20 2544 8800', 'kothrud@bubhandari.com', 'https://maps.google.com/?q=Mahindra+BU+Bhandari+Kothrud+Pune', 4.8, '["Ganesh Gokhale", "Smita Joshi"]', 1);

-- SEED DEALERSHIPS: DELHI / NCR
INSERT OR REPLACE INTO dealerships (id, name, city, state, area, address, pin_code, phone, email, map_url, rating, available_advisors, is_active)
VALUES
('delhi_koncept_mathura_rd', 'Mahindra Koncept Automobiles - Mathura Road', 'Delhi', 'Delhi', 'Mohan Cooperative', 'A-Block, Mohan Cooperative Industrial Estate, Mathura Road, New Delhi', '110044', '+91 11 4188 5500', 'mathuraroad@konceptmahindra.com', 'https://maps.google.com/?q=Mahindra+Koncept+Mathura+Road+Delhi', 4.9, '["Harish Rawat (Senior Advisor)", "Divya Sharma (EV Lead)"]', 1),
('delhi_indraprastha_rama_rd', 'Mahindra Indraprastha Automobiles - Rama Road', 'Delhi', 'Delhi', 'Moti Nagar / Rama Road', 'B-12, Rama Road Industrial Area, Near Moti Nagar Metro Station, New Delhi', '110015', '+91 11 4545 7700', 'ramard@indraprasthaauto.com', 'https://maps.google.com/?q=Mahindra+Indraprastha+Rama+Road+Delhi', 4.8, '["Karan Bhasin", "Simran Kaur"]', 1),
('delhi_koncept_green_park', 'Mahindra Koncept Automobiles - South Delhi', 'Delhi', 'Delhi', 'Green Park', 'G-4, Green Park Main Market, Near Aurobindo Marg, New Delhi', '110016', '+91 11 2686 4400', 'greenpark@konceptmahindra.com', 'https://maps.google.com/?q=Mahindra+Koncept+Green+Park+Delhi', 4.9, '["Varun Malhotra", "Anjali Malik"]', 1),
('delhi_shiva_patparganj', 'Mahindra Shiva Automobiles - East Delhi', 'Delhi', 'Delhi', 'Patparganj', 'Plot 28, Patparganj Industrial Area, Near Anand Vihar, East Delhi', '110092', '+91 11 4300 2200', 'patparganj@shivaauto.com', 'https://maps.google.com/?q=Mahindra+Shiva+Patparganj+Delhi', 4.7, '["Manish Tyagi", "Rachna Gupta"]', 1),
('delhi_koncept_gurugram', 'Mahindra Koncept Automobiles - Gurugram', 'Delhi', 'Delhi', 'Sector 18 Gurugram', 'Old Delhi-Gurgaon Road, Near Maruti Plant, Sector 18, Gurugram, NCR', '122015', '+91 124 456 7800', 'gurugram@konceptmahindra.com', 'https://maps.google.com/?q=Mahindra+Koncept+Gurugram', 4.9, '["Ashok Yadav", "Pooja Ahluwalia"]', 1),
('delhi_dynamic_noida', 'Mahindra Dynamic Motors - Noida', 'Delhi', 'Delhi', 'Sector 63 Noida', 'D-Block, Sector 63, Near Electronic City Metro, Noida, NCR', '201301', '+91 120 488 9900', 'noida@dynamicmahindra.com', 'https://maps.google.com/?q=Mahindra+Dynamic+Motors+Noida', 4.8, '["Rahul Chauhan", "Swati Saxena"]', 1);

-- SEED DEALERSHIPS: BANGALORE
INSERT OR REPLACE INTO dealerships (id, name, city, state, area, address, pin_code, phone, email, map_url, rating, available_advisors, is_active)
VALUES
('bangalore_sireesh_hosur_rd', 'Mahindra Sireesh Auto - Hosur Road', 'Bangalore', 'Karnataka', 'Madiwala / Koramangala', 'No. 120/1, Hosur Main Road, Near Silk Board Junction, Madiwala, Bengaluru', '560068', '+91 80 4032 5500', 'hosur@sireeshauto.com', 'https://maps.google.com/?q=Mahindra+Sireesh+Auto+Hosur+Road+Bangalore', 4.9, '["Suresh Gowda (SUV Lead)", "Deepa Murthy (EV Specialist)"]', 1),
('bangalore_anant_bannerghatta', 'Mahindra Anant Cars - Bannerghatta Road', 'Bangalore', 'Karnataka', 'JP Nagar / Bannerghatta', 'No. 44, Bannerghatta Main Road, Opposite IIM-B, JP Nagar, Bengaluru', '560076', '+91 80 4344 7700', 'bannerghatta@anantcars.com', 'https://maps.google.com/?q=Mahindra+Anant+Cars+Bannerghatta+Bangalore', 4.8, '["Karthik Reddy", "Pavithra Rao"]', 1),
('bangalore_sireesh_marathahalli', 'Mahindra Sireesh Auto - Marathahalli', 'Bangalore', 'Karnataka', 'Marathahalli / Outer Ring Road', 'Outer Ring Road, Near Marathahalli Bridge & Prestige Tech Park, Bengaluru', '560037', '+91 80 6766 8800', 'marathahalli@sireeshauto.com', 'https://maps.google.com/?q=Mahindra+Sireesh+Marathahalli+Bangalore', 4.8, '["Vinod Hegde", "Lavanya Nair"]', 1),
('bangalore_india_garage_vasanth', 'Mahindra India Garage - Central Bengaluru', 'Bangalore', 'Karnataka', 'Vasanth Nagar / Palace Road', 'No. 1, Palace Cross Road, Near Mount Carmel College, Vasanth Nagar, Bengaluru', '560020', '+91 80 2235 6600', 'palace@indiagarage.com', 'https://maps.google.com/?q=Mahindra+India+Garage+Palace+Road+Bangalore', 4.9, '["Vijay Raghavan", "Ananya Bhat"]', 1),
('bangalore_anant_mysore_rd', 'Mahindra Anant Cars - Mysore Road', 'Bangalore', 'Karnataka', 'Nayandahalli', 'No. 88, Mysore Main Road, Near Nayandahalli Metro Station, Bengaluru', '560039', '+91 80 2860 3300', 'mysoreroad@anantcars.com', 'https://maps.google.com/?q=Mahindra+Anant+Cars+Mysore+Road+Bangalore', 4.7, '["Chetan Kumar", "Meghana Raj"]', 1),
('bangalore_sireesh_yelahanka', 'Mahindra Sireesh Auto - North Bengaluru', 'Bangalore', 'Karnataka', 'Yelahanka / Hebbal', 'Bellary Main Road, Near Esteem Mall & Yelahanka Bypass, Bengaluru', '560064', '+91 80 4911 2200', 'yelahanka@sireeshauto.com', 'https://maps.google.com/?q=Mahindra+Sireesh+Yelahanka+Bangalore', 4.8, '["Pradeep Nayak", "Bhavana Swamy"]', 1);

-- SEED DEALERSHIPS: CHENNAI
INSERT OR REPLACE INTO dealerships (id, name, city, state, area, address, pin_code, phone, email, map_url, rating, available_advisors, is_active)
VALUES
('chennai_mpl_anna_salai', 'Mahindra MPL Automobiles - Mount Road', 'Chennai', 'Tamil Nadu', 'Nandanam / Anna Salai', 'No. 498, Anna Salai (Mount Road), Near Nandanam Signal, Chennai', '600035', '+91 44 2434 5500', 'mountroad@mplauto.com', 'https://maps.google.com/?q=Mahindra+MPL+Anna+Salai+Chennai', 4.9, '["Ravi Chandran (Chief SUV Consultant)", "Lakshmi Narayanan (EV Specialist)"]', 1),
('chennai_zulaikha_ambattur', 'Mahindra Zulaikha Motors - Ambattur', 'Chennai', 'Tamil Nadu', 'Ambattur Industrial Estate', 'Plot 58, South Phase, Ambattur Industrial Estate, Chennai', '600058', '+91 44 4390 1100', 'ambattur@zulaikhamotors.com', 'https://maps.google.com/?q=Mahindra+Zulaikha+Ambattur+Chennai', 4.8, '["Senthil Nathan", "Divya Krishnan"]', 1),
('chennai_vst_kilpauk', 'Mahindra VST Motors - Central Chennai', 'Chennai', 'Tamil Nadu', 'Kilpauk / Poonamallee', 'No. 144, Poonamallee High Road, Near Kilpauk Medical College, Chennai', '600010', '+91 44 2836 7700', 'kilpauk@vstmotors.com', 'https://maps.google.com/?q=Mahindra+VST+Kilpauk+Chennai', 4.8, '["Karthik Sundaram", "Sneha Ram"]', 1),
('chennai_mpl_omr', 'Mahindra MPL Automobiles - OMR IT Corridor', 'Chennai', 'Tamil Nadu', 'Perungudi / OMR', 'Rajiv Gandhi Salai (OMR), Near Perungudi Toll Plaza & RMZ Millenia, Chennai', '600096', '+91 44 6655 4400', 'omr@mplauto.com', 'https://maps.google.com/?q=Mahindra+MPL+OMR+Chennai', 4.9, '["Venkatesh Babu", "Archana Murugan"]', 1),
('chennai_zulaikha_chromepet', 'Mahindra Zulaikha Motors - South Chennai', 'Chennai', 'Tamil Nadu', 'Chromepet / GST Road', 'No. 22, Grand Southern Trunk (GST) Road, Near Chromepet Railway Station, Chennai', '600044', '+91 44 2241 8800', 'chromepet@zulaikhamotors.com', 'https://maps.google.com/?q=Mahindra+Zulaikha+Chromepet+Chennai', 4.7, '["Balaji Raman", "Swetha Natarajan"]', 1),
('chennai_vst_velachery', 'Mahindra VST Motors - Velachery', 'Chennai', 'Tamil Nadu', 'Velachery', 'No. 76, Velachery Main Road, Near Phoenix Marketcity, Chennai', '600042', '+91 44 4299 3300', 'velachery@vstmotors.com', 'https://maps.google.com/?q=Mahindra+VST+Velachery+Chennai', 4.8, '["Dinesh Kumar", "Keerthana Selvam"]', 1);

