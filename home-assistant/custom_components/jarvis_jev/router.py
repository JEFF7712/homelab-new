from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .const import CLARIFY_THRESHOLD, CLIMATE_THRESHOLD, LIGHT_THRESHOLD, MODEL


@dataclass(frozen=True)
class Target:
    entity_id: str
    actions: frozenset[str]


@dataclass(frozen=True)
class Command:
    target: str
    action: str
    confidence: float
    value: float | None = None
    color: str | None = None


@dataclass(frozen=True)
class Decision:
    route: str
    command: Command | None = None
    speech: str | None = None


TARGETS = {
    "downstairs_lights": Target(
        "light.downstairs_lights",
        frozenset(
            {
                "turn_on",
                "turn_off",
                "toggle",
                "set_brightness",
                "adjust_brightness_up",
                "adjust_brightness_down",
                "set_color",
            }
        ),
    ),
    "kitchen_lights": Target(
        "light.kitchen_lights",
        frozenset(
            {
                "turn_on",
                "turn_off",
                "toggle",
                "set_brightness",
                "adjust_brightness_up",
                "adjust_brightness_down",
                "set_color",
            }
        ),
    ),
    "living_room_lights": Target(
        "light.living_room_lights",
        frozenset(
            {
                "turn_on",
                "turn_off",
                "toggle",
                "set_brightness",
                "adjust_brightness_up",
                "adjust_brightness_down",
                "set_color",
            }
        ),
    ),
    "bedroom_lights": Target(
        "light.bedroom_roku_lights",
        frozenset(
            {
                "turn_on",
                "turn_off",
                "toggle",
                "set_brightness",
                "adjust_brightness_up",
                "adjust_brightness_down",
                "set_color",
            }
        ),
    ),
    "all_govee_lights": Target(
        "light.all_govee_lights",
        frozenset(
            {
                "turn_on",
                "turn_off",
                "toggle",
                "set_brightness",
                "adjust_brightness_up",
                "adjust_brightness_down",
                "set_color",
            }
        ),
    ),
    "kitchen_mushroom_lamp": Target(
        "light.kitchen_mushroom_lamp", frozenset({"turn_on", "turn_off", "toggle"})
    ),
    "bedroom_window_plug": Target(
        "light.bedroom_window_plug", frozenset({"turn_on", "turn_off", "toggle"})
    ),
    "bedroom_mushroom_plug": Target(
        "light.bedroom_mushroom_plug", frozenset({"turn_on", "turn_off", "toggle"})
    ),
    "good_vibes_sign": Target(
        "light.living_room_good_vibes_sign",
        frozenset({"turn_on", "turn_off", "toggle"}),
    ),
    "stairs_light": Target(
        "switch.stairs_light", frozenset({"turn_on", "turn_off", "toggle"})
    ),
    "living_room_thermostat": Target(
        "climate.living_room_ac_living_room_ac_thermostat",
        frozenset(
            {"set_temperature", "adjust_temperature_up", "adjust_temperature_down"}
        ),
    ),
    "satellite_media_player": Target(
        "media_player.homelab_05_satellite_media_player", frozenset({"pause_media"})
    ),
    "movie_mode": Target("scene.movie_low_living_room", frozenset({"activate_scene"})),
}

COLORS = frozenset(
    {
        "white",
        "red",
        "orange",
        "yellow",
        "green",
        "blue",
        "purple",
        "pink",
        "neon_pink",
        "warm_white",
    }
)

_NUMBER = re.compile(
    r"(?<![\w.])(-?\d+(?:\.\d+)?)(?:\s*(?:degrees?|percent)|\s*%|\s*°[fc]?)?(?![\w.])",
    re.IGNORECASE,
)
_SPEAKER = re.compile(r"^speaker\s+[^\s]+\s+", re.IGNORECASE)


def normalized_text(text: str) -> str:
    return _SPEAKER.sub("", text.strip(), count=1)


