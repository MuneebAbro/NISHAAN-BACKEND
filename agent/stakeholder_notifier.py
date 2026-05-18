def generate_messages(classification, allocated, simulated_actions):
    n = classification.get("neighborhood", "Unknown")
    c_type = classification.get("crisisType", "incident")
    sev = classification.get("severity", "MEDIUM")
    conf = classification.get("confidence", 0.0)
    
    public_msg = f"ALERT: {sev} {c_type} in {n}. Please avoid the area. Emergency teams dispatched."
    hospital_msg = f"CLINICAL BRIEFING: {sev} {c_type} in {n}. Expect possible casualties. ETA 15-30 mins."
    utility_msg = f"TECHNICAL ESCALATION: Potential infrastructure impact at {n} due to {c_type}. Priority {sev}."
    police_msg = f"OPERATIONAL ORDER: {allocated.get('policeUnits', 0)} units needed at {n}. Objective: Secure area."
    media_msg = f"SITREP: {c_type.title()} reported in {n}. Severity: {sev}. System Confidence: {conf:.2f}. " \
                f"Resources deployed: {', '.join([f'{c} {r}' for r, c in allocated.items() if c > 0])}."
                
    return {
        "PUBLIC": public_msg,
        "HOSPITAL": hospital_msg,
        "UTILITY_COMPANY": utility_msg,
        "POLICE": police_msg,
        "MEDIA": media_msg
    }
