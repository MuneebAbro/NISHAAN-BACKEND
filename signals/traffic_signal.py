import random

NEIGHBORHOODS = ["Gulshan", "Saddar", "Korangi", "Lyari", "DHA", "Clifton", "Orangi", "Malir", "Kemari", "Nazimabad"]

def fetch_traffic_signals():
    traffic_data = {}
    
    for n in NEIGHBORHOODS:
        congestion = random.uniform(0.0, 0.3)
        incident_hint = "clear"
        
        if random.random() < 0.2:
            congestion = random.uniform(0.7, 1.0)
            incident_hint = random.choice(["unusual slowdown", "road closed", "accident reported", "gridlock"])
            
        traffic_data[n] = {
            "congestion": congestion,
            "incidentHint": incident_hint,
            "credibility": 0.8
        }
        
    return traffic_data
