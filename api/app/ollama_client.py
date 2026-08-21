import os
import json
import datetime as dt
from zoneinfo import ZoneInfo

import httpx

from .catalog import VALID_TYPES, PAYMENT_METHODS

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Riyadh")
CURRENCY = os.environ.get("DEFAULT_CURRENCY", "SAR")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "60"))


class ParseError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _categories_prompt_block(categories: list[tuple[str, str, str]]) -> str:
    by_cat: dict[str, list[str]] = {}
    cat_type: dict[str, str] = {}
    for t, c, s in categories:
        by_cat.setdefault(c, []).append(s)
        cat_type[c] = t
    lines = [f"- [{cat_type[c]}] {c}: " + ", ".join(subs) for c, subs in by_cat.items()]
    return "\n".join(lines)


def _system_prompt(categories: list[tuple[str, str, str]]) -> str:
    now = dt.datetime.now(ZoneInfo(TIMEZONE))
    return f"""You are a strict JSON API. You convert a short message from a family member into
budget transactions. You must respond with ONLY valid JSON, no prose, no markdown fences.

Today's date is {now.strftime('%Y-%m-%d')} ({now.strftime('%A')}). Currency is {CURRENCY} unless stated otherwise.

Respond with exactly this JSON shape:
{{
  "transactions": [
    {{
      "date": "YYYY-MM-DD",
      "type": "Income" | "Expense" | "Savings",
      "category": "<one of the categories below, exact spelling>",
      "subcategory": "<one of that category's subcategories below, exact spelling>",
      "description": "short free text",
      "amount": <positive number>,
      "payment_method": "" | one of {PAYMENT_METHODS}
    }}
  ],
  "clarification_needed": "" or a short question if something essential (amount, or a sensible category) is missing
}}

If the message describes more than one transaction, include multiple entries. If you cannot
confidently map it to a category below, or there's no amount, leave "transactions" empty and
fill "clarification_needed" instead of guessing. If nothing more specific fits but you ARE
confident about the type (Income/Expense/Savings), use category "Miscellaneous" with
subcategory "Other" (for Expense) as the catch-all — never put a Type value (Income/Expense/
Savings) into the "category" field, and never put a Category name into the "subcategory" field.

Valid categories and subcategories (use EXACT spelling):
{_categories_prompt_block(categories)}"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()


def _call_ollama(system_prompt: str, user_text: str) -> dict:
    try:
        resp = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "format": "json",
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise ParseError(f"Couldn't reach the AI model (Ollama) — {e}")

    data = resp.json()
    content = data.get("message", {}).get("content", "")
    try:
        return json.loads(_strip_code_fence(content))
    except json.JSONDecodeError:
        raise ParseError("The AI model returned something that wasn't valid JSON. Try rephrasing.")


def _validate(parsed: dict, categories: list[tuple[str, str, str]]) -> list[dict]:
    valid_pairs = {(c, s) for _, c, s in categories}
    valid_categories = {c for _, c, _ in categories}
    subs_by_category: dict[str, list[str]] = {}
    type_by_category: dict[str, str] = {}
    for t, c, s in categories:
        subs_by_category.setdefault(c, []).append(s)
        type_by_category[c] = t

    if parsed.get("clarification_needed"):
        raise ParseError(parsed["clarification_needed"])

    txns = parsed.get("transactions") or []
    if not txns:
        raise ParseError("I didn't find a transaction in that message. Try including an amount, e.g. '45 SAR groceries'.")

    clean = []
    for t in txns:
        try:
            cat, sub = t["category"], t["subcategory"]
            ttype = t["type"]
            amount = float(t["amount"])
        except (KeyError, TypeError, ValueError):
            raise ParseError("The AI model's answer was missing a required field. Try rephrasing.")

        if (cat, sub) not in valid_pairs:
            # Common small-model slip: it shifts the hierarchy up one level —
            # e.g. category="Expense" (that's actually a Type) paired with
            # subcategory="Miscellaneous" (that's actually a Category). Detect
            # that specific shape and auto-correct rather than rejecting an
            # answer that was actually clear about what it meant.
            if cat in VALID_TYPES and sub in valid_categories:
                corrected_category = sub
                subs = subs_by_category[corrected_category]
                corrected_sub = "Other" if "Other" in subs else subs[0]
                cat, sub = corrected_category, corrected_sub
                ttype = type_by_category[corrected_category]
            else:
                raise ParseError(f"'{cat} / {sub}' isn't one of our categories. Send /categories to see the full list.")

        if ttype not in VALID_TYPES:
            raise ParseError(f"'{ttype}' isn't a valid type.")
        if amount <= 0:
            raise ParseError("Amount must be greater than zero.")

        clean.append({
            "date": t.get("date") or dt.date.today().isoformat(),
            "type": ttype,
            "category": cat,
            "subcategory": sub,
            "description": t.get("description", "") or "",
            "amount": round(amount, 2),
            "payment_method": t.get("payment_method", "") or "",
            "notes": "",
        })
    return clean


def parse_message(text: str, categories: list[tuple[str, str, str]]) -> list[dict]:
    """Parse free text into validated transaction dicts using the local Ollama model.
    Retries once with a corrective nudge if the first attempt fails validation."""
    system_prompt = _system_prompt(categories)

    try:
        parsed = _call_ollama(system_prompt, text)
        return _validate(parsed, categories)
    except ParseError as first_error:
        # one retry, telling the model exactly what went wrong
        nudge = (
            f"{text}\n\n(Your previous answer was invalid: {first_error.message} "
            f"Respond again with ONLY the JSON shape described, using exact category/subcategory spelling.)"
        )
        parsed = _call_ollama(system_prompt, nudge)
        return _validate(parsed, categories)