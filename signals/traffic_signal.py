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
