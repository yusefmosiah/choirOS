# Experiment: q3-modes-classification

**Date**: 2026-01-29T01:33:03.219008Z
**Question**: What are modes really - risk levels, verification strategies, or capability categories?

## PREDICTION
Mode selection will be driven by risk/verification signals while mode configs enforce capability boundaries.

## EXPERIMENT
Analyze mode_config capability profiles and probe mode_engine transitions by toggling ModeInputs flags to see which signals trigger mode changes.

## OBSERVE
If capability profiles are distinct and risk/verification signals influence mode selection, mark modes as a hybrid of capability boundaries and risk strategies.

## LEARNING
- Status: supported
- Summary: Mode selection responds to risk/verification signals, while mode configs enforce capability boundaries (write/network/tooling).
- Evidence: supervisor/mode_config.py, supervisor/mode_engine.py
