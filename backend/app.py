from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import json
import re
import faiss
import numpy as np
import requests

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()


RESOURCE_MAP = {
    "anthrax": [
        {
            "title": "CDC: About Anthrax",
            "url": "https://www.cdc.gov/anthrax/about/index.html",
            "type": "public_health"
        },
        {
            "title": "CDC: Clinical Overview of Anthrax",
            "url": "https://www.cdc.gov/anthrax/hcp/clinical-overview/index.html",
            "type": "clinical"
        },
        {
            "title": "CDC: Anthrax as a Bioterrorism Threat",
            "url": "https://www.cdc.gov/anthrax/bioterrorism/index.html",
            "type": "preparedness"
        },
        {
            "title": "CDC: Anthrax Prevention",
            "url": "https://www.cdc.gov/anthrax/prevention/index.html",
            "type": "prevention"
        }
    ],

    "botulism": [
        {
            "title": "CDC: About Botulism",
            "url": "https://www.cdc.gov/botulism/about/index.html",
            "type": "public_health"
        },
        {
            "title": "CDC: Clinical Overview of Botulism",
            "url": "https://www.cdc.gov/botulism/hcp/clinical-overview/index.html",
            "type": "clinical"
        },
        {
            "title": "CDC: Symptoms of Botulism",
            "url": "https://www.cdc.gov/botulism/signs-symptoms/index.html",
            "type": "symptoms"
        },
        {
            "title": "CDC: Botulism as a Bioterrorism Threat",
            "url": "https://www.cdc.gov/botulism/bioterrorism/index.html",
            "type": "preparedness"
        }
    ],

    "smallpox": [
        {
            "title": "CDC: About Smallpox",
            "url": "https://www.cdc.gov/smallpox/about/index.html",
            "type": "public_health"
        },
        {
            "title": "CDC: Smallpox History",
            "url": "https://www.cdc.gov/smallpox/about/history.html",
            "type": "background"
        },
        {
            "title": "CDC: Smallpox as a Bioterrorism Threat",
            "url": "https://www.cdc.gov/smallpox/bioterrorism/index.html",
            "type": "preparedness"
        },
        {
            "title": "CDC Stacks: Smallpox Overview PDF",
            "url": "https://stacks.cdc.gov/view/cdc/26503/cdc_26503_DS1.pdf",
            "type": "reference"
        }
    ],

    "sarin": [
        {
            "title": "CDC: Sarin Fact Sheet",
            "url": "https://www.cdc.gov/chemical-emergencies/chemical-fact-sheets/sarin.html",
            "type": "public_health"
        },
        {
            "title": "NIOSH: Sarin (GB) Emergency Response Card",
            "url": "https://www.cdc.gov/niosh/ershdb/emergencyresponsecard_29750001.html",
            "type": "responder"
        },
        {
            "title": "CDC Stacks: Sarin Quick Reference Guide PDF",
            "url": "https://stacks.cdc.gov/view/cdc/248932/cdc_248932_DS1.pdf",
            "type": "reference"
        },
        {
            "title": "NIH NCBI: Sarin Background Reference",
            "url": "https://www.ncbi.nlm.nih.gov/books/NBK222849/",
            "type": "scientific"
        }
    ],

    "mustard gas": [
        {
            "title": "CDC: Mustard Gas Fact Sheet",
            "url": "https://www.cdc.gov/chemical-emergencies/chemical-fact-sheets/mustard-gas.html",
            "type": "public_health"
        },
        {
            "title": "NIOSH: Sulfur Mustard Emergency Response Card",
            "url": "https://www.cdc.gov/niosh/ershdb/emergencyresponsecard_29750008.html",
            "type": "responder"
        },
        {
            "title": "ATSDR: Sulfur Mustard ToxFAQs PDF",
            "url": "https://www.atsdr.cdc.gov/toxfaqs/tfacts49.pdf",
            "type": "toxicology"
        },
        {
            "title": "CDC Stacks: Sulfur Mustard Reference",
            "url": "https://stacks.cdc.gov/view/cdc/130184",
            "type": "reference"
        }
    ],

    "cyanide": [
        {
            "title": "CDC: Cyanide Fact Sheet",
            "url": "https://www.cdc.gov/chemical-emergencies/chemical-fact-sheets/cyanide.html",
            "type": "public_health"
        },
        {
            "title": "NIOSH: Hydrogen Cyanide Pocket Guide",
            "url": "https://www.cdc.gov/niosh/npg/npgd0333.html",
            "type": "responder"
        },
        {
            "title": "ATSDR: Cyanide ToxFAQs PDF",
            "url": "https://www.atsdr.cdc.gov/toxfaqs/tfacts8.pdf",
            "type": "toxicology"
        },
        {
            "title": "NIOSH: Hydrogen Cyanide Emergency Response Card",
            "url": "https://www.cdc.gov/niosh/ershdb/emergencyresponsecard_29750038.html",
            "type": "responder"
        }
    ],

    "radiological exposure": [
        {
            "title": "CDC: Radiation Emergencies",
            "url": "https://www.cdc.gov/radiation-emergencies/index.html",
            "type": "public_health"
        },
        {
            "title": "CDC: About Radiation Emergencies",
            "url": "https://www.cdc.gov/radiation-emergencies/about/index.html",
            "type": "background"
        },
        {
            "title": "CDC: Preparing for a Radiation Emergency",
            "url": "https://www.cdc.gov/radiation-emergencies/safety/index.html",
            "type": "preparedness"
        },
        {
            "title": "CDC: Radiation Response Briefing Manual PDF",
            "url": "https://www.cdc.gov/radiation-emergencies/media/pdfs/2024/04/20_316861-A_RadiationResponse-508-1.pdf",
            "type": "responder"
        }
    ],

    "nuclear fallout": [
        {
            "title": "CDC: Nuclear Blast FAQ",
            "url": "https://www.cdc.gov/radiation-emergencies/about/nuclear-blast-faq.html",
            "type": "public_health"
        },
        {
            "title": "CDC: Nuclear Weapon Infographic",
            "url": "https://www.cdc.gov/radiation-emergencies/infographic/nuclear-weapon.html",
            "type": "preparedness"
        },
        {
            "title": "CDC: Preparing for Radiation Incidents",
            "url": "https://www.cdc.gov/radiation-emergencies/hcp/nuclear-detonations/preparing.html",
            "type": "responder"
        },
        {
            "title": "CDC: Immediate Actions After a Nuclear Detonation",
            "url": "https://www.cdc.gov/radiation-emergencies/hcp/nuclear-detonations/immediate-actions.html",
            "type": "responder"
        }
    ],

    "ppe": [
        {
            "title": "NIOSH: PPE for Emergency Preparedness",
            "url": "https://www.cdc.gov/niosh/emres/safety/ppe.html",
            "type": "responder"
        },
        {
            "title": "NIOSH: Respirator Types and Use",
            "url": "https://www.cdc.gov/niosh/ppe/respirators/index.html",
            "type": "respiratory"
        },
        {
            "title": "NIOSH: CBRN Respiratory Protection Handbook Update",
            "url": "https://www.cdc.gov/niosh/bulletin/2025/cbrn-handbook.html",
            "type": "respiratory"
        },
        {
            "title": "NIOSH: Respiratory Protection for Emergencies",
            "url": "https://www.cdc.gov/niosh/bulletin/2009/respiratory-protection-emergencies.html",
            "type": "respiratory"
        }
    ],

    "respiratory protection": [
        {
            "title": "NIOSH: Respirator Types and Use",
            "url": "https://www.cdc.gov/niosh/ppe/respirators/index.html",
            "type": "respiratory"
        },
        {
            "title": "NIOSH: PPE for Emergency Preparedness",
            "url": "https://www.cdc.gov/niosh/emres/safety/ppe.html",
            "type": "responder"
        },
        {
            "title": "NIOSH: CBRN Respiratory Protection Handbook Update",
            "url": "https://www.cdc.gov/niosh/bulletin/2025/cbrn-handbook.html",
            "type": "respiratory"
        }
    ],

    "decontamination": [
        {
            "title": "CDC: How to Self-Decontaminate After a Radiation Emergency",
            "url": "https://www.cdc.gov/radiation-emergencies/prevention/self-decontaminate.html",
            "type": "public_health"
        },
        {
            "title": "CDC: Decontamination for Yourself and Others",
            "url": "https://www.cdc.gov/radiation-emergencies/infographic/decontamination.html",
            "type": "public_health"
        },
        {
            "title": "CDC: Safety Guidelines for Decontamination of Radioactive Material",
            "url": "https://www.cdc.gov/radiation-health/safety/decontamination.html",
            "type": "guidance"
        },
        {
            "title": "CDC: What to Do — Stay Inside",
            "url": "https://www.cdc.gov/radiation-emergencies/response/stay-inside.html",
            "type": "preparedness"
        }
    ],

    "emergency response": [
        {
            "title": "NIOSH: Emergency Response Safety and Health Database",
            "url": "https://www.cdc.gov/niosh/ershdb/default.html",
            "type": "responder"
        },
        {
            "title": "NIOSH: Emergency Preparedness and Response Program",
            "url": "https://www.cdc.gov/niosh/research-programs/portfolio/epr.html",
            "type": "program"
        },
        {
            "title": "CDC: Radiation Response Briefing Manual PDF",
            "url": "https://www.cdc.gov/radiation-emergencies/media/pdfs/2024/04/20_316861-A_RadiationResponse-508-1.pdf",
            "type": "responder"
        },
        {
            "title": "CDC: Response to Nuclear or Radiological Emergencies",
            "url": "https://www.cdc.gov/radiation-emergencies/programs/index.html",
            "type": "program"
        }
    ],

    "biosurveillance": [
        {
            "title": "CDC: BioSense Platform",
            "url": "https://www.cdc.gov/nssp/php/about/about-nssp-and-the-biosense-platform.html",
            "type": "surveillance"
        },
        {
            "title": "CDC: Surveillance Resource Center",
            "url": "https://www.cdc.gov/ophdst/data-research/index.html",
            "type": "surveillance"
        },
        {
            "title": "CDC Stacks: National Biosurveillance Strategy",
            "url": "https://stacks.cdc.gov/view/cdc/35002",
            "type": "strategy"
        },
        {
            "title": "CDC Stacks: National Biosurveillance Advisory Report",
            "url": "https://stacks.cdc.gov/view/cdc/12000",
            "type": "strategy"
        }
    ]
}


