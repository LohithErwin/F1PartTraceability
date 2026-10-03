"""
Gathers Flag nodes + part-swap counts from the graph and has the local LLM
write a concise executive risk report — same idea as the SQL version.

Requires: Ollama running locally with qwen2.5 pulled.
"""
import json
import requests
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5"


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


def gather_context():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database="f1DB") as session:
        flags = [dict(r) for r in session.run("""
            MATCH (f:Flag)-[:ABOUT_PART]->(p:Part), (f)-[:ABOUT_CAR]->(c:Car),
                  (t:Team)-[:OWNS]->(c)
            RETURN f.flag_type AS flag_type, f.detail AS detail,
                   t.name AS team, c.car_number AS car_number
        """)]

        swap_counts = [dict(r) for r in session.run("""
            MATCH (t:Team)-[:OWNS]->(c:Car)<-[:ON_CAR]-(e:Event {event_type:'install'})
            MATCH (p:Part)-[:HAD_EVENT]->(e)
            RETURN t.name AS team, p.part_type AS part_type, count(*) AS swaps
            ORDER BY swaps DESC
        """)]
    driver.close()
    return {"flags": flags, "part_swap_counts": swap_counts}


def generate_report():
    context = gather_context()
    report = ollama_chat(
        "You are the technical program manager for an F1 team's parts traceability "
        "graph system. Write a concise executive risk report (under 300 words) "
        "covering: 1) which teams/cars have active integrity violations and their "
        "operational risk (e.g. grid penalties), 2) notable part-swap frequency "
        "patterns, 3) recommended next actions. Plain, direct, professional tone.",
        f"Graph data:\n{json.dumps(context, default=str, indent=2)}",
    )
    print(report)
    with open("season_risk_report.md", "w") as f:
        f.write(report)
    return report


if __name__ == "__main__":
    generate_report()