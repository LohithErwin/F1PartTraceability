// Run once against the database (cypher-shell or Neo4j Browser)

CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.team_id IS UNIQUE;
CREATE CONSTRAINT car_id IF NOT EXISTS FOR (c:Car) REQUIRE c.car_id IS UNIQUE;
CREATE CONSTRAINT driver_id IF NOT EXISTS FOR (d:Driver) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT part_serial IF NOT EXISTS FOR (p:Part) REQUIRE p.serial_number IS UNIQUE;
CREATE CONSTRAINT race_number IF NOT EXISTS FOR (r:Race) REQUIRE r.race_number IS UNIQUE;
CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE;

CREATE INDEX part_type_idx IF NOT EXISTS FOR (p:Part) ON (p.part_type);
CREATE INDEX event_race_idx IF NOT EXISTS FOR (e:Event) ON (e.race_number);
CREATE INDEX event_type_idx IF NOT EXISTS FOR (e:Event) ON (e.event_type);
