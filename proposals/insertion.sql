INSERT INTO forms VALUES (,,,,,,,,,,,,,,,,,,,,);

String.Format(
    "INSERT INTO forms VALUES ({0},{1},{2},...,,,,,,,,,,,,,,,,,);",
    body.project_id,
    body.project_title,
    body.deadline,
    ...
)