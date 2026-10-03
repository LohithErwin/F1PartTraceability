"""
Two visualizations pulled straight from Neo4j:
  1. lineage_graph.png — the REPLACED_BY chain for one part type on one car,
     drawn with networkx (shows the graph-native traversal visually).
  2. violations_by_team.png — bar chart of Flag counts per team.
"""
import sys
import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")


def lineage_graph(part_type: str):
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database="f1DB") as session:
        rows = session.run("""
            MATCH (a:Part {part_type:$pt})-[:REPLACED_BY]->(b:Part)
            RETURN a.serial_number AS a, b.serial_number AS b
        """, pt=part_type)
        edges = [(r["a"], r["b"]) for r in rows]
    driver.close()

    if not edges:
        print(f"No REPLACED_BY edges found for {part_type}")
        return

    G = nx.DiGraph()
    G.add_edges_from(edges)
    pos = nx.spring_layout(G, k=0.6, seed=42)

    plt.figure(figsize=(12, 8))
    nx.draw(G, pos, with_labels=True, node_size=800, node_color="lightblue",
            font_size=7, arrows=True, arrowsize=12)
    plt.title(f"Part lineage graph: {part_type}")
    plt.tight_layout()
    plt.savefig("lineage_graph.png", dpi=150)
    print("Saved lineage_graph.png")


def violations_by_team():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database="f1DB") as session:
        rows = session.run("""
            MATCH (f:Flag)-[:ABOUT_CAR]->(c:Car)<-[:OWNS]-(t:Team)
            RETURN t.name AS team, count(*) AS n
            ORDER BY n DESC
        """)
        data = [(r["team"], r["n"]) for r in rows]
    driver.close()

    if not data:
        print("No flags to plot.")
        return

    teams, counts = zip(*data)
    plt.figure(figsize=(8, 4))
    plt.bar(teams, counts, color="firebrick")
    plt.ylabel("Integrity flags")
    plt.title("Traceability violations by team")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig("violations_by_team.png", dpi=150)
    print("Saved violations_by_team.png")


if __name__ == "__main__":
    violations_by_team()
    ptype = sys.argv[1] if len(sys.argv) > 1 else "engine"
    lineage_graph(ptype)