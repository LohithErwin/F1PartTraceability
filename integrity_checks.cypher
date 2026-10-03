// ===== 1. DOUBLE INSTALL =====
// A part currently INSTALLED_ON more than one car at once.
MATCH (p:Part)-[:INSTALLED_ON]->(c:Car)
WITH p, collect(c.car_id) AS cars
WHERE size(cars) > 1
RETURN p.serial_number AS part, cars AS installed_on_cars;

// ===== 2. ORPHAN REMOVE =====
// A 'remove' event for a part that has no earlier 'install' event on that car
// at a lower-or-equal race number.
MATCH (p:Part)-[:HAD_EVENT]->(rem:Event {event_type:'remove'})-[:ON_CAR]->(c:Car)
WHERE NOT EXISTS {
  MATCH (p)-[:HAD_EVENT]->(ins:Event {event_type:'install'})-[:ON_CAR]->(c)
  WHERE ins.race_number <= rem.race_number
}
RETURN p.serial_number AS part, c.car_id AS car, rem.race_number AS remove_race;

// ===== 3. OVER LIMIT (grid penalty risk) =====
// For each part, match consecutive install->remove pairs on the same car and
// compute races used vs its regulation usage_limit.
MATCH (p:Part)-[:HAD_EVENT]->(ins:Event {event_type:'install'})-[:ON_CAR]->(c:Car)
MATCH (p)-[:HAD_EVENT]->(rem:Event {event_type:'remove'})-[:ON_CAR]->(c)
WHERE rem.race_number > ins.race_number
  AND NOT EXISTS {
    MATCH (p)-[:HAD_EVENT]->(mid:Event)-[:ON_CAR]->(c)
    WHERE mid.race_number > ins.race_number AND mid.race_number < rem.race_number
  }
WITH p, c, ins, rem, (rem.race_number - ins.race_number) AS races_used
WHERE races_used > p.usage_limit
RETURN p.serial_number AS part, p.part_type AS type, c.car_id AS car,
       races_used, p.usage_limit AS limit;

// ===== 4. PART LINEAGE (genealogy chain) =====
// Full replacement history for a given part type on a given car, following
// REPLACED_BY across the whole season — this is the traversal a relational
// DB would need a recursive CTE for; here it's a native variable-length path.
MATCH path = (first:Part)-[:REPLACED_BY*0..]->(last:Part)
WHERE first.part_type = $part_type
  AND EXISTS { MATCH (first)-[:INSTALLED_ON|HAD_EVENT]-() }
  AND NOT EXISTS { ()-[:REPLACED_BY]->(first) }   // start of the chain
RETURN [n IN nodes(path) | n.serial_number] AS lineage;
