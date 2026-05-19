import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from groq import Groq

def predict_spread_forecast(mapped_type, sev_raw, neighborhood, base_conf, reasoning):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _mock_spread_prediction(mapped_type)
        
    prompt = """You are NISHAAN's predictive crisis spread forecaster for Karachi, Pakistan.
You analyze an active crisis and forecast its spatial spread (impact radius increase/shrinkage) over the next 2 hours.
Based on the inputs, return ONLY valid JSON with this exact structure:
{
  "predicted_radius_km": float,
  "direction": string, // One of: "NORTH", "NORTH_EAST", "EAST", "SOUTH_EAST", "SOUTH", "SOUTH_WEST", "WEST", "NORTH_WEST", "STATIONARY"
  "confidence": number, // integer 0-100
  "reasoning_en": string, // brief English reasoning
  "reasoning_ur": string // Urdu translation of the reasoning
}"""

    client = Groq(api_key=api_key)
    try:
        data_input = {
            "crisis_type": mapped_type,
            "severity": sev_raw,
            "neighborhood": neighborhood,
            "confidence": base_conf,
            "reasoning": reasoning
        }
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt + "\n\nData:\n" + json.dumps(data_input)
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content
        return json.loads(text.strip())
    except Exception as e:
        print(f"Error calling Groq for spread forecast: {e}")
        return _mock_spread_prediction(mapped_type)

