"""Deterministic mood selection and transition guards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


MOOD_CALM = "CALM"
MOOD_CURIOUS = "CURIOUS"
MOOD_SKEPTICAL = "SKEPTICAL"
MOOD_PARANOID = "PARANOID"
MOOD_BOLD = "BOLD"
MOOD_PETTY = "PETTY"
MOOD_CONTRITE = "CONTRITE"
MOOD_DEFERENTIAL = "DEFERENTIAL"


@dataclass(frozen=True)
class MoodInputs:
    crash_detected: bool = False
    has_demo: bool = True
    conjectures_present: bool = True
    repeated_verifier_failures: bool = False
    about_to_cross_privilege_boundary: bool = False
    preference_missing: bool = False
    ambiguity_blocking: bool = False
    user_idk: bool = False
    verifiers_regress: bool = False
    hyperthesis_high: bool = False
    mitigations_installed: bool = False
    verified_and_bounded: bool = False
    suspected_reward_hack: bool = False
    state_consistent: bool = True
    previous_mood: Optional[str] = None


def select_initial_mood(inputs: MoodInputs) -> str:
    if inputs.crash_detected:
        return MOOD_CONTRITE
    if not inputs.has_demo or not inputs.conjectures_present:
        return MOOD_CURIOUS
    if inputs.repeated_verifier_failures:
        return MOOD_SKEPTICAL
    if inputs.about_to_cross_privilege_boundary:
        return MOOD_DEFERENTIAL if inputs.preference_missing else MOOD_PARANOID
    return MOOD_CALM


def transition_mood(current: str, inputs: MoodInputs) -> str:
    if inputs.crash_detected:
        return MOOD_CONTRITE
    if inputs.suspected_reward_hack:
        return MOOD_PETTY
    if inputs.preference_missing:
        return MOOD_DEFERENTIAL

    if current == MOOD_CALM:
        if inputs.ambiguity_blocking or inputs.user_idk:
            return MOOD_CURIOUS
        if inputs.verifiers_regress:
            return MOOD_SKEPTICAL
    elif current == MOOD_SKEPTICAL:
        if inputs.hyperthesis_high:
            return MOOD_PARANOID
        if inputs.verified_and_bounded:
            return MOOD_CALM
    elif current == MOOD_PARANOID:
        if inputs.mitigations_installed:
            return MOOD_BOLD
    elif current == MOOD_CONTRITE:
        if inputs.state_consistent:
            return inputs.previous_mood or MOOD_CALM
        return MOOD_CONTRITE

    return current
