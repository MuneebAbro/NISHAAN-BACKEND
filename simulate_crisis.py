#!/usr/bin/env python3
import os
import sys
import time
import random
import argparse
from datetime import datetime, timezone, timedelta

# Add project root to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environmental variables
from dotenv import load_dotenv
load_dotenv()

# Configure GOOGLE_APPLICATION_CREDENTIALS dynamically to point to the local serviceAccountKey.json
key_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Nishaan", "serviceAccountKey.json"))
if os.path.exists(key_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    print(f"[*] Firebase configuration loaded from local key: {key_path}")
else:
    print(f"[!] Warning: serviceAccountKey.json not found at expected path: {key_path}")

from firestore.writer import FirestoreWriter
from agent.resource_allocator import ResourceAllocator
from agent.action_simulator import simulate_action
from agent.stakeholder_notifier import generate_messages

AREAS = [
    # Karachi
    "Steel Town (Karachi)",
    "Gulshan (Karachi)",
    "Saddar (Karachi)",
    "Korangi (Karachi)",
    "Lyari (Karachi)",
    "DHA (Karachi)",
    "Clifton (Karachi)",
    "Orangi (Karachi)",
    "Malir (Karachi)",
    "Kemari (Karachi)",
    "Nazimabad (Karachi)",
    # Lahore
    "Gulberg (Lahore)",
    "DHA Phase 5 (Lahore)",
    "Model Town (Lahore)",
    "Johar Town (Lahore)",
    "Anarkali (Lahore)",
    # Islamabad
    "Blue Area (Islamabad)",
    "Sector F-6 (Islamabad)",
    "Sector G-9 (Islamabad)",
    "Sector I-8 (Islamabad)",
    # Rawalpindi
    "Saddar (Rawalpindi)",
    "Bahria Town (Rawalpindi)",
    "Satellite Town (Rawalpindi)",
    # Peshawar
    "Hayatabad (Peshawar)",
    "University Road (Peshawar)",
    # Quetta
    "Hazara Town (Quetta)",
    "Jinnah Road (Quetta)",
    # Faisalabad
    "Clock Tower (Faisalabad)",
    "D Ground (Faisalabad)",
    # Multan
    "Gulgasht Colony (Multan)",
    "Cantonment (Multan)"
]

CRISIS_TYPES = [
    "urban flooding",
    "heatwave",
    "road accident",
    "power outage",
    "water main burst",
    "fire",
    "building collapse"
]

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MONITORING"]

def print_menu(title, options):
    print(f"\n=== {title} ===")
    for idx, opt in enumerate(options, 1):
        print(f" {idx}. {opt}")
    
    while True:
        try:
            choice = input(f"Select option (1-{len(options)}): ").strip()
            val = int(choice)
            if 1 <= val <= len(options):
                return options[val-1]
        except ValueError:
            pass
        print("[!] Invalid choice, try again.")

def main():
    parser = argparse.ArgumentParser(description="NISHAAN Crisis Simulation Injector")
    parser.add_argument("--neighborhood", choices=AREAS, help="Area/neighborhood name")
    parser.add_argument("--type", choices=CRISIS_TYPES, help="Type of crisis event")
    parser.add_argument("--severity", choices=SEVERITIES, help="Crisis severity level")
    parser.add_argument("--reasoning", help="Custom description/reasoning text")
    
    args = parser.parse_args()
    
    # Run interactively if arguments are missing
    if not (args.neighborhood and args.type and args.severity):
        print("\n--- NISHAAN INTERACTIVE CRISIS SIMULATION TOOL ---")
        args.neighborhood = print_menu("SELECT TARGET AREA", AREAS)
        args.type = print_menu("SELECT CRISIS TYPE", CRISIS_TYPES)
        args.severity = print_menu("SELECT SEVERITY LEVEL", SEVERITIES)
        
    if not args.reasoning:
        default_reasoning = f"Simulated {args.type} reported in {args.neighborhood}. Response units dispatched."
        args.reasoning = input(f"\nEnter description [default: '{default_reasoning}']: ").strip()
        if not args.reasoning:
            args.reasoning = default_reasoning
            
    print(f"\n[*] Initiating simulation injection:")
    print(f"    - Area:     {args.neighborhood}")
    print(f"    - Type:     {args.type}")
    print(f"    - Severity: {args.severity}")
    print(f"    - Detail:   {args.reasoning}")
    
    # 1. Build classification dictionary
    classification = {
        "crisisDetected": True,
        "crisisType": args.type,
        "severity": args.severity,
        "neighborhood": args.neighborhood,
        "confidence": 0.95,
        "reasoning": args.reasoning,
        "affectedPopulation": random.randint(150, 4500),
        "expectedDurationHours": random.randint(4, 36),
        "spreadRisk": random.choice(["LOW", "MEDIUM", "HIGH"]),
        "falseAlarmProbability": 0.02
    }
    
    # 2. Initialize Firestore writer
    writer = FirestoreWriter()
    if not writer.db:
        print("[!] Error: Firestore connection failed. Cannot write to Firebase. Exiting.")
        sys.exit(1)
        
    # 3. Allocate resources
    allocator = ResourceAllocator()
    crisis_id = f"crisis_{int(time.time())}_0"
    alloc_result = allocator.allocate(crisis_id, classification)
    allocated = alloc_result["allocated"]
    
    # 4. Simulate action descriptions
    simulated_actions = []
    for res_type, count in allocated.items():
        sim_act = simulate_action(res_type, count, classification)
        simulated_actions.append(sim_act)
        
    # 5. Generate stakeholder messages
    messages = generate_messages(classification, allocated, simulated_actions)
    
    # 6. Write to Firestore (this triggers FCM push notifications automatically!)
    print("[*] Writing crisis to database...")
    writer.write_crisis(crisis_id, classification, "ACTIVE", allocated, messages, simulated_actions)
    writer.write_alerts(crisis_id, classification, messages)
    
    print(f"\n[+] SUCCESS: Crisis '{crisis_id}' has been injected successfully!")
    print(f"    - View in client dashboard/map centered on: {args.neighborhood}")
    print(f"    - Push notification sent to topic 'all_users'")
    print("----------------------------------------------------\n")

if __name__ == "__main__":
    main()
