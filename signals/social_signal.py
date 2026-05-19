import random

NEIGHBORHOODS = [
    # Karachi
    "Gulshan (Karachi)", "Saddar (Karachi)", "Korangi (Karachi)", "Lyari (Karachi)", 
    "DHA (Karachi)", "Clifton (Karachi)", "Orangi (Karachi)", "Malir (Karachi)", 
    "Kemari (Karachi)", "Nazimabad (Karachi)", "Steel Town (Karachi)",
    # Lahore
    "Gulberg (Lahore)", "DHA Phase 5 (Lahore)", "Model Town (Lahore)", 
    "Johar Town (Lahore)", "Anarkali (Lahore)",
    # Islamabad
    "Blue Area (Islamabad)", "Sector F-6 (Islamabad)", "Sector G-9 (Islamabad)", 
    "Sector I-8 (Islamabad)",
    # Rawalpindi
    "Saddar (Rawalpindi)", "Bahria Town (Rawalpindi)", "Satellite Town (Rawalpindi)",
    # Peshawar
    "Hayatabad (Peshawar)", "University Road (Peshawar)",
    # Quetta
    "Hazara Town (Quetta)", "Jinnah Road (Quetta)",
    # Faisalabad
    "Clock Tower (Faisalabad)", "D Ground (Faisalabad)",
    # Multan
    "Gulgasht Colony (Multan)", "Cantonment (Multan)"
]

CRISIS_TYPES = ["urban flooding", "heatwave", "road accident", "power outage", "water main burst", "fire", "building collapse"]

def fetch_social_signals(force_multi=False):
    reports = []
    
    # Decide if we inject a false alarm scenario (20% chance)
    inject_false_alarm = random.random() < 0.2 and not force_multi
    
    # Simulate multiple concurrent events (between 3 and 6) to cover multiple cities/areas
    num_events = random.randint(3, 6) if not inject_false_alarm else 1
    
    for _ in range(num_events):
        target_neighborhood = random.choice(NEIGHBORHOODS)
        target_crisis = random.choice(CRISIS_TYPES)
        
        num_reports = random.randint(5, 12)
        
        if inject_false_alarm:
            num_reports = random.randint(2, 4) # fewer reports
            target_crisis = "fire"
        
        for _ in range(num_reports):
            cred = random.uniform(0.3, 0.9)
            if inject_false_alarm:
                cred = random.uniform(0.1, 0.4) # Low credibility
                
            report = {
                "neighborhood": target_neighborhood,
                "text": f"Emergency in {target_neighborhood}! Looks like {target_crisis}.",
                "urgency": random.uniform(0.4, 1.0),
                "geo_confidence": random.uniform(0.5, 1.0),
                "credibility": cred
            }
            reports.append(report)
            
    return reports