def build_request(text: str) -> dict[str, Any]:
    return {
        "state": normalized_text(text),
        "model": MODEL,
        "questions": {
            "request_kind": {
                "type": "choice",
                "instructions": (
                    "Classify this utterance. A home command requests one concrete "
                    "smart-home action. Compound means two or more actions."
                ),
                "criteria": {
                    "home_command": "One concrete smart-home action",
                    "general_or_conversation": "General knowledge or conversation, with no home action",
                    "compound": "Two or more requested actions",
                    "unsupported": "A home request that cannot be represented by the available targets or actions",
                },
            },
            "target": {
                "type": "choice",
                "instructions": (
                    "Select the explicitly requested smart-home target. Do not infer "
                    "a room that was not stated."
                ),
                "criteria": {key: value.entity_id for key, value in TARGETS.items()}
                | {"none_or_unknown": "No explicit known target"},
            },
            "action": {
                "type": "choice",
                "instructions": "Select the single requested action.",
                "criteria": {
                    "turn_on": "Turn on",
                    "turn_off": "Turn off",
                    "toggle": "Toggle",
                    "set_brightness": "Set an exact brightness percentage",
                    "adjust_brightness_up": "Increase brightness",
                    "adjust_brightness_down": "Decrease brightness",
                    "set_color": "Set a named light color",
                    "set_temperature": "Set an exact thermostat temperature",
                    "adjust_temperature_up": "Make the thermostat warmer",
                    "adjust_temperature_down": "Make the thermostat cooler",
                    "activate_scene": "Activate a scene",
                    "pause_media": "Pause or stop media",
                    "none_or_unsupported": "No supported action",
                },
            },
            "color": {
                "type": "choice",
                "instructions": "Select the explicitly requested color, or none if color is irrelevant or absent.",
                "criteria": {color: color.replace("_", " ") for color in sorted(COLORS)}
                | {"none_or_unknown": "No supported color stated"},
            },
            "reference": {
                "type": "choice",
                "instructions": (
                    "Was the target explicitly named in this utterance? Pronouns and "
                    "phrases such as it, them, there, or down here are ambiguous."
                ),
                "criteria": {
                    "explicit_target": "A target or room is explicitly named",
                    "missing_or_ambiguous": "The target is omitted or only referenced indirectly",
                },
            },
        },
    }


def _choice(answers: dict[str, Any], name: str) -> tuple[str, float] | None:
    answer = answers.get(name)
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        return None
    choice = answer.get("choice")
    confidence = answer.get("confidence")
    if not isinstance(choice, str) or not isinstance(confidence, (int, float)):
        return None
    if not 0 <= float(confidence) <= 1:
        return None
    return choice, float(confidence)


def _one_number(text: str) -> float | None:
    values = [float(match.group(1)) for match in _NUMBER.finditer(text)]
    return values[0] if len(values) == 1 else None


def decide(text: str, payload: Any) -> Decision:
    if not isinstance(payload, dict) or payload.get("model") != MODEL:
        return Decision("reject", speech="Jev is unavailable.")
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return Decision("reject", speech="Jev is unavailable.")

    kind = _choice(answers, "request_kind")
    if kind is None:
        return Decision("reject", speech="Jev is unavailable.")
    kind_name, kind_confidence = kind
    if kind_name == "general_or_conversation" and kind_confidence >= LIGHT_THRESHOLD:
        return Decision("fallback")
    if kind_name == "compound":
        return Decision("clarify", speech="Please ask for one action at a time.")
    if kind_name != "home_command":
        return Decision(
            "clarify", speech="Please repeat with one supported device and action."
        )

    target_answer = _choice(answers, "target")
    action_answer = _choice(answers, "action")
    reference_answer = _choice(answers, "reference")
    if target_answer is None or action_answer is None or reference_answer is None:
        return Decision("reject", speech="Jev is unavailable.")
    target_name, target_confidence = target_answer
    action, action_confidence = action_answer
    reference, reference_confidence = reference_answer
    target = TARGETS.get(target_name)
    confidence = min(
        kind_confidence, target_confidence, action_confidence, reference_confidence
    )

    if target is None or action not in target.actions or reference != "explicit_target":
        return Decision(
            "clarify", speech="Please repeat with the device or room and one action."
        )

    value: float | None = None
    color: str | None = None
    if action in {"set_brightness", "set_temperature"}:
        value = _one_number(normalized_text(text))
        if value is None:
            return Decision("clarify", speech="Please repeat with one exact value.")
        if action == "set_brightness" and not 0 <= value <= 100:
            return Decision(
                "clarify",
                speech="Brightness must be between zero and one hundred percent.",
            )
    if action == "set_color":
        color_answer = _choice(answers, "color")
        if color_answer is None:
            return Decision("reject", speech="Jev is unavailable.")
        color, color_confidence = color_answer
        confidence = min(confidence, color_confidence)
        if color not in COLORS:
            return Decision("clarify", speech="Please name a supported color.")

    threshold = (
        CLIMATE_THRESHOLD
        if target_name == "living_room_thermostat"
        else LIGHT_THRESHOLD
    )
    if confidence < threshold:
        if confidence >= CLARIFY_THRESHOLD:
            return Decision(
                "clarify", speech="Please repeat with the device or room and action."
            )
        return Decision("clarify", speech="I could not identify a safe home command.")

    return Decision(
        "execute",
        command=Command(target_name, action, confidence, value=value, color=color),
    )
