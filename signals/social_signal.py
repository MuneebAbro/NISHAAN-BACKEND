import random

NEIGHBORHOODS = ["Gulshan", "Saddar", "Korangi", "Lyari", "DHA", "Clifton", "Orangi", "Malir", "Kemari", "Nazimabad"]
CRISIS_TYPES = ["urban flooding", "heatwave", "road accident", "power outage", "water main burst", "fire", "building collapse"]

def fetch_social_signals(force_multi=False):
    reports = []
    
    # Decide if we inject a false alarm scenario (20% chance)
    inject_false_alarm = random.random() < 0.2 and not force_multi
    
    num_events = 2 if force_multi else 1
    
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
