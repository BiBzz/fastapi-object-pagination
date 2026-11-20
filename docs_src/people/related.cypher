MATCH (person:Person)
MATCH (person:Person)-[:WORKS_FOR]-(company:Company)
WHERE toLower(company.name) = toLower($filter_company_name_iexact)
RETURN DISTINCT person
ORDER BY person.name ASC SKIP $skip LIMIT $limit

MATCH (person:Person)
MATCH (person:Person)-[:WORKS_FOR]-(company:Company)
WHERE toLower(company.name) = toLower($filter_company_name_iexact)
RETURN COUNT(DISTINCT person)