def get_resources(question: str):
    q = question.lower()
    words = set(re.findall(r"\b[a-z]+\b", q))

    for topic, links in RESOURCE_MAP.items():
        topic_l = topic.lower()

        if " " in topic_l:
            if topic_l in q:
                return links[:3]
        else:
            if topic_l in words:
                return links[:3]

    return []


def get_sensor_db_connection():
    return psycopg2.connect(
        host=SENSOR_DB_HOST,
        port=SENSOR_DB_PORT,
        dbname=SENSOR_DB_NAME,
        user=SENSOR_DB_USER,
        password=SENSOR_DB_PASSWORD,
        cursor_factory=RealDictCursor,
        connect_timeout=10
    )


def fetch_recent_sensor_data(limit=20):
    conn = get_sensor_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    timestamp,
                    dose_rate,
                    count_rate,
                    device_id,
                    location,
                    status,
                    sensor_type,
                    created_at,
                    updated_at
                FROM sensor_readings
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()
    finally:
        conn.close()


def format_sensor_context(rows):
    if not rows:
        return "No recent live CBRN sensor data is available."

    lines = []
    for row in rows:
        location = row.get("location")
        if isinstance(location, dict):
            location_str = json.dumps(location)
        else:
            location_str = str(location)

        lines.append(
            f"Time: {row.get('timestamp')}, "
            f"Device: {row.get('device_id')}, "
            f"Sensor type: {row.get('sensor_type')}, "
            f"Dose rate: {row.get('dose_rate')}, "
            f"Count rate: {row.get('count_rate')}, "
            f"Status: {row.get('status')}, "
            f"Location: {location_str}"
        )

    return "\n".join(lines)


