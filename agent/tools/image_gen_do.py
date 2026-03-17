import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

DO_INFERENCE_IMAGE_ENDPOINT = "https://inference.do-ai.run/v1/images/generations"
IMAGE_MODEL = "gpt-image-1"


class DOImageGenerator:
    def __init__(self) -> None:
        self._api_key: str | None = os.getenv("DIGITALOCEAN_INFERENCE_KEY")
        self._endpoint: str = DO_INFERENCE_IMAGE_ENDPOINT

    async def generate_og_image(self, app_name: str, description: str) -> bytes | None:
        prompt = (
            f"Create a modern, clean OG image for a web app called '{app_name}'. "
            f"{description}. Style: minimal, tech, gradient background."
        )
        return await self._generate(prompt)

    async def generate_logo(self, app_name: str) -> bytes | None:
        prompt = (
            f"Create a simple, modern logo icon for a web app called '{app_name}'. "
            "Style: minimal, vector, clean lines, suitable for app icon."
        )
        return await self._generate(prompt)

    async def _generate(self, prompt: str) -> bytes | None:
        if not self._api_key:
            logger.warning("DIGITALOCEAN_INFERENCE_KEY is not set; skipping image generation")
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self._endpoint,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": IMAGE_MODEL,
                        "prompt": prompt,
                        "response_format": "b64_json",
                        "n": 1,
                    },
                )
                response.raise_for_status()
                data = response.json()
                b64 = data["data"][0]["b64_json"]
                return base64.b64decode(b64)

        except httpx.HTTPStatusError as exc:
            logger.warning("DO Inference image API error: HTTP %s", exc.response.status_code)
            return None
        except httpx.TimeoutException:
            logger.warning("DO Inference image API request timed out")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("DO Inference image generation failed: %s", exc)
            return None
