"""
Natural-language interface over the Neo4j graph. Converts a plain English
question into a read-only Cypher query using local Ollama (qwen2.5), runs
it, and explains the results in plain English.

Requires: Ollama running locally with qwen2.5 pulled (ollama pull qwen2.5)
Requires: pip install neo4j requests --break-system-packages

Usage:
    python llm_agent.py "Which parts are currently over their usage limit?"
    python llm_agent.py "Show me the replacement chain for engine parts on car 1"
"""
import sys
import json
import re
import requests
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5"

GRAPH_SCHEMA = """
Nodes:
  Team(team_id, name)
  Car(car_id, car_number)
  Driver(name)
  Part(serial_number, part_type, usage_limit, team_id)
  Race(race_number, name, date)
  Event(event_id, event_type[install|remove], reason[scheduled|crash|upgrade], race_number)
  Flag(flag_type[double_install|orphan_remove|over_limit], detail, detected_at)

Relationships:
  (Team)-[:OWNS]->(Car)
  (Car)-[:DRIVEN_BY]->(Driver)
  (Part)-[:INSTALLED_ON]->(Car)          // current install state
  (Part)-[:HAD_EVENT]->(Event)
  (Event)-[:AT_RACE]->(Race)
  (Event)-[:ON_CAR]->(Car)
  (Part)-[:REPLACED_BY]->(Part)          // lineage chain
  (Flag)-[:ABOUT_PART]->(Part)
  (Flag)-[:ABOUT_CAR]->(Car)
"""


def ollama_chat(system: str, user: str) -> str:
    resp = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    })
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def nl_to_cypher(question: str) -> str:
    raw = ollama_chat(
        "You convert natural language questions into a single read-only Cypher "
        "query against this Neo4j graph schema:\n" + GRAPH_SCHEMA +
        "\nRules:\n"
        "- MATCH/RETURN only, no CREATE/MERGE/DELETE/SET.\n"
        "- For any question about usage-limit violations, double installs, or "
        "orphaned records, query the existing :Flag nodes (already computed by "
        "the integrity checker) instead of recalculating from Event/Race data. "
        "e.g. MATCH (f:Flag {flag_type:'over_limit'})-[:ABOUT_PART]->(p:Part), "
        "(f)-[:ABOUT_CAR]->(c:Car) RETURN p.serial_number, c.car_id, f.detail\n"
        "- Never use size((pattern)) — that syntax is deprecated. Use "
        "COUNT { (pattern) } instead if you need a relationship count.\n"
        "Return ONLY the raw Cypher, no markdown fences, no commentary.",
        question,
    )
    cypher = re.sub(r"^```(cypher)?|```$", "", raw, flags=re.MULTILINE).strip()
    forbidden = ("create", "merge", "delete", "set", "remove ")
    if any(kw in cypher.lower() for kw in forbidden):
        raise ValueError(f"Refusing write query: {cypher}")
    return cypher


def run_query(cypher: str):
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database="f1DB") as session:
        rows = [dict(r) for r in session.run(cypher)]
    driver.close()
    return rows


def explain_results(question: str, cypher: str, rows: list) -> str:
    return ollama_chat(
        "You are a data analyst for an F1 team's parts traceability graph. "
        "Given a user's question, the Cypher query that was run, and the "
        "resulting rows, explain the answer in clear plain English. If results "
        "relate to Flag nodes (over_limit, double_install, orphan_remove), call "
        "out the operational/regulatory risk explicitly (e.g. grid penalty).",
        f"Question: {question}\n\nCypher run: {cypher}\n\nResults (JSON): {json.dumps(rows, default=str)}",
    )


def ask(question: str):
    cypher = nl_to_cypher(question)
    rows = run_query(cypher)
    answer = explain_results(question, cypher, rows)
    print(f"\nCypher:\n  {cypher}\n")
    print(f"Answer:\n{answer}\n")
    return answer


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python llm_agent.py "your question here"')
        sys.exit(1)
    ask(" ".join(sys.argv[1:]))