import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

class FirestoreWriter:
    def __init__(self):
        try:
            if not firebase_admin._apps:
                # Try base64-encoded service account from env var (for Vercel deployment)
                b64_key = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64")
                cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                
                if b64_key:
                    sanitized_key = b64_key.strip().replace("\n", "").replace("\r", "").replace(" ", "")
                    service_account_info = json.loads(base64.b64decode(sanitized_key).decode('utf-8'))
                    cred = credentials.Certificate(service_account_info)
                    firebase_admin.initialize_app(cred)
                    print("SUCCESS: Firestore initialized successfully with Base64 credentials.")
                elif cred_path:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    print("SUCCESS: Firestore initialized successfully with GOOGLE_APPLICATION_CREDENTIALS path.")
                else:
                    print("WARNING: No Firebase credentials provided. Firestore writes will be mocked.")
                    self.db = None
                    return
                    
            self.db = firestore.client()
        except Exception as e:
            print(f"Failed to initialize Firestore: {e}. Writes will be mocked.")
            self.db = None

    def write_crisis(self, crisis_id, classification, status, allocated=None, messages=None, simulated_actions=None):
        if not self.db:
            return
            
        doc_ref = self.db.collection('crises').document(crisis_id)
        
        import random
        neighborhood_coords = {
            "Gulshan": (24.9180, 67.0970),
            "Saddar": (24.8600, 67.0100),
            "Korangi": (24.8300, 67.1200),
            "Lyari": (24.8700, 66.9900),
            "DHA": (24.8000, 67.0700),
            "Clifton": (24.8150, 67.0300),
            "Orangi": (24.9500, 66.9600),
            "Malir": (24.9000, 67.1900),
            "Kemari": (24.8200, 66.9700),
            "Nazimabad": (24.9100, 67.0300)
        }
        
        neighborhood = classification.get("neighborhood", "Unknown")
        base_lat, base_lon = neighborhood_coords.get(neighborhood, (24.8607, 67.0011))
        
        # Add slight dispersion offset to prevent exact overlap
        lat = base_lat + random.uniform(-0.006, 0.006)
        lon = base_lon + random.uniform(-0.006, 0.006)
        
        c_type_raw = str(classification.get("crisisType", "")).upper()
        if "FLOOD" in c_type_raw:
            mapped_type = "FLOOD"
        elif "ACCIDENT" in c_type_raw:
            mapped_type = "TRAFFIC_ACCIDENT"
        elif "HEATWAVE" in c_type_raw:
            mapped_type = "HEATWAVE"
        elif "FIRE" in c_type_raw or "COLLAPSE" in c_type_raw or "POWER" in c_type_raw or "WATER" in c_type_raw:
            mapped_type = "INFRASTRUCTURE_FAILURE"
        else:
            mapped_type = "UNKNOWN"

        sev_raw = str(classification.get("severity", "MONITORING")).upper()
        if sev_raw not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MONITORING"]:
            sev_raw = "MONITORING"
            
        try:
            conf_val = int(float(classification.get("confidence", 0.0)) * 100)
        except:
            conf_val = 0
            
        neighborhood = classification.get("neighborhood", "Unknown")
        
        data = {
            "crisis_type": mapped_type,
            "severity": sev_raw,
            "confidence": conf_val,
            "centroid": firestore.GeoPoint(lat, lon),
            "impact_radius_km": 5.0,
            "title_en": f"{mapped_type.replace('_', ' ')} Alert in {neighborhood}",
            "title_ur": f"الرٹ: {neighborhood} میں ہنگامی صورتحال",
            "description_en": messages.get("PUBLIC", classification.get("reasoning", "")) if messages else classification.get("reasoning", ""),
            "description_ur": "",
            "assigned_agencies": list(allocated.keys()) if allocated else [],
            "missing_persons_count": 0,
            "analyst_reasoning": classification.get("reasoning", ""),
            "status": status.upper() if status else "MONITORING",
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            
            # Legacy fields for debugging/traceability
            "type": classification.get("crisisType"),
            "neighborhood": neighborhood,
            "affectedPopulation": classification.get("affectedPopulation"),
            "expectedDurationHours": classification.get("expectedDurationHours"),
            "spreadRisk": classification.get("spreadRisk"),
            "conflictingSignals": classification.get("conflictingSignals", False)
        }
        
        if allocated:
            data["resourcesAllocated"] = allocated
        if messages:
            data["stakeholderMessages"] = messages
        if simulated_actions:
            data["simulatedActions"] = simulated_actions
            
        try:
            doc_ref.set(data, merge=True)
        except Exception as e:
            print(f"Error writing crisis to Firestore: {e}")

    def write_agent_trace(self, trace_data):
        if not self.db:
            return
            
        trace_data["timestamp"] = firestore.SERVER_TIMESTAMP
        
        try:
            self.db.collection('agent_traces').add(trace_data)
        except Exception as e:
            print(f"Error writing trace to Firestore: {e}")

    def write_alerts(self, crisis_id, classification, messages):
        if not self.db:
            return
            
        alert_data = {
            "crisisId": crisis_id,
            "severity": classification.get("severity"),
            "type": classification.get("crisisType"),
            "title": f"{classification.get('severity')} Alert: {classification.get('crisisType')}",
            "description": messages.get("PUBLIC", ""),
            "neighborhood": classification.get("neighborhood"),
            "isRead": False,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        
        try:
            self.db.collection('alerts').add(alert_data)
        except Exception as e:
            print(f"Error writing alert to Firestore: {e}")

    def get_active_crises(self):
        if not self.db:
            return []
        try:
            crises_ref = self.db.collection('crises').where(filter=FieldFilter('status', '==', 'ACTIVE')).stream()
            active_crises = []
            for doc in crises_ref:
                c_data = doc.to_dict()
                c_data['id'] = doc.id
                active_crises.append(c_data)
            return active_crises
        except Exception as e:
            print(f"Error getting active crises: {e}")
            return []

    def get_unlinked_missing_persons(self):
        if not self.db:
            return []
        try:
            # We query for reports that are SEARCHING or have no linked_crisis_id
            # Note: Firestore might require composite index if we do multiple clauses, 
            # so we fetch all 'SEARCHING' and filter in memory
            persons_ref = self.db.collection('missing_persons').where(filter=FieldFilter('status', '==', 'SEARCHING')).stream()
            unlinked = []
            for doc in persons_ref:
                p_data = doc.to_dict()
                if not p_data.get('linked_crisis_id'):
                    p_data['id'] = doc.id
                    unlinked.append(p_data)
            return unlinked
        except Exception as e:
            print(f"Error getting unlinked missing persons: {e}")
            return []

    def link_missing_person(self, person_id, crisis_id):
        if not self.db:
            return
        try:
            person_ref = self.db.collection('missing_persons').document(person_id)
            person_ref.update({
                'linked_crisis_id': crisis_id,
                'status': 'LINKED',
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Increment missing persons count in crisis
            crisis_ref = self.db.collection('crises').document(crisis_id)
            crisis_ref.update({
                'missing_persons_count': firestore.Increment(1)
            })
        except Exception as e:
            print(f"Error linking missing person: {e}")
