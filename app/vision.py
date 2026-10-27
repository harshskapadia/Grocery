"""Turn a photo of a product into a search term using Claude's vision.

Needs ANTHROPIC_API_KEY (or another Anthropic credential) to be set.
"""
from __future__ import annotations

import base64

import anthropic

PROMPT = (
    "This is a photo of a grocery product. Reply with ONLY a short supermarket "
    "search query for it: brand, product name and size if visible, e.g. "
    "'Pauls Full Cream Milk 2L'. If it's loose produce, just name it, e.g. "
    "'bananas'. If no grocery product is visible, reply exactly: UNKNOWN"
)


class NotAProductError(ValueError):
    pass


def identify_product(image_bytes: bytes, media_type: str) -> str:
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        output_config={"effort": "low"},
        # If a request is ever declined, the API retries it on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )
    if response.stop_reason == "refusal":
        raise NotAProductError("The image could not be processed.")
    text = "".join(b.text for b in response.content if b.type == "text").strip().strip("'\"")
    if not text or text.upper() == "UNKNOWN":
        raise NotAProductError("No grocery product recognised in the photo.")
    return text
