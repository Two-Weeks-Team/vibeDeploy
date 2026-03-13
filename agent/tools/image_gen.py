import asyncio
import os

import httpx
from gradient_adk.tracing import trace_tool

from ..llm import DO_INFERENCE_BASE_URL, MODEL_CONFIG

FAL_INVOKE_URL = f"{DO_INFERENCE_BASE_URL}/async-invoke"
FAL_POLL_INTERVAL = 2.0
FAL_MAX_WAIT = 60.0

FAL_SIZE_MAP = {
    "1024x1024": "square",
    "1792x1024": "landscape_16_9",
    "1024x1792": "portrait_16_9",
}


@trace_tool("generate_app_logo")
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


@trace_tool("generate_ui_mockup")
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


@trace_tool("generate_placeholder_image")
async def generate_placeholder_image(context: str) -> dict:
    return await _generate_image(
        prompt=f"Simple placeholder illustration for: {context}. Minimal, modern style.",
        size="1024x1024",
        purpose="placeholder",
    )


@trace_tool("image_generation_request")
async def _generate_image(
    prompt: str,
    size: str = "1024x1024",
    purpose: str = "image",
) -> dict:
    api_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("DIGITALOCEAN_INFERENCE_KEY")
    if not api_key:
        return {"image_url": "", "error": "GRADIENT_MODEL_ACCESS_KEY not set"}

    image_size = FAL_SIZE_MAP.get(size, "square")
    model_id = MODEL_CONFIG["image"]

    try:
        async with httpx.AsyncClient(timeout=FAL_MAX_WAIT + 10) as client:
            invoke_resp = await client.post(
                FAL_INVOKE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model_id": model_id,
                    "input": {"prompt": prompt, "image_size": image_size},
                },
            )
            invoke_resp.raise_for_status()
            invoke_data = invoke_resp.json()
            request_id = invoke_data["request_id"]

            elapsed = 0.0
            while elapsed < FAL_MAX_WAIT:
                await asyncio.sleep(FAL_POLL_INTERVAL)
                elapsed += FAL_POLL_INTERVAL

                status_resp = await client.get(
                    f"{FAL_INVOKE_URL}/{request_id}/status",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()

                if status_data.get("error"):
                    return {"image_url": "", "error": status_data["error"]}

                if status_data["status"] == "COMPLETED":
                    images = status_data.get("output", {}).get("images", [])
                    image_url = images[0]["url"] if images else ""
                    return {
                        "image_url": image_url,
                        "purpose": purpose,
                        "model": model_id,
                        "prompt_used": prompt[:200],
                    }

            return {"image_url": "", "error": f"Timed out after {FAL_MAX_WAIT}s"}

    except httpx.HTTPStatusError as e:
        return {"image_url": "", "error": f"HTTP {e.response.status_code}"}
    except httpx.TimeoutException:
        return {"image_url": "", "error": "Image generation timed out"}
    except Exception as e:
        return {"image_url": "", "error": str(e)[:200]}