def is_live_sensor_query(question: str) -> bool:
    q = question.lower()

    live_terms = [
        "live sensor", "live sensors",
        "current sensor", "current sensors",
        "sensor reading", "sensor readings",   # 🔴 CRITICAL FIX
        "current reading", "current readings",
        "recent sensor data", "sensor status",
        "latest sensor", "latest readings",
        "latest sensor readings",
        "dose rate", "count rate",
        "radiation level",
        "which device", "device online", "online device",
        "what are the readings", "show readings",
        "sensor information", "sensor values",
        "latest sensor data", "current sensor data",
        "what sensor is online", "which sensor is online",
        "current status of the sensors", "latest live data"
    ]

    if any(term in q for term in live_terms):
        return True

    # 🔴 Stronger fallback logic
    if "sensor" in q and ("reading" in q or "readings" in q or "status" in q or "online" in q):
        return True

    if "device" in q and ("reading" in q or "readings" in q or "status" in q or "online" in q):
        return True

    return False


def is_live_sensor_analysis_query(question: str) -> bool:
    q = question.lower()

    analysis_terms = [
        "analysis", "analyze", "analyse",
        "risk level", "threat level",
        "assessment", "briefing", "report",
        "generate report", "situation report",
        "trend", "trends",
        "anomaly", "anomalies",
        "alert", "alerts",
        "is everything normal",
        "is there any danger",
        "is it safe",
        "what does this mean",
        "detailed analysis",
         "safe", "danger", "issue", "problem",
         "abnormal", "unusual", "spike",
          "concerning", "okay", "normal",
          "what's happening", "status"
    ]

    sensor_terms = [
        "sensor", "sensors",
        "reading", "readings",
        "dose rate", "count rate",
        "device", "online",
        "live data", "current data",
        "radiation level"
    ]

    return any(a in q for a in analysis_terms) and any(s in q for s in sensor_terms)


