import random

def simulate_action(res_type, count, classification):
    if count == 0:
        return {
            "action": f"No {res_type} deployed",
            "beforeState": "",
            "expectedAfterState": "",
            "responseTimeMinutes": 0,
            "congestionImpact": "None",
            "resourceCost": "0 units",
            "sideEffects": []
        }
        
    n = classification.get("neighborhood", "Unknown")
    c_type = classification.get("crisisType", "incident")
    
    action_desc = f"Deploy {count} {res_type} to {n}"
    before_state = f"{n} is experiencing {c_type}"
    after_state = f"{res_type} arrival will mitigate {c_type} impacts"
    
    return {
        "action": action_desc,
        "beforeState": before_state,
        "expectedAfterState": after_state,
        "responseTimeMinutes": random.randint(10, 45),
        "congestionImpact": "High" if count > 2 else "Low",
        "resourceCost": f"{count} units",
        "sideEffects": ["traffic diversion in surrounding areas"] if count > 2 else []
    }
