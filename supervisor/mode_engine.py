"""Deterministic mode selection and transition guards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


MODE_CALM = "CALM"
MODE_CURIOUS = "CURIOUS"
MODE_SKEPTICAL = "SKEPTICAL"
MODE_PARANOID = "PARANOID"
MODE_BOLD = "BOLD"
MODE_PETTY = "PETTY"
MODE_CONTRITE = "CONTRITE"
MODE_DEFERENTIAL = "DEFERENTIAL"


@dataclass(frozen=True)
class ModeInputs:
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
    previous_mode: Optional[str] = None


def select_initial_mode(inputs: ModeInputs) -> str:
    if inputs.crash_detected:
        return MODE_CONTRITE
    if not inputs.has_demo or not inputs.conjectures_present:
        return MODE_CURIOUS
    if inputs.repeated_verifier_failures:
        return MODE_SKEPTICAL
    if inputs.about_to_cross_privilege_boundary:
        return MODE_DEFERENTIAL if inputs.preference_missing else MODE_PARANOID
    return MODE_CALM


def transition_mode(current: str, inputs: ModeInputs) -> str:
    if inputs.crash_detected:
        return MODE_CONTRITE
    if inputs.suspected_reward_hack:
        return MODE_PETTY
    if inputs.preference_missing:
        return MODE_DEFERENTIAL

    if current == MODE_CALM:
        if inputs.ambiguity_blocking or inputs.user_idk:
            return MODE_CURIOUS
        if inputs.verifiers_regress:
            return MODE_SKEPTICAL
    elif current == MODE_SKEPTICAL:
        if inputs.hyperthesis_high:
            return MODE_PARANOID
        if inputs.verified_and_bounded:
            return MODE_CALM
    elif current == MODE_PARANOID:
        if inputs.mitigations_installed:
            return MODE_BOLD
    elif current == MODE_CONTRITE:
        if inputs.state_consistent:
            return inputs.previous_mode or MODE_CALM
        return MODE_CONTRITE

    return current