def build_sensor_analysis(rows):
    if not rows:
        return {
            "summary": "No recent sensor data available.",
            "device": None,
            "latest_dose_rate": None,
            "latest_count_rate": None,
            "status": None,
            "trend": "unknown",
            "risk_level": "unknown",
            "anomaly": False
        }

    latest = rows[0]
    dose_rates = [r["dose_rate"] for r in rows if r.get("dose_rate") is not None]
    count_rates = [r["count_rate"] for r in rows if r.get("count_rate") is not None]

    avg_dose = sum(dose_rates) / len(dose_rates) if dose_rates else None
    avg_count = sum(count_rates) / len(count_rates) if count_rates else None

    trend = "stable"
    if len(dose_rates) >= 2:
        if dose_rates[0] > dose_rates[-1]:
            trend = "increasing"
        elif dose_rates[0] < dose_rates[-1]:
            trend = "decreasing"

    latest_dose = latest.get("dose_rate")
    anomaly = False
    if avg_dose is not None and latest_dose is not None:
        anomaly = latest_dose > avg_dose * 1.5

    risk_level = "low"
    if latest_dose is not None:
        if latest_dose >= 1.0:
            risk_level = "high"
        elif latest_dose >= 0.3:
            risk_level = "moderate"

    return {
        "device": latest.get("device_id"),
        "location": latest.get("location"),
        "status": latest.get("status"),
        "sensor_type": latest.get("sensor_type"),
        "latest_dose_rate": latest_dose,
        "latest_count_rate": latest.get("count_rate"),
        "average_dose_rate": avg_dose,
        "average_count_rate": avg_count,
        "trend": trend,
        "risk_level": risk_level,
        "anomaly": anomaly
    }



app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
INDEX_DIR = BASE_DIR / "rag_store"

INDEX_PATH = INDEX_DIR / "cbrn.index"
DOCS_PATH = INDEX_DIR / "documents.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


SENSOR_DB_HOST = os.getenv("SENSOR_DB_HOST", "192.168.5.125")
SENSOR_DB_PORT = int(os.getenv("SENSOR_DB_PORT", "5435"))
SENSOR_DB_NAME = os.getenv("SENSOR_DB_NAME", "postgres")
SENSOR_DB_USER = os.getenv("SENSOR_DB_USER", "postgres")
SENSOR_DB_PASSWORD = os.getenv("SENSOR_DB_PASSWORD")


TOP_K = 2

index = None
documents = None
embedder = None


def is_greeting(text: str) -> bool:
    q = text.strip().lower()
    return q in {"hi", "hello", "hey", "hei", "hie", "good morning", "good afternoon", "good evening"}


def fallback_response():
    return {
        "answer": "Sorry, I can’t answer that at the moment. Please check again in the next few days as my training and knowledge base continue to improve.",
        "sources": []
    }


