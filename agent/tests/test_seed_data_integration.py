from agent.nodes.code_generator import _DOMAIN_KEYWORDS, detect_domain, get_structured_seed_data


def test_detect_domain_returns_recipe_for_food_text():
    assert detect_domain("I want to build a recipe sharing app with food recommendations") == "recipe"


def test_detect_domain_returns_ecommerce_for_shopping_text():
    assert detect_domain("online shop with product cart and payment gateway") == "ecommerce"


def test_detect_domain_falls_back_to_project_for_unknown_text():
    assert detect_domain("something completely unrelated xyz123") == "project"


def test_get_structured_seed_data_returns_list_of_dicts():
    result = get_structured_seed_data("recipe cooking meal planning app")
    assert isinstance(result, list)
    assert all(isinstance(item, dict) for item in result)


def test_get_structured_seed_data_items_have_id_field():
    result = get_structured_seed_data("product shop with cart and order management")
    for item in result:
        assert "id" in item, f"Missing 'id' field in item: {item}"


def test_domain_detection_is_case_insensitive():
    assert detect_domain("RECIPE FOOD COOK") == "recipe"
    assert detect_domain("Recipe Food Cook") == "recipe"
    assert detect_domain("recipe food cook") == "recipe"


def test_each_domain_keyword_list_is_non_empty():
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        assert len(keywords) > 0, f"Domain '{domain}' has empty keyword list"


def test_structured_seed_data_count_parameter_works():
    for count in [3, 5, 10]:
        result = get_structured_seed_data("analytics dashboard with metrics and charts", count=count)
        assert len(result) == count, f"Expected {count} items, got {len(result)}"


def test_detect_domain_returns_analytics_for_dashboard_text():
    assert detect_domain("dashboard with analytics metrics and data insights") == "analytics"


def test_detect_domain_returns_social_for_social_text():
    assert detect_domain("social feed with posts and community sharing") == "social"


def test_detect_domain_returns_project_for_task_text():
    assert detect_domain("project management with tasks and kanban board") == "project"


def test_get_structured_seed_data_default_count_is_eight():
    result = get_structured_seed_data("cooking recipe app")
    assert len(result) == 8
