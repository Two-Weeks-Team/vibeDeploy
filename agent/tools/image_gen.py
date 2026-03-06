import os

import httpx

from ..llm import DO_INFERENCE_BASE_URL, MODEL_CONFIG


async def generate_app_logo(name: str, description: str) -> dict:
    return await _generate_image(
        prompt=(
            f"Minimal, modern app logo for '{name}': {description}. "
            f"Clean vector style, suitable for app icon. "
            f"Single icon on transparent background, no text."
        ),
        size="1024x1024",
        purpose="logo",
    )


async def generate_ui_mockup(app_description: str) -> dict:
    return await _generate_image(
        prompt=(
            f"Clean UI mockup screenshot of a web application: {app_description}. "
            f"Modern design, dark theme, minimal layout. "
            f"Show the main screen with realistic placeholder content."
        ),
        size="1792x1024",
        purpose="mockup",
    )


async def generate_placeholder_image(context: str) -> dict:
    return await _generate_image(
        prompt=f"Simple placeholder illustration for: {context}. Minimal, modern style.",
        size="1024x1024",
        purpose="placeholder",
    )


async def _generate_image(
    prompt: str,
    size: str = "1024x1024",
    purpose: str = "image",
) -> dict:
    api_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY")
    if not api_key:
        return {"image_url": "", "error": "DIGITALOCEAN_INFERENCE_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{DO_INFERENCE_BASE_URL}/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL_CONFIG["image"],
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                },
            )
            response.raise_for_status()
            data = response.json()

            image_data = data.get("data", [{}])[0]
            image_url = image_data.get("url", "")
            b64_data = image_data.get("b64_json", "")

            return {
                "image_url": image_url,
                "has_b64": bool(b64_data),
                "purpose": purpose,
                "prompt_used": prompt[:200],
            }

    except httpx.HTTPStatusError as e:
        return {"image_url": "", "error": f"HTTP {e.response.status_code}"}
    except httpx.TimeoutException:
        return {"image_url": "", "error": "Image generation timed out"}
    except Exception as e:
        return {"image_url": "", "error": str(e)[:200]}
