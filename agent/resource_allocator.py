class ResourceAllocator:
    def __init__(self):
        self.total_resources = {
            "ambulances": 5,
            "rescueTeams": 3,
            "policeUnits": 8,
            "waterTankers": 4,
            "fieldInspectors": 6,
            "emergencyGenerators": 3,
            "publicAlertChannels": 2
        }
        self.available_resources = self.total_resources.copy()
        
    def reset(self):
        self.available_resources = self.total_resources.copy()

    def allocate(self, crisis_id, classification):
        self.reset()
        
        req = {}
        c_type = classification.get("crisisType", "")
        sev = classification.get("severity", "MEDIUM")
        
        if c_type == "flood" or c_type == "urban flooding":
            req = {"rescueTeams": 2, "ambulances": 2, "policeUnits": 3, "publicAlertChannels": 1}
        elif c_type == "heatwave":
            req = {"ambulances": 2, "waterTankers": 2, "publicAlertChannels": 1}
        elif c_type == "road accident" or c_type == "accident":
            req = {"ambulances": 2, "policeUnits": 2, "fieldInspectors": 1}
        elif c_type == "power outage" or c_type == "powerOutage":
            req = {"emergencyGenerators": 2, "fieldInspectors": 1}
        else:
            req = {"policeUnits": 1, "fieldInspectors": 1}
            
        allocated = {}
        shortages = {}
        tradeoff_reasoning = ""
        
        for res, needed in req.items():
            avail = self.available_resources.get(res, 0)
            if avail >= needed:
                allocated[res] = needed
                self.available_resources[res] -= needed
            else:
                allocated[res] = avail
                shortages[res] = needed - avail
                self.available_resources[res] = 0
                tradeoff_reasoning += f"Reduced {res} from {needed} to {avail} due to constraint. "
                
        return {
            "allocated": allocated,
            "shortages": shortages,
            "tradeoff_reasoning": tradeoff_reasoning.strip()
        }
