import base64
import json
import os

import anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")


def _image_block(image_bytes):
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded}}


def _parse_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    return json.loads(text)


CAPTION_PROMPT = """Look at the attached photo(s) — they're all going in the same Instagram post.
Write ONE short, casual, catchy caption for the whole post: under 12 words, no corporate
or "AI-sounding" tone, sounds like a real person casually captioning their own photo.
Respond with ONLY valid JSON in this exact shape, no other text:
{"caption": "the caption text, no hashtags in it", "hashtags": ["tag1", "tag2", ...]}
Give 6-10 relevant hashtags, without the # symbol."""


def generate_caption(images):
    """images: list of JPEG bytes, all belonging to the same post."""
    client = anthropic.Anthropic()
    content = [_image_block(image_bytes) for image_bytes in images]
    content.append({"type": "text", "text": CAPTION_PROMPT})

    message = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": content}],
    )

    data = _parse_json_response(message.content[0].text)
    hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in data["hashtags"])
    return f"{data['caption']}\n\n{hashtags}"


CATEGORY_PROMPT = """Look at this photo and classify it for organizing an Instagram posting queue.
Respond with ONLY valid JSON in this exact shape, no other text:
{"category": "short lowercase category, e.g. travel, fashion, food, lifestyle, fitness",
 "location": "specific place name if identifiable, e.g. Kenya, Paris, else null",
 "has_person": true or false}"""


def categorize_photo(image_bytes):
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [_image_block(image_bytes), {"type": "text", "text": CATEGORY_PROMPT}],
        }],
    )
    return _parse_json_response(message.content[0].text)