def _mock_spread_prediction(mapped_type):
    # Rule-based fallback prediction
    if "FLOOD" in mapped_type:
        return {
            "predicted_radius_km": 7.5,
            "direction": "SOUTH_EAST",
            "confidence": 85,
            "reasoning_en": "Low-lying areas of Gulshan expected to accumulate water down-gradient towards Lyari Expressway.",
            "reasoning_ur": "گلشن کے نشیبی علاقوں میں پانی لیاری ایکسپریس وے کی طرف بہنے کا اندیشہ ہے۔"
        }
    elif "HEATWAVE" in mapped_type:
        return {
            "predicted_radius_km": 10.0,
            "direction": "STATIONARY",
            "confidence": 90,
            "reasoning_en": "Heat dome centered over urban core. No active wind movement forecast to dissipate thermal mass.",
            "reasoning_ur": "گرمی کا مرکز شہر کا اندرونی حصہ ہے۔ حرارت کو کم کرنے کے لیے ہوا کا کوئی بہاؤ متوقع نہیں ہے۔"
        }
    else:
        return {
            "predicted_radius_km": 4.5,
            "direction": "STATIONARY",
            "confidence": 75,
            "reasoning_en": "Standard incident perimeter maintained. No dynamic expansion vectors identified.",
            "reasoning_ur": "معیاری انسیڈنٹ پیرامیٹر برقرار ہے۔ پھیلاؤ کا کوئی متحرک اشارہ نہیں ملا۔"
        }

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

    def write_timeline_event(self, crisis_id, event_id, title, description, event_type, timestamp=None):
        if not self.db:
            return
        event_ref = self.db.collection('crises').document(crisis_id).collection('timeline').document(event_id)
        data = {
            "title": title,
            "description": description,
            "type": event_type,
            "timestamp": timestamp if timestamp else firestore.SERVER_TIMESTAMP
        }
        try:
            event_ref.set(data, merge=True)
        except Exception as e:
            print(f"Error writing timeline event to Firestore: {e}")

    def write_crisis(self, crisis_id, classification, status, allocated=None, messages=None, simulated_actions=None):
        if not self.db:
            return
            
        doc_ref = self.db.collection('crises').document(crisis_id)
        
        # Get existing crisis document if it exists to get verification counts
        try:
            existing = doc_ref.get()
            if existing.exists:
                existing_data = existing.to_dict()
            else:
                existing_data = {}
        except Exception as e:
            print(f"Error reading existing crisis: {e}")
            existing_data = {}

        # Feature 1: Verification Counts and Confidence Modifier
        yes = 0
        no = 0
        unsure = 0
        try:
            verifs_ref = doc_ref.collection("verifications").stream()
            for v_doc in verifs_ref:
                v_data = v_doc.to_dict()
                resp = str(v_data.get("response", "")).upper()
                if resp == "YES":
                    yes += 1
                elif resp == "NO":
                    no += 1
                elif resp == "UNSURE":
                    unsure += 1
            print(f"SUCCESS: Counted verifications from subcollection for crisis {crisis_id}: YES={yes}, NO={no}, UNSURE={unsure}")
        except Exception as e:
            print(f"WARNING: Error reading verifications subcollection: {e}. Falling back to parent counts.")
            yes = existing_data.get("verification_yes", 0)
            no = existing_data.get("verification_no", 0)
            unsure = existing_data.get("verification_unsure", 0)

        total = yes + no + unsure
        modifier = ((yes - no) / total * 0.2) if total > 0 else 0.0
        
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
            base_conf = float(classification.get("confidence", 0.0))
        except:
            base_conf = 0.0
            
        adjusted_confidence = min(1.0, max(0.0, base_conf + modifier))
        conf_val = int(adjusted_confidence * 100)
            
        neighborhood = classification.get("neighborhood", "Unknown")
        
        # Feature 3: Predicted Spread / Impact Radius Forecast
        spread_prediction = predict_spread_forecast(mapped_type, sev_raw, neighborhood, base_conf, classification.get("reasoning", ""))
        
        data = {
            "crisis_type": mapped_type,
            "severity": sev_raw,
            "confidence": conf_val,
            "confidence_modifier": modifier,
            "verification_yes": yes,
            "verification_no": no,
            "verification_unsure": unsure,
            "spread_prediction": spread_prediction,
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
            
            # Feature 2: Crisis Timeline / Pulse Feed seeding
            from datetime import datetime, timezone, timedelta
            pk_timezone = timezone(timedelta(hours=5))
            now = datetime.now(pk_timezone)
            
            # 1. SENTINEL_DETECTED
            s_time = now - timedelta(minutes=15)
            s_desc = f"Sentinel flagged a potential {mapped_type.replace('_', ' ')} in {neighborhood} via fused weather, social, and traffic data."
            self.write_timeline_event(crisis_id, "step_1_sentinel", "Potential crisis detected", s_desc, "SENTINEL", s_time)
            
            # 2. ANALYST_CLASSIFIED
            a_time = now - timedelta(minutes=10)
            a_desc = f"Crisis classified as {mapped_type.replace('_', ' ')}, severity {sev_raw}. Base confidence: {int(base_conf * 100)}%."
            self.write_timeline_event(crisis_id, "step_2_analyst", "Crisis classified and verified", a_desc, "ANALYST", a_time)
            
            # 3. COMMANDER_ALLOCATED
            c_time = now - timedelta(minutes=5)
            res_str = ", ".join([f"{count} {res.replace('_', ' ').title()}" for res, count in (allocated or {}).items()])
            c_desc = f"Resources allocated: {res_str or 'Monitoring only'}. Stakeholder alerts generated."
            self.write_timeline_event(crisis_id, "step_3_commander", "Resources dispatched", c_desc, "COMMANDER", c_time)
            
            # 4. VERIFICATION_ADJUSTED
            v_time = now
            v_desc = f"Crowd verification: {yes} YES, {no} NO, {unsure} UNSURE. Confidence score adjusted to {conf_val}%."
            self.write_timeline_event(crisis_id, "step_4_verification", "Crowd verification adjustment", v_desc, "ANALYST", v_time)
            
        except Exception as e:
            print(f"Error writing crisis or seeding timeline events to Firestore: {e}")

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

    def get_all_active_missing_persons(self):
        if not self.db:
            return []
        try:
            persons_ref = self.db.collection('missing_persons').stream()
            active_persons = []
            for doc in persons_ref:
                p_data = doc.to_dict()
                if p_data.get('status') != 'FOUND':
                    p_data['id'] = doc.id
                    active_persons.append(p_data)
            return active_persons
        except Exception as e:
            print(f"Error getting active missing persons: {e}")
            return []

    def get_witness_reports(self, person_id):
        if not self.db:
            return []
        try:
            reports_ref = self.db.collection('missing_persons').document(person_id).collection('witness_reports').stream()
            reports = []
            for doc in reports_ref:
                r_data = doc.to_dict()
                r_data['id'] = doc.id
                reports.append(r_data)
            return reports
        except Exception as e:
            print(f"Error getting witness reports: {e}")
            return []

    def mark_witness_report_processed(self, person_id, report_id):
        if not self.db:
            return
        try:
            report_ref = self.db.collection('missing_persons').document(person_id).collection('witness_reports').document(report_id)
            report_ref.update({
                'processed': True
            })
            
            # Increment witness_reports_count in parent missing person document
            person_ref = self.db.collection('missing_persons').document(person_id)
            person_ref.update({
                'witness_reports_count': firestore.Increment(1)
            })
        except Exception as e:
            print(f"Error marking witness report processed: {e}")
