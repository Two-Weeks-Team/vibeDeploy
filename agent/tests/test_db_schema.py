from pathlib import Path


def test_schema_sql_exists():
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    assert schema_path.exists()


def test_schema_has_required_tables():
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    content = schema_path.read_text()
    for table in ("sessions", "council_analyses", "cross_examinations", "vibe_scores", "deployments"):
        assert f"CREATE TABLE {table}" in content


def test_schema_has_foreign_keys():
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    content = schema_path.read_text()
    assert content.count("REFERENCES sessions(id)") == 4


def test_schema_has_indexes():
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    content = schema_path.read_text()
    assert "CREATE INDEX" in content or "CREATE UNIQUE INDEX" in content
