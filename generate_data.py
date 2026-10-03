"""
Builds the same synthetic F1 season as the SQL version, but directly as a
Neo4j graph: Team-OWNS->Car-DRIVEN_BY->Driver, Part-HAD_EVENT->Event-AT_RACE->Race,
Event-ON_CAR->Car, Part-INSTALLED_ON->Car (current state), Part-REPLACED_BY->Part
(lineage chain). Includes two deliberately broken records so the integrity
queries have real violations to catch.

Requires: pip install neo4j --break-system-packages
Requires: a running Neo4j instance (see README for Docker command).
"""
import random
from datetime import date, timedelta
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")   # match your local Neo4j instance

random.seed(42)

TEAMS = ["Red Falcon", "Silver Arrow", "Apex Racing", "Vortex GP", "Titan Motorsport"]
PART_TYPES = {
    "engine": 4, "gearbox": 6, "turbo": 4, "ers": 2,
    "chassis": 22, "front_wing": 3, "rear_wing": 3,
}
N_RACES = 22


def run(tx, query, **params):
    tx.run(query, **params)


def seed_teams_cars_races(session):
    for i, name in enumerate(TEAMS, start=1):
        session.execute_write(run,
            "MERGE (t:Team {team_id:$id}) SET t.name=$name", id=i, name=name)
        for car_num in (1, 2):
            car_id = (i - 1) * 2 + car_num
            driver = f"{name} Driver {car_num}"
            session.execute_write(run, """
                MATCH (t:Team {team_id:$tid})
                MERGE (c:Car {car_id:$cid}) SET c.car_number=$num
                MERGE (d:Driver {name:$driver})
                MERGE (t)-[:OWNS]->(c)
                MERGE (c)-[:DRIVEN_BY]->(d)
            """, tid=i, cid=car_id, num=car_num, driver=driver)

    start = date(2026, 3, 1)
    for r in range(1, N_RACES + 1):
        session.execute_write(run, """
            MERGE (race:Race {race_number:$r})
            SET race.name=$name, race.date=$d
        """, r=r, name=f"Round {r}", d=str(start + timedelta(days=14 * (r - 1))))


def new_part(session, team_id, part_type, seq):
    sn = f"{part_type[:3].upper()}-T{team_id}-{seq:03d}"
    session.execute_write(run, """
        CREATE (p:Part {serial_number:$sn, part_type:$pt, usage_limit:$lim, team_id:$tid})
    """, sn=sn, pt=part_type, lim=PART_TYPES[part_type], tid=team_id)
    return sn


_event_counter = 0

def log_event(session, serial, car_id, event_type, reason, race_number):
    global _event_counter
    _event_counter += 1
    session.execute_write(run, """
        MATCH (p:Part {serial_number:$sn}), (c:Car {car_id:$cid}), (r:Race {race_number:$race})
        CREATE (e:Event {event_id:$eid, event_type:$etype, reason:$reason, race_number:$race})
        MERGE (p)-[:HAD_EVENT]->(e)
        MERGE (e)-[:AT_RACE]->(r)
        MERGE (e)-[:ON_CAR]->(c)
    """, sn=serial, cid=car_id, race=race_number, eid=_event_counter,
         etype=event_type, reason=reason)

    if event_type == "install":
        session.execute_write(run, """
            MATCH (p:Part {serial_number:$sn}), (c:Car {car_id:$cid})
            MERGE (p)-[:INSTALLED_ON]->(c)
        """, sn=serial, cid=car_id)
    else:
        session.execute_write(run, """
            MATCH (p:Part {serial_number:$sn})-[rel:INSTALLED_ON]->(:Car {car_id:$cid})
            DELETE rel
        """, sn=serial, cid=car_id)


def link_replacement(session, old_serial, new_serial):
    session.execute_write(run, """
        MATCH (old:Part {serial_number:$old}), (new:Part {serial_number:$new})
        MERGE (old)-[:REPLACED_BY]->(new)
    """, old=old_serial, new=new_serial)


def generate_events(session):
    part_seq = {}
    for team_id in range(1, len(TEAMS) + 1):
        for car_num in (1, 2):
            car_id = (team_id - 1) * 2 + car_num
            current = {}
            races_on_current = {}

            for race in range(1, N_RACES + 1):
                for ptype, limit in PART_TYPES.items():
                    if ptype not in current:
                        part_seq[(team_id, ptype)] = part_seq.get((team_id, ptype), 0) + 1
                        sn = new_part(session, team_id, ptype, part_seq[(team_id, ptype)])
                        log_event(session, sn, car_id, "install", "scheduled", race)
                        current[ptype] = sn
                        races_on_current[ptype] = 1
                        continue

                    races_on_current[ptype] += 1
                    crash = random.random() < 0.04
                    due = races_on_current[ptype] >= limit and random.random() < 0.85

                    if crash or due:
                        reason = "crash" if crash else "scheduled"
                        old_sn = current[ptype]
                        log_event(session, old_sn, car_id, "remove", reason, race)

                        part_seq[(team_id, ptype)] = part_seq.get((team_id, ptype), 0) + 1
                        new_sn = new_part(session, team_id, ptype, part_seq[(team_id, ptype)])
                        log_event(session, new_sn, car_id, "install", reason, race)
                        link_replacement(session, old_sn, new_sn)

                        current[ptype] = new_sn
                        races_on_current[ptype] = 1


def inject_violations(session):
    """Deliberately broken records for the integrity checker to catch."""
    # Orphan remove: remove event with no prior install
    session.execute_write(run, """
        CREATE (p:Part {serial_number:'GHOST-001', part_type:'engine', usage_limit:4, team_id:1})
        WITH p
        MATCH (c:Car {car_id:1}), (r:Race {race_number:5})
        CREATE (e:Event {event_id:99001, event_type:'remove', reason:'scheduled', race_number:5})
        MERGE (p)-[:HAD_EVENT]->(e)
        MERGE (e)-[:AT_RACE]->(r)
        MERGE (e)-[:ON_CAR]->(c)
    """)

    # Double install: existing part installed on a second car without removal
    session.execute_write(run, """
        MATCH (p:Part)-[:INSTALLED_ON]->(c1:Car)
        WITH p, c1 LIMIT 1
        MATCH (c2:Car {car_id:3})
        WHERE c2.car_id <> c1.car_id
        MATCH (r:Race {race_number:3})
        CREATE (e:Event {event_id:99002, event_type:'install', reason:'scheduled', race_number:3})
        MERGE (p)-[:HAD_EVENT]->(e)
        MERGE (e)-[:AT_RACE]->(r)
        MERGE (e)-[:ON_CAR]->(c2)
        MERGE (p)-[:INSTALLED_ON]->(c2)
    """)


if __name__ == "__main__":
    print("hello world")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database="f1DB") as session:
        session.execute_write(run, "MATCH (n) DETACH DELETE n")  # clean slate
        seed_teams_cars_races(session)
        generate_events(session)
        inject_violations(session)
    driver.close()
    print("Season graph generated in Neo4j.")