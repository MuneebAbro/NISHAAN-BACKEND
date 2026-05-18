import os
import json
import time
from groq import Groq

def classify_crisis(fused_context):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _mock_classification(fused_context)

    prompt = """You are NISHAAN's crisis classification engine for Karachi, Pakistan. 
You receive fused signals from weather, social media, and traffic sources. 
Analyze them and return ONLY valid JSON with this exact structure:
{
  "crisisDetected": boolean,
  "crisisType": string,
  "severity": string,
  "confidence": float,
  "neighborhood": string,
  "affectedPopulation": number,
  "expectedDurationHours": number,
  "spreadRisk": string,
  "conflictingSignals": boolean,
  "falseAlarmProbability": float,
  "reasoning": string
}"""

    client = Groq(api_key=api_key)

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt + "\n\nData:\n" + json.dumps(fused_context)
                    }
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"}
            )
            text = response.choices[0].message.content
            return json.loads(text.strip())

        except Exception as e:
            if "429" in str(e):
                wait = 10 * (attempt + 1)
                print(f"Groq rate limited. Waiting {wait}s then retrying...")
                time.sleep(wait)
            else:
                print(f"Groq API error: {e}")
                break

    print("Falling back to rule-based classification.")
    return _mock_classification(fused_context)


def _mock_classification(fused_context):
    num_reports = fused_context.get("num_reports", 0)
    social_cred = fused_context.get("social_credibility", 0)
    n = fused_context.get("neighborhood", "Unknown")

    detected = num_reports > 2
    false_alarm = social_cred < 0.4

    return {
        "crisisDetected": detected,
        "crisisType": "urban flooding" if "flood" in str(fused_context) else "road accident",
        "severity": "HIGH" if num_reports > 6 else "MEDIUM",
        "confidence": 0.8 if social_cred > 0.6 else 0.4,
        "neighborhood": n,
        "affectedPopulation": num_reports * 150,
        "expectedDurationHours": 4,
        "spreadRisk": "MEDIUM",
        "conflictingSignals": False,
        "falseAlarmProbability": 0.8 if false_alarm else 0.1,
        "reasoning": f"Rule-based fallback. {num_reports} reports in {n} (Gemini unavailable)."
    }
