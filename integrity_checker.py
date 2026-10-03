"""
Runs the Cypher integrity checks from integrity_checks.cypher, writes each
violation as a :Flag node linked to the offending Part/Car, and prints a
human-readable report — mirrors integrity_flags table in the SQL version.

Usage: python integrity_checks.py
"""
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

DOUBLE_INSTALL = """
MATCH (p:Part)-[:INSTALLED_ON]->(c:Car)
WITH p, collect(c) AS cars
WHERE size(cars) > 1
UNWIND cars AS c
RETURN p.serial_number AS part_sn, c.car_id AS car_id
"""

ORPHAN_REMOVE = """
MATCH (p:Part)-[:HAD_EVENT]->(rem:Event {event_type:'remove'})-[:ON_CAR]->(c:Car)
WHERE NOT EXISTS {
  MATCH (p)-[:HAD_EVENT]->(ins:Event {event_type:'install'})-[:ON_CAR]->(c)
  WHERE ins.race_number <= rem.race_number
}
RETURN p.serial_number AS part_sn, c.car_id AS car_id, rem.race_number AS race
"""

OVER_LIMIT = """
MATCH (p:Part)-[:HAD_EVENT]->(ins:Event {event_type:'install'})-[:ON_CAR]->(c:Car)
MATCH (p)-[:HAD_EVENT]->(rem:Event {event_type:'remove'})-[:ON_CAR]->(c)
WHERE rem.race_number > ins.race_number
  AND NOT EXISTS {
    MATCH (p)-[:HAD_EVENT]->(mid:Event)-[:ON_CAR]->(c)
    WHERE mid.race_number > ins.race_number AND mid.race_number < rem.race_number
  }
WITH p, c, (rem.race_number - ins.race_number) AS races_used
WHERE races_used > p.usage_limit
RETURN p.serial_number AS part_sn, p.part_type AS part_type, c.car_id AS car_id,
       races_used, p.usage_limit AS usage_limit
"""

WRITE_FLAG = """
MATCH (p:Part {serial_number:$sn}), (c:Car {car_id:$car_id})
CREATE (f:Flag {flag_type:$ftype, detail:$detail, detected_at:datetime()})
MERGE (f)-[:ABOUT_PART]->(p)
MERGE (f)-[:ABOUT_CAR]->(c)
"""


def run_checks():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    flags = []
    with driver.session(database="f1DB") as session:
        session.run("MATCH (f:Flag) DETACH DELETE f")

        for row in session.run(DOUBLE_INSTALL):
            detail = f"Part {row['part_sn']} installed on multiple cars simultaneously (car {row['car_id']})"
            flags.append((row['part_sn'], row['car_id'], "double_install", detail))

        for row in session.run(ORPHAN_REMOVE):
            detail = f"Remove event at race {row['race']} has no matching prior install"
            flags.append((row['part_sn'], row['car_id'], "orphan_remove", detail))

        for row in session.run(OVER_LIMIT):
            detail = f"{row['part_type']} used for {row['races_used']} races (limit {row['usage_limit']}) before swap — grid penalty risk"
            flags.append((row['part_sn'], row['car_id'], "over_limit", detail))

        for sn, car_id, ftype, detail in flags:
            session.run(WRITE_FLAG, sn=sn, car_id=car_id, ftype=ftype, detail=detail)

    driver.close()

    print(f"Integrity check complete — {len(flags)} issue(s) found.\n")
    for sn, car_id, ftype, detail in flags:
        print(f"[{ftype.upper()}] part={sn} car={car_id} :: {detail}")


def part_lineage(part_type: str):
    """Walks the REPLACED_BY chain for a given part type, per car."""
    query = """
    MATCH (first:Part {part_type:$ptype})
    WHERE NOT EXISTS { ()-[:REPLACED_BY]->(first) }
    MATCH path = (first)-[:REPLACED_BY*0..]->(last:Part)
    RETURN [n IN nodes(path) | n.serial_number] AS lineage
    """
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database="f1DB") as session:
        for row in session.run(query, ptype=part_type):
            print(" -> ".join(row["lineage"]))
    driver.close()


if __name__ == "__main__":
    run_checks()
    print("\nSample lineage (engine chains):")
    part_lineage("engine")