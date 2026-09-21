"""L0 deterministic fast path for unambiguous canonical commands.

Parses a small grammar of smart-home commands directly into a Command
without invoking any model. Anything that does not match the full grammar
returns None so L1 (the decision model) handles it.

Safety comes from three properties: full-string match only, a closed
target vocabulary, and structural validation against TARGETS (the action
must be supported by the resolved target, values must be in range).
"""

from __future__ import annotations

import re

from .const import RESTRICTED_ACTIONS
from .router import _NUMBER, COLORS, TARGETS, Command, normalized_text

_POLITE = re.compile(r"^(?:please[,\s]+|hey jarvis[,\s]+)+")
_WS = re.compile(r"\s+")
_END_PUNCT = re.compile(r"[.!?]+$")
_COMPOUND = re.compile(r"[,;]|\band\b|\bthen\b|\bwhile\b")

_AREA = r"(?:kitchen|living room|bedroom|downstairs|govee)"
_ROOM = r"(?:kitchen|living room|bedroom|downstairs)"
_LIGHT = rf"(?:the\s+)?(?:all\s+the\s+)?(?:{_AREA})\s+lights?"
_WIRED = r"(?:the\s+)?stairs\s+lights?"
_SIGN = r"(?:the\s+)?good\s+vibes\s+sign"
_LAMP = r"(?:the\s+)?kitchen\s+mushroom\s+lamp"
_PLUG = r"(?:the\s+)?bedroom\s+(?:mushroom\s+plug|window\s+plug)"
_THERMO = r"(?:the\s+)?(?:living\s+room\s+)?thermostat"
_TEMP_WORD = r"(?:the\s+)?living\s+room\s+temperature"
_MEDIA = r"(?:the\s+)?(?:satellite\s+(?:media\s+player|speaker)|music\s+on\s+the\s+satellite\s+speaker)"
_MOVIE = r"movie\s+mode"

_ANY_TARGET = rf"(?:{_LIGHT}|{_WIRED}|{_SIGN}|{_LAMP}|{_PLUG}|{_THERMO}|{_TEMP_WORD}|{_MEDIA}|{_MOVIE})"
_LIGHT_TARGET = rf"(?:{_LIGHT}|{_WIRED}|{_SIGN}|{_LAMP}|{_PLUG})"

_ON_OFF = r"(?:turn|switch)"
_COLOR_WORDS = sorted(COLORS, key=len, reverse=True)
_COLOR = "(?:" + "|".join(c.replace("_", r"\s+") for c in _COLOR_WORDS) + ")"
_NUM = r"(-?\d+(?:\.\d+)?)"

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"{_ON_OFF}\s+(on|off)\s+({_ANY_TARGET})"), "onoff_lead"),
    (re.compile(rf"{_ON_OFF}\s+({_ANY_TARGET})\s+(on|off)"), "onoff_trail"),
    (
        re.compile(rf"{_ON_OFF}\s+the\s+lights\s+(on|off)\s+in\s+the\s+({_ROOM})"),
        "onoff_area",
    ),
    (re.compile(rf"toggle\s+({_LIGHT_TARGET})"), "toggle"),
    (
        re.compile(
            rf"(?:set|put)\s+({_LIGHT_TARGET})\s+(?:to|at)\s+{_NUM}\s*(?:percent|%)"
        ),
        "brightness",
    ),
    (
        re.compile(rf"dim\s+({_LIGHT_TARGET})\s+to\s+{_NUM}\s*(?:percent|%)"),
        "brightness",
    ),
    (
        re.compile(
            rf"(?:set|turn|change|make)\s+({_LIGHT_TARGET})\s+(?:to\s+)?({_COLOR})"
        ),
        "color",
    ),
    (
        re.compile(rf"set\s+(?:{_THERMO}|{_TEMP_WORD})\s+to\s+{_NUM}\s*(?:degrees?)?"),
        "temperature",
    ),
    (re.compile(rf"(?:pause|stop)\s+({_MEDIA})"), "media"),
    (
        re.compile(
            rf"(?:activate|put\s+on|set\s+the\s+scene\s+to)\s+({_MOVIE})"
            r"(?:\s+in\s+the\s+living\s+room)?"
        ),
        "scene",
    ),
]

_TARGET_KEY: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"^(?:the\s+)?(?:all\s+the\s+)?{_AREA}\s+lights?$"), "area"),
    (re.compile(r"^stairs\s+lights?$"), "stairs_light"),
    (re.compile(r"^good\s+vibes\s+sign$"), "good_vibes_sign"),
    (re.compile(r"^kitchen\s+mushroom\s+lamp$"), "kitchen_mushroom_lamp"),
    (re.compile(r"^bedroom\s+mushroom\s+plug$"), "bedroom_mushroom_plug"),
    (re.compile(r"^bedroom\s+window\s+plug$"), "bedroom_window_plug"),
    (
        re.compile(r"^(?:living\s+room\s+)?(?:thermostat|temperature)$"),
        "living_room_thermostat",
    ),
    (
        re.compile(
            r"^(?:satellite\s+(?:media\s+player|speaker)|music\s+on\s+the\s+satellite\s+speaker)$"
        ),
        "satellite_media_player",
    ),
    (re.compile(r"^movie\s+mode$"), "movie_mode"),
]

_AREA_KEY = {
    "kitchen": "kitchen_lights",
    "living room": "living_room_lights",
    "bedroom": "bedroom_lights",
    "downstairs": "downstairs_lights",
    "govee": "all_govee_lights",
}

_COLOR_KEY = {c.replace("_", " "): c for c in COLORS}

_BRIGHTNESS_RANGE = (0.0, 100.0)
_TEMPERATURE_RANGE = (50.0, 90.0)


def _clean(text: str) -> str:
    cleaned = _WS.sub(" ", normalized_text(text).lower()).strip()
    cleaned = _END_PUNCT.sub("", cleaned).strip()
    return _POLITE.sub("", cleaned).strip()


def _resolve_target(phrase: str) -> str | None:
    phrase = _WS.sub(" ", phrase).strip()
    phrase = re.sub(r"^(?:all\s+the\s+|the\s+)", "", phrase)
    for pattern, key in _TARGET_KEY:
        if pattern.match(phrase):
            if key == "area":
                area = re.sub(r"^(?:the\s+)?(?:all\s+the\s+)?|\s+lights?$", "", phrase)
                return _AREA_KEY.get(_WS.sub(" ", area).strip())
            return key
    return None


def _single_number(text: str) -> float | None:
    values = [float(m.group(1)) for m in _NUMBER.finditer(text)]
    return values[0] if len(values) == 1 else None


def _in_range(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value <= bounds[1]


def parse_canonical(text: str) -> Command | None:
    """Return a Command for unambiguous canonical utterances, else None."""
    cleaned = _clean(text)
    if not cleaned or _COMPOUND.search(cleaned):
        return None
    for pattern, kind in _PATTERNS:
        match = pattern.fullmatch(cleaned)
        if match is None:
            continue
        command = _build(kind, match, cleaned)
        if command is not None:
            if command.action in RESTRICTED_ACTIONS:
                return None
            return command
    return None


def _build(kind: str, match: re.Match[str], cleaned: str) -> Command | None:
    if kind in {"onoff_lead", "onoff_trail"}:
        if kind == "onoff_lead":
            state, phrase = match.group(1), match.group(2)
        else:
            phrase, state = match.group(1), match.group(2)
        return _command(phrase, f"turn_{state}")
    if kind == "onoff_area":
        state, area = match.group(1), match.group(2)
        target = _AREA_KEY.get(area)
        if target is None or f"turn_{state}" not in TARGETS[target].actions:
            return None
        return Command(target, f"turn_{state}", 1.0)
    if kind == "toggle":
        return _command(match.group(1), "toggle")
    if kind == "brightness":
        value = _single_number(cleaned)
        if value is None or not _in_range(value, _BRIGHTNESS_RANGE):
            return None
        command = _command(match.group(1), "set_brightness")
        if command is None:
            return None
        return Command(command.target, command.action, 1.0, value=value)
    if kind == "color":
        color = _COLOR_KEY.get(_WS.sub(" ", match.group(2)).strip())
        if color is None:
            return None
        command = _command(match.group(1), "set_color")
        if command is None:
            return None
        return Command(command.target, command.action, 1.0, color=color)
    if kind == "temperature":
        value = _single_number(cleaned)
        if value is None or not _in_range(value, _TEMPERATURE_RANGE):
            return None
        target = _resolve_target("thermostat")
        if target is None or "set_temperature" not in TARGETS[target].actions:
            return None
        return Command(target, "set_temperature", 1.0, value=value)
    if kind == "media":
        target = _resolve_target(match.group(1))
        if target != "satellite_media_player":
            return None
        return Command(target, "pause_media", 1.0)
    if kind == "scene":
        return Command("movie_mode", "activate_scene", 1.0)
    return None


def _command(phrase: str, action: str) -> Command | None:
    target = _resolve_target(phrase)
    if target is None or action not in TARGETS[target].actions:
        return None
    return Command(target, action, 1.0)
