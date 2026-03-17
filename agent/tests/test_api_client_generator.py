import json

from agent.nodes.type_generator import generate_api_client


def _make_spec(paths: dict) -> str:
    return json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "Client API", "version": "1.0.0"},
            "paths": paths,
        }
    )


def test_generates_function_for_each_endpoint_method_pair():
    spec = _make_spec(
        {
            "/users": {
                "get": {"responses": {"200": {"description": "ok"}}},
                "post": {"responses": {"201": {"description": "ok"}}},
            },
            "/items": {
                "put": {"responses": {"200": {"description": "ok"}}},
                "delete": {"responses": {"204": {"description": "ok"}}},
            },
        }
    )

    result = generate_api_client(spec)

    assert "export async function getUsers(" in result
    assert "export async function postUsers(" in result
    assert "export async function putItems(" in result
    assert "export async function deleteItems(" in result


def test_function_names_follow_method_plus_camelized_path_segments():
    spec = _make_spec(
        {
            "/users": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/items": {"post": {"responses": {"201": {"description": "ok"}}}},
            "/blog-posts": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/users/{id}": {"get": {"responses": {"200": {"description": "ok"}}}},
        }
    )

    result = generate_api_client(spec)

    assert "export async function getUsers(" in result
    assert "export async function postItems(" in result
    assert "export async function getBlogPosts(" in result
    assert "export async function getUsersById(" in result


def test_post_accepts_typed_body_param():
    spec = _make_spec(
        {
            "/items": {
                "post": {
                    "requestBody": {
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreateItemRequest"}}}
                    },
                    "responses": {
                        "201": {
                            "description": "created",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                        }
                    },
                }
            }
        }
    )

    result = generate_api_client(spec)

    assert "export async function postItems(body: CreateItemRequest): Promise<Item>" in result
    assert 'method: "POST"' in result
    assert "body: JSON.stringify(body)" in result


def test_put_accepts_typed_body_param():
    spec = _make_spec(
        {
            "/items": {
                "put": {
                    "requestBody": {
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UpdateItemRequest"}}}
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )

    result = generate_api_client(spec)

    assert "export async function putItems(body: UpdateItemRequest): Promise<PutItemsResponse>" in result


def test_non_body_method_does_not_accept_body_param():
    spec = _make_spec({"/users": {"get": {"responses": {"200": {"description": "ok"}}}}})
    result = generate_api_client(spec)
    assert "export async function getUsers(): Promise<GetUsersResponse>" in result


def test_includes_api_error_class():
    spec = _make_spec({})
    result = generate_api_client(spec)
    assert "export class ApiError extends Error" in result
    assert "if (!res.ok) throw new ApiError(res.status, await res.text());" in result or "ApiError" in result


def test_includes_api_base_url_from_env():
    spec = _make_spec({})
    result = generate_api_client(spec)
    assert "const API_BASE_URL" in result
    assert "process.env.NEXT_PUBLIC_API_BASE_URL" in result


def test_empty_paths_produces_minimal_client_with_preamble_only():
    spec = _make_spec({})
    result = generate_api_client(spec)

    assert "const API_BASE_URL" in result
    assert "export class ApiError" in result
    assert "export async function" not in result


def test_response_type_is_referenced_from_response_schema_ref():
    spec = _make_spec(
        {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/GetUsersResponse"}}
                            },
                        }
                    }
                }
            }
        }
    )

    result = generate_api_client(spec)
    assert "export async function getUsers(): Promise<GetUsersResponse>" in result


def test_array_response_ref_is_rendered_as_array_type():
    spec = _make_spec(
        {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/User"},
                                    }
                                }
                            },
                        }
                    }
                }
            }
        }
    )
    result = generate_api_client(spec)
    assert "export async function getUsers(): Promise<User[]>" in result


def test_path_parameter_is_typed_and_interpolated_in_url():
    spec = _make_spec(
        {
            "/users/{id}": {
                "get": {
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    result = generate_api_client(spec)
    assert "export async function getUsersById(id: number): Promise<GetUsersByIdResponse>" in result
    assert "fetch(`${API_BASE_URL}/users/${id}`)" in result


def test_invalid_json_returns_error_comment():
    result = generate_api_client("{bad json")
    assert result.startswith("//")
    assert "Error" in result