def clean_answer(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def finish_cleanly(text: str) -> str:
    text = clean_answer(text)
    last_punct = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    if last_punct != -1:
        return text[:last_punct + 1]
    return text


def is_vague_question(question: str, history=None) -> bool:
    q = question.lower().strip()
    history = history or []

    # If there is prior conversation, allow follow-up style questions through
    if history:
        return False

    # Only truly minimal unclear inputs should be treated as vague
    very_short_unclear = {
        "this", "that", "it", "more", "help", "why", "how", "what"
    }

    vague_phrases = {
        "what about that",
        "what about it",
        "this one",
        "that one"
    }

    if q in very_short_unclear:
        return True

    if q in vague_phrases:
        return True

    return False


def load_rag_assets():
    global index, documents, embedder

    # 👇 prevent re-loading (VERY important for gunicorn)
    if embedder is not None and index is not None and documents is not None:
        return

    from sentence_transformers import SentenceTransformer

    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found: {INDEX_PATH}")

    if not DOCS_PATH.exists():
        raise FileNotFoundError(f"Documents file not found: {DOCS_PATH}")

    print("Loading embedding model...")
    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print("Loading FAISS index...")
    index = faiss.read_index(str(INDEX_PATH))

    print("Loading documents metadata...")
    with open(DOCS_PATH, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"Loaded {len(documents)} chunks.")


if embedder is None or index is None or documents is None:
    print("RAG assets not loaded — loading now...")
    load_rag_assets()


def search_documents(query: str, top_k=TOP_K):
    if not query.strip():
        return []

    query_embedding = embedder.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)

    scores, indices = index.search(query_embedding, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        if idx < 0 or idx >= len(documents):
            print(f"Skipping invalid document index: {idx} (documents length: {len(documents)})")
            continue

        doc = documents[idx]
        results.append({
            "score": float(score),
            "file": doc["file"],
            "text": doc["text"],
            "chunk_index": doc["chunk_index"]
        })

    return results


def rewrite_with_history(question: str, history: list):
    if not history:
        return question

    history_text = "\n".join(
        [f"{m.get('role', 'user')}: {m.get('text', '')}" for m in history[-6:]]
    )

    prompt = f"""
You are helping convert a follow-up question into a fully clear standalone question.

Rules:
- Use conversation history to resolve references like "he", "it", "that", or names
- Make the question explicit and self-contained
- Preserve the user's intent exactly
- Do not introduce new information
- Return ONLY the rewritten question
- If the question is already clear, return it unchanged

Conversation history:
{history_text}

Latest user question:
{question}

Standalone question:
""".strip()

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 60,
                    "stop": ["\n\n\n"]
                }
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        rewritten = clean_answer(data.get("response", "").strip())
        print("Rewritten question:", rewritten if rewritten else question)
        return rewritten if rewritten else question
    except Exception as e:
        print(f"Rewrite error: {e}")
        return question


def clarification_with_ollama(question: str, history: list):
    history_text = "\n".join(
        [f"{m.get('role', 'user')}: {m.get('text', '')}" for m in history[-6:]]
    ) if history else ""

    prompt = f"""
You are Sisiwenyewe, a CBRN intelligence assistant.

LANGUAGE RULE:
- Always respond in English only

The user's latest question is too vague or incomplete.

Ask one short, precise clarifying question that will help you provide an accurate and useful response.

Do not answer the original question.
Do not provide explanations.
Be direct, professional, and concise.

Conversation history:
{history_text}

Latest user question:
{question}

Clarifying question:
""".strip()

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 50
                }
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        answer = finish_cleanly(data.get("response", "").strip())
        return answer if answer else "Could you clarify what specific information you need?"
    except Exception as e:
        print(f"Clarification error: {e}")
        return "Could you clarify what specific information you need?"


def answer_with_ollama(question: str, contexts: list, history: list):
    context_text = "\n\n".join([c["text"] for c in contexts])

    history_text = "\n".join(
        [f"{m.get('role', 'user')}: {m.get('text', '')}" for m in history[-6:]]
    ) if history else ""

    prompt = f"""
You are Sisiwenyewe, a sovereign CBRN intelligence system serving Uganda and the East African region.
CBRN refers to Chemical, Biological, Radiological, and Nuclear threats.

MISSION:
Provide accurate, structured, and operationally useful intelligence to support policymakers, emergency responders, and institutions.

RESPONSE PRINCIPLES:
- Be clear, professional, and concise
- Answer the user’s question directly
- Stay tightly focused on the user’s intent
- Use structured reasoning where appropriate, but keep the final answer concise

LANGUAGE RULE:
- Always respond in English only
- Never respond in Chinese or any other language

CONTEXTUAL ADAPTATION:
- Apply global knowledge to the Ugandan and East African context where relevant
- Do NOT assume specific local facts unless supported by context or widely established knowledge

CRITICAL BEHAVIOUR RULES:
- Use recent conversation history to interpret follow-up questions correctly
- Do not introduce unrelated threats or topics unless explicitly required
- Do not repeat or expose internal context, documents, or retrieval processes

SAFETY AND ACCURACY RULES (STRICT):
- Do NOT guess or speculate
- Do NOT substitute one agent, chemical, or threat for another
- If information is insufficient or unclear, respond with:
  "I do not have sufficient confirmed information to provide a reliable answer. Please clarify or provide more detail."

INTELLIGENCE STANDARD:
- Prioritise correctness over completeness
- Provide confident answers only when supported by reliable knowledge
- Where appropriate, frame responses using established CBRN principles

SYSTEM PROTECTION:
- Do NOT mention model names, AI systems, training data, or internal architecture
- Do NOT say "as an AI model"
- Do NOT disclose how the system works internally

GUIDANCE:
- Use the provided context as the primary source of truth
- If context is incomplete, supplement with reliable general knowledge ONLY if confident
- Do not fabricate or invent details
- If the context represents live sensor data, use it as the primary operational source and do not claim real-time confirmation beyond what the data shows

RESPONSE FORMAT:
- Provide one well-structured paragraph (3–5 sentences)
- Ensure clarity, completeness, and professional tone
- End with a complete and well-formed sentence

Recent conversation:
{history_text}

Question:
{question}

Context:
{context_text}

Answer:
""".strip()

    try:
        print("Calling Ollama with retrieved context...")
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 260
                }
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        answer = finish_cleanly(data.get("response", "").strip())
        print("Ollama returned a response.")
        print("Ollama answer preview:", answer[:300] if answer else "EMPTY")
        return answer if answer else ""
    except Exception as e:
        print(f"Ollama error: {e}")
        return ""


