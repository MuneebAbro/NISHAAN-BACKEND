"""
NISHAAN Autonomous Agent — Vercel Serverless Endpoint

This is the main entry point for the agent. It runs as a Vercel serverless function
triggered by a cron job every minute (configured in vercel.json).

Endpoint: GET /api/run
"""

import os
import sys
import time
import math
import json
import logging
import random
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

# Add project root to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from signals.weather_signal import fetch_weather_signal
from signals.social_signal import fetch_social_signals
from signals.traffic_signal import fetch_traffic_signals
from agent.signal_fuser import fuse_signals
from agent.crisis_classifier import classify_crisis
from agent.resource_allocator import ResourceAllocator
from agent.action_simulator import simulate_action
from agent.stakeholder_notifier import generate_messages
from firestore.writer import FirestoreWriter

logging.basicConfig(level=logging.INFO, format='%(message)s')
pk_time = timezone(timedelta(hours=5))


def log_trace(writer, step, action, reasoning, confidence=None, crisis_id=None, input_data=None, output_data=None):
    timestamp = datetime.now(pk_time).isoformat()
    conf_str = f" (confidence: {confidence:.2f})" if confidence is not None else ""
    log_msg = f"[NISHAAN AGENT] {timestamp} [STEP {step}] {action} — {reasoning}{conf_str}"
    logging.info(log_msg)
    
    if crisis_id:
        # Convert confidence to integer percentage if it is a float
        conf_val = None
        if confidence is not None:
            try:
                conf_val = int(float(confidence) * 100)
            except:
                conf_val = None

        # Build metadata map expected by Android client
        meta = {}
        if input_data:
            meta["input_data"] = input_data
        if output_data:
            meta["output_data"] = output_data

        # Extract person_id if this is a missing person linking step
        missing_person_id = None
        if input_data and isinstance(input_data, dict):
            missing_person_id = input_data.get("person_id")

        writer.write_agent_trace({
            "agent_name": "NISHAAN Autonomous Agent",
            "crisis_id": crisis_id,
            "step": step,
            "action": action,
            "reasoning_summary": reasoning,
            "confidence": conf_val,
            "metadata": meta,
            "missing_person_id": missing_person_id
        })


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2)**2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * (math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def process_unlinked_missing_persons(writer):
    active_crises = writer.get_active_crises()
    if not active_crises:
        return 0
        
    unlinked_persons = writer.get_unlinked_missing_persons()
    if not unlinked_persons:
        return 0

    linked_count = 0
    for person in unlinked_persons:
        loc = person.get('last_seen_location')
        if not loc:
            continue
            
        person_lat = loc.latitude
        person_lon = loc.longitude
        
        closest_crisis = None
        min_distance = float('inf')
        
        for crisis in active_crises:
            c_loc = crisis.get('centroid')
            if not c_loc:
                continue
                
            c_lat = c_loc.latitude
            c_lon = c_loc.longitude
            radius = crisis.get('impact_radius_km', 5.0)
            
            dist = haversine_distance(person_lat, person_lon, c_lat, c_lon)
            if dist <= radius and dist < min_distance:
                min_distance = dist
                closest_crisis = crisis
                
        if closest_crisis:
            crisis_id = closest_crisis['id']
            person_id = person['id']
            writer.link_missing_person(person_id, crisis_id)
            linked_count += 1
            
            log_trace(
                writer,
                step=7,
                action="MISSING_PERSON_LINKED",
                reasoning=f"Linked missing person {person.get('person_name', 'Unknown')} to crisis {closest_crisis.get('title_en', crisis_id)} (distance: {min_distance:.2f}km).",
                crisis_id=crisis_id,
                input_data={"person_id": person_id, "distance": min_distance}
            )

    return linked_count


def check_witness_match(person_desc, sighting_desc):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        w1 = set(person_desc.lower().split())
        w2 = set(sighting_desc.lower().split())
        overlap = w1.intersection(w2)
        common_keywords = {"shirt", "jeans", "blue", "red", "black", "cap", "bag", "glasses", "tall", "short"}
        matches = overlap.intersection(common_keywords)
        similarity = 85 if len(matches) >= 1 else 30
        return similarity, f"Heuristic visual signature match based on keywords: {', '.join(matches)}" if matches else "No matching keywords."

    from groq import Groq
    prompt = """You are MATCHER, NISHAAN's missing person similarity matcher.
Compare the missing person's profile description and a witness sighting report.
Determine if the sighting is highly likely to be the same missing person (similarity score 0 to 100).
Return ONLY valid JSON with this exact structure:
{
  "similarity_score": number, // integer 0-100
  "reasoning": string // brief English explanation of visual corroboration (e.g. clothing overlap, height, features)
}"""

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nMissing Person Description:\n{person_desc}\n\nSighting Report:\n{sighting_desc}"
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        res = json.loads(response.choices[0].message.content.strip())
        return int(res.get("similarity_score", 0)), res.get("reasoning", "")
    except Exception as e:
        print(f"Error calling Groq in MATCHER: {e}")
        return 50, "Error running Groq matcher. Fallback to medium confidence."


def process_witness_reports(writer):
    active_persons = writer.get_all_active_missing_persons()
    if not active_persons:
        return 0

    processed_count = 0
    for person in active_persons:
        person_id = person['id']
        reports = writer.get_witness_reports(person_id)
        
        unprocessed = [r for r in reports if not r.get('processed')]
        for report in unprocessed:
            report_id = report['id']
            visual_desc = report.get('visual_details', '')
            person_desc = person.get('description', '')
            
            score, reasoning = check_witness_match(person_desc, visual_desc)
            
            if score >= 60:
                log_trace(
                    writer,
                    step=8,
                    action="WITNESS_CORROBORATED",
                    reasoning=f"🔍 Match similarity {score}%: {reasoning}",
                    confidence=score / 100.0,
                    crisis_id=person.get("linked_crisis_id") or "unlinked",
                    input_data={"person_id": person_id, "sighting_id": report_id, "visual_details": visual_desc}
                )
            
            writer.mark_witness_report_processed(person_id, report_id)
            processed_count += 1

    return processed_count


def agent_loop():
    """Run one cycle of the agent loop. Returns a summary dict."""
    writer = FirestoreWriter()
    allocator = ResourceAllocator()
    
    # Use timestamp-based cycle count for multi-crisis injection (every 5th minute)
    minute = datetime.now(pk_time).minute
    multi_crisis_injection = (minute % 5 == 0)
    
    weather = fetch_weather_signal()
    social = fetch_social_signals(force_multi=multi_crisis_injection)
    traffic = fetch_traffic_signals()
    
    fused_contexts = fuse_signals(weather, social, traffic)
    
    crises_detected = 0
    crises_written = 0
    false_alarms = 0
    
    for idx, context in enumerate(fused_contexts):
        crisis_id = f"crisis_{int(time.time())}_{idx}"
        
        classification = classify_crisis(context)
        if not classification.get("crisisDetected", False):
            continue
        
        crises_detected += 1
        
        weather_desc = f"weather: {weather.get('conditionCode', 'unknown')} (cred: {weather.get('credibility', 0):.2f})"
        social_desc = f"social: {len(social)} reports"
        
        log_trace(
            writer,
            step=1, 
            action="SIGNAL FUSION", 
            reasoning=f"Weather: {weather_desc}, Social: {social_desc}, Traffic: data loaded",
            crisis_id=crisis_id,
            input_data={"weather": weather, "social": social, "traffic": traffic},
            output_data=context
        )
        
        log_trace(
            writer,
            step=2,
            action="CRISIS CLASSIFIED",
            reasoning=f"{classification.get('crisisType')} / {classification.get('severity')} / {classification.get('neighborhood')}",
            confidence=classification.get("confidence", 0.0),
            crisis_id=crisis_id,
            input_data=context,
            output_data=classification
        )
        
        false_alarm_prob = classification.get("falseAlarmProbability", 0.0)
        conflicting = classification.get("conflictingSignals", False)
        
        if false_alarm_prob > 0.6 or conflicting:
            log_trace(
                writer,
                step=2.5,
                action="FALSE ALARM VERIFICATION",
                reasoning=f"High false alarm prob ({false_alarm_prob}) or conflicting signals. Dispatching field inspector.",
                crisis_id=crisis_id
            )
            if random.random() < false_alarm_prob:
                log_trace(
                    writer,
                    step=3,
                    action="ALERT RETRACTED",
                    reasoning="Signal was confirmed as false alarm by field verification.",
                    crisis_id=crisis_id
                )
                writer.write_crisis(crisis_id, classification, "FALSE_ALARM")
                false_alarms += 1
                continue
            else:
                log_trace(
                    writer,
                    step=3,
                    action="SIGNAL VERIFIED",
                    reasoning="Signal verified by field inspector — escalating",
                    crisis_id=crisis_id
                )
        
        if classification.get("confidence", 0) > 0.4:
            alloc_result = allocator.allocate(crisis_id, classification)
            allocated = alloc_result["allocated"]
            tradeoffs = alloc_result["tradeoff_reasoning"]
            
            res_str = ", ".join([f"{count} {res}" for res, count in allocated.items()])
            reasoning_str = f"Allocated: {res_str}. Trade-offs: {tradeoffs}" if tradeoffs else f"Allocated: {res_str}."
            
            log_trace(
                writer,
                step=4,
                action="RESOURCES ALLOCATED",
                reasoning=reasoning_str,
                crisis_id=crisis_id,
                input_data=classification,
                output_data=alloc_result
            )
            
            simulated_actions = []
            for res_type, count in allocated.items():
                sim_act = simulate_action(res_type, count, classification)
                simulated_actions.append(sim_act)
            
            actions_summary = " ".join([s["action"] for s in simulated_actions])
            log_trace(
                writer,
                step=5,
                action="ACTIONS SIMULATED",
                reasoning=actions_summary,
                crisis_id=crisis_id,
                output_data={"simulated_actions": simulated_actions}
            )
            
            messages = generate_messages(classification, allocated, simulated_actions)
            
            writer.write_crisis(crisis_id, classification, "ACTIVE", allocated, messages, simulated_actions)
            writer.write_alerts(crisis_id, classification, messages)
            crises_written += 1
            
            log_trace(
                writer,
                step=6,
                action="FIRESTORE UPDATED",
                reasoning=f"crises/{crisis_id} written. Alerts generated.",
                crisis_id=crisis_id
            )
            
    # After processing all signals, link unlinked missing persons
    linked_count = process_unlinked_missing_persons(writer)
    witness_reports_processed = process_witness_reports(writer)
    
    return {
        "firestore_connected": (writer.db is not None),
        "crises_detected": crises_detected,
        "crises_written": crises_written,
        "false_alarms": false_alarms,
        "missing_persons_linked": linked_count,
        "witness_reports_processed": witness_reports_processed,
        "multi_crisis_mode": multi_crisis_injection
    }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_GET(self):
        try:
            result = agent_loop()
            
            response = {
                "status": "ok",
                "timestamp": datetime.now(pk_time).isoformat(),
                "result": result
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            error_response = {
                "status": "error",
                "timestamp": datetime.now(pk_time).isoformat(),
                "error": str(e)
            }
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())
