import base64
import json
import os

import anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

MEDIA_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "heic": "image/heic",
}

PROMPT = """Look at this photo and write an Instagram post for it.
Respond with ONLY valid JSON in this exact shape, no other text:
{"caption": "the caption text, no hashtags in it", "hashtags": ["tag1", "tag2", ...]}

Keep the caption short and natural, 1-3 sentences. Give 6-10 relevant hashtags,
without the # symbol."""


def generate_caption(image_bytes, extension):
    client = anthropic.Anthropic()
    media_type = MEDIA_TYPES.get(extension.lower(), "image/jpeg")
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    message = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": encoded},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )

    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text

    data = json.loads(text)
    hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in data["hashtags"])
    return f"{data['caption']}\n\n{hashtags}"