@app.route("/", methods=["GET"])
def home():
    return "Sisiwenyewe backend is running."




def is_cbrn_query(question: str) -> bool:
    q = question.lower()
    words = set(re.findall(r"\b[a-z]+\b", q))

    cbrn_single_terms = {
        "cbrn", "chemical", "biological", "radiological", "nuclear",
        "anthrax", "botulism", "smallpox", "mustard", "cyanide",
        "toxin", "agent", "radiation", "fallout", "ppe",
        "decontamination", "biosurveillance", "hazmat",
        "contamination", "exposure", "decon"
    }

    cbrn_phrases = {
        "mustard gas",
        "nerve agent",
        "blister agent",
        "radiological exposure",
        "nuclear fallout",
        "respiratory protection",
        "emergency response"
    }

    if any(phrase in q for phrase in cbrn_phrases):
        return True

    return any(word in cbrn_single_terms for word in words)


def is_weather_query(question: str) -> bool:
    q = question.lower()
    words = re.findall(r"\b[a-z]+\b", q)

    weather_terms = {
        "weather", "forecast", "temperature", "climate",
        "rain", "rainfall", "raining", "humidity", "wind",
        "storm", "sunny", "cloudy"
    }

    return any(word in weather_terms for word in words)


def get_weather_resources():
    return [
        {
            "title": "Uganda National Meteorological Authority (UNMA)",
            "url": "https://www.unma.go.ug"
        },
        {
            "title": "AccuWeather: Uganda Forecast",
            "url": "https://www.accuweather.com/en/ug/national/weather-forecast"
        },
        {
            "title": "BBC Weather: Uganda",
            "url": "https://www.bbc.com/weather/226074"
        }
    ]




def answer_general(question: str, history: list):
    history_text = "\n".join(
        [f"{m.get('role', 'user')}: {m.get('text', '')}" for m in history[-6:]]
    ) if history else ""

    prompt = f"""
You are Sisiwenyewe, an intelligent assistant.

LANGUAGE RULE:
- Always respond in English only
- Never respond in Chinese or any other language

MISSION:
Provide accurate, clear, and reliable answers to the user's question.

Rules:
- Answer directly using general world knowledge
- For ordinary factual questions, provide the best direct answer you can
- If the question is about a current office-holder, public figure, or recent political situation, answer cautiously and avoid pretending to have live verified data
- If uncertain, say so clearly and briefly
- Do NOT mention AI, models, or internal systems
- Keep the response to 2–4 sentences
- Stay focused on the actual question

CRITICAL FACT RULE:
- If the question is about a specific person and you are not certain, DO NOT guess
- Do NOT fabricate biographies, roles, or affiliations
- Do NOT infer identity from similar names

ACCURACY PRIORITY:
- Prioritise correctness over completeness
- Never invent facts to fill gaps
- Give the best answer you can from general knowledge, while avoiding false certainty for live or changing facts

Conversation:
{history_text}

Question:
{question}

Answer:
""".strip()

    try:
        print("General model URL:", OLLAMA_URL)
        print("General model name:", OLLAMA_MODEL)

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 220
                }
            },
            timeout=60
        )

        print("General model status:", response.status_code)
        print("General model raw response:", response.text[:500])

        response.raise_for_status()
        data = response.json()
        return finish_cleanly(data.get("response", "").strip())

    except Exception as e:
        print(f"General model error: {e}")
        return ""


