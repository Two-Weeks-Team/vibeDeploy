import json

from agent.nodes.seed_data import DOMAIN_GENERATORS, generate_seed_data, to_typescript_const

_ALL_DOMAINS = ["recipe", "project", "analytics", "social", "ecommerce"]


def test_all_five_domains_are_registered():
    assert set(DOMAIN_GENERATORS.keys()) == set(_ALL_DOMAINS)


def test_each_domain_generates_at_least_five_items():
    for domain in _ALL_DOMAINS:
        data = generate_seed_data(domain, count=5)
        assert len(data) >= 5, f"{domain} returned {len(data)} items"


def test_each_domain_generates_valid_json():
    for domain in _ALL_DOMAINS:
        data = generate_seed_data(domain, count=5)
        serialized = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(serialized)
        assert len(parsed) == 5


def test_no_lorem_ipsum_or_sample():
    forbidden = ["lorem ipsum", "sample item", "placeholder", "test data"]
    for domain in _ALL_DOMAINS:
        data = generate_seed_data(domain, count=10)
        text = json.dumps(data, ensure_ascii=False).lower()
        for word in forbidden:
            assert word not in text, f"'{word}' found in {domain} seed data"


def test_each_item_has_id_field():
    for domain in _ALL_DOMAINS:
        data = generate_seed_data(domain, count=5)
        for item in data:
            assert "id" in item, f"Missing 'id' in {domain} item"


def test_unknown_domain_falls_back_to_project():
    data = generate_seed_data("nonexistent", count=3)
    assert len(data) == 3
    assert "task" in data[0]


def test_to_typescript_const_format():
    data = [{"id": "1", "name": "Test"}]
    ts = to_typescript_const(data, "testData")
    assert ts.startswith("export const testData = ")
    assert ts.endswith(" as const;\n")
    assert '"id": "1"' in ts


def test_to_typescript_const_preserves_unicode():
    data = [{"id": "1", "name": "한글 데이터"}]
    ts = to_typescript_const(data, "koreanData")
    assert "한글 데이터" in ts


def test_generate_seed_data_custom_count():
    data = generate_seed_data("recipe", count=15)
    assert len(data) == 15


def test_recipe_domain_has_expected_fields():
    data = generate_seed_data("recipe", count=1)
    item = data[0]
    assert "name" in item
    assert "difficulty" in item
    assert "time" in item


def test_ecommerce_domain_has_price_as_int():
    data = generate_seed_data("ecommerce", count=1)
    assert isinstance(data[0]["price"], int)
