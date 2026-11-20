MATCH (person:Person)
WHERE toLower(person.city) = toLower($filter_person_city_iexact)
RETURN DISTINCT person
ORDER BY person.name ASC SKIP $skip LIMIT $limit