def is_profile_query(question: str) -> bool:
    q = question.lower()
    profile_terms = [
        "prof stephen",
        "stephen akandwanaho",
        "akandwanaho",
        "who is prof stephen",
        "who is stephen akandwanaho",
        "mugisha stephen",
        "mugisha akandwanaho",
        "prof mugisha akandwanaho",
        "prof mugisha stephen",
         "allan atwine",

        "agaba allan",

        "agaba allan atwine",

        "who is allan atwine",

        "who is agaba allan atwine"
    ]
    return any(term in q for term in profile_terms)


def is_current_office_query(question: str) -> bool:
    q = question.lower()
    office_terms = [
        "president of", "prime minister of", "ceo of",
        "current president", "current prime minister",
        "who leads", "head of state"
    ]
    return any(term in q for term in office_terms)



def search_profile_documents(query: str, top_k=TOP_K):
    if not query.strip():
        return []

    query_embedding = embedder.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)

    profile_docs = []
   

    # collect only internal_profile rows
    for i, doc in enumerate(documents):
        if doc.get("file") == "internal_profile":
            profile_docs.append(doc)
         

    if not profile_docs:
        return []

    # build temporary matrix from the same FAISS-loaded documents order
    # easiest way: re-embed profile texts directly
    profile_texts = [d["text"] for d in profile_docs]
    profile_embeddings = embedder.encode(
        profile_texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)

    scores = np.dot(profile_embeddings, query_embedding[0])

    ranked = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in ranked:
        doc = profile_docs[idx]
        results.append({
            "score": float(scores[idx]),
            "file": doc["file"],
            "text": doc["text"],
            "chunk_index": doc["chunk_index"]
        })

    return results



def search_documents_filtered(query: str, file_filter: str, top_k=TOP_K):
    results = search_documents(query, top_k=top_k * 5)
    filtered = [r for r in results if r["file"] == file_filter]
    return filtered[:top_k]



def sensor_summary_from_rows(rows):
    analysis = build_sensor_analysis(rows)
    location = analysis.get("location")

    if isinstance(location, dict):
        location = location.get("name", json.dumps(location))

    anomaly_text = (
        "An anomaly is indicated and should be reviewed."
        if analysis.get("anomaly")
        else "No anomaly is indicated in the latest sample."
    )

    return (
        f"Latest live sensor readings show device {analysis.get('device')} online at {location}. "
        f"The latest dose rate is {analysis.get('latest_dose_rate')} and the latest count rate is {analysis.get('latest_count_rate')}. "
        f"Across the latest readings, the trend appears {analysis.get('trend')} with a preliminary risk level of {analysis.get('risk_level')}. "
        f"{anomaly_text}"
    )

    
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    question_lower = question.lower()
    history = data.get("history", [])

    print(f"Question received: {question}")

    if not question:
        return jsonify({
            "answer": "Please enter a question.",
            "sources": [],
            "resources": []
        }), 400

    # Protect system identity
    if any(phrase in question_lower for phrase in [
        "what model", "which model", "are you gpt",
        "are you llama", "what ai are you", "who built you",
        "what system are you"
    ]):
        return jsonify({
            "answer": "Sisiwenyewe is a sovereign CBRN intelligence system designed to support policymakers, governments, emergency responders, and military with accurate and context-aware threat intelligence.",
            "sources": [],
            "resources": []
        })

    # Greetings
    if is_greeting(question):
        return jsonify({
            "answer": "Hi. How can I assist today?",
            "sources": [],
            "resources": []
        })

    # Rewrite follow-up questions
    effective_question = rewrite_with_history(question, history)
    print("Effective question:", effective_question)

    sensor_intent_terms = [
        "sensor", "sensors", "radiation", "dose", "dose rate",
         "count rate", "device", "summit view", "reading", "readings",
         "safe", "danger", "normal", "abnormal", "spike", "risk",
         "threat", "status", "online"
]

    if any(term in effective_question.lower() for term in sensor_intent_terms): 
      if not is_live_sensor_query(effective_question) and not is_live_sensor_analysis_query(effective_question):
        effective_question = effective_question + " sensor readings"



        # Live sensor analysis queries
    if is_live_sensor_analysis_query(effective_question):
        print("Live sensor analysis query detected — using sensor database.")

        try:
            rows = fetch_recent_sensor_data(limit=20)
            analysis_context = json.dumps(build_sensor_analysis(rows), indent=2)

            live_context = [{
                "score": 1.0,
                "file": "live_sensor_analysis",
                "text": analysis_context,
                "chunk_index": 0
            }]

            answer = answer_with_ollama(effective_question, live_context, history)

            if not answer:
                answer = sensor_summary_from_rows(rows)

            return jsonify({
                "answer": answer,
                "sources": ["live_sensor_analysis"],
                "resources": []
            })

        except Exception as e:
            print(f"Live sensor analysis DB error: {e}")
            return jsonify({
                "answer": "I could not access live sensor data at the moment. The system is currently operating in advisory mode.",
                "sources": [],
                "resources": []
            })

    # Live sensor queries
    if is_live_sensor_query(effective_question):
        print("Live sensor query detected — using sensor database.")

        try:
            rows = fetch_recent_sensor_data(limit=20)
            sensor_context = format_sensor_context(rows)

            live_context = [{
                "score": 1.0,
                "file": "live_sensor_data",
                "text": sensor_context,
                "chunk_index": 0
            }]

            answer = answer_with_ollama(effective_question, live_context, history)

            if not answer:
                answer = sensor_summary_from_rows(rows)

            return jsonify({
    "answer": answer,
    "sources": ["live_sensor_data"],
    "resources": []
})

           
        except Exception as e:
            print(f"Live sensor DB error: {e}")
            return jsonify({
                "answer": "I could not access live sensor data at the moment. The system is currently operating in advisory mode.",
                "sources": [],
                "resources": []
            })


    # Vague questions
    if is_vague_question(question, history):
        clarification = clarification_with_ollama(question, history)
        return jsonify({
            "answer": clarification,
            "sources": [],
            "resources": []
        })

    # Current office queries
    if is_current_office_query(effective_question):
        answer = answer_general(effective_question, history)

        if not answer:
            return jsonify({
                "answer": "I do not currently have confirmed live information for that office-holder query. Please consult an official or trusted current source.",
                "sources": [],
                "resources": []
            })

        return jsonify({
            "answer": answer,
            "sources": [],
            "resources": []
        })

    # General queries (non-CBRN)
    if not is_cbrn_query(effective_question):
        print("General query detected — using general model.")

        answer = answer_general(effective_question, history)

        if not answer:
            return jsonify({
                "answer": "I do not have sufficient confirmed information to provide a reliable answer.",
                "sources": [],
                "resources": []
            })

        return jsonify({
            "answer": answer,
            "sources": [],
            "resources": []
        })

    # CBRN queries (RAG)
    results = search_documents(effective_question, top_k=TOP_K)

    if not results:
        print("No retrieval results — using fallback.")

        answer = answer_with_ollama(effective_question, [], history)

        if not answer:
            return jsonify({
                "answer": "I do not have sufficient confirmed information to provide a reliable answer.",
                "sources": [],
                "resources": get_resources(question)
            })

        return jsonify({
            "answer": answer,
            "sources": [],
            "resources": get_resources(question)
        })

    top_score = results[0]["score"]
    print(f"Top score: {top_score:.4f}")

    # Weak RAG → fallback to general
    if top_score < 0.20:
        print("Low RAG score — using general model.")

        answer = answer_general(effective_question, history)

        if not answer:
            return jsonify({
                "answer": "I do not have sufficient confirmed information to provide a reliable answer.",
                "sources": [],
                "resources": get_resources(question)
            })

        return jsonify({
            "answer": answer,
            "sources": [],
            "resources": get_resources(question)
        })


# Strong RAG
    # Strong RAG
    answer = answer_with_ollama(effective_question, results, history)

    if not answer:
        answer = answer_general(effective_question, history)

    if not answer:
        return jsonify({
            "answer": "I do not have sufficient confirmed information to provide a reliable answer.",
            "sources": list(dict.fromkeys(r["file"] for r in results)),
            "resources": get_resources(question)
        })

    return jsonify({
        "answer": answer,
        "sources": list(dict.fromkeys(r["file"] for r in results)),
        "resources": get_resources(question)
    })

if __name__ == "__main__":
    print("Loading RAG assets for server startup...")
    load_rag_assets()
    print("RAG assets loaded successfully.")
    app.run(debug=True, host="127.0.0.1", port=5001)