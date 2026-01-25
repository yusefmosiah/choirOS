import unittest

from supervisor.mode_engine import (
    MODE_BOLD,
    MODE_CALM,
    MODE_CONTRITE,
    MODE_CURIOUS,
    MODE_DEFERENTIAL,
    MODE_PARANOID,
    MODE_PETTY,
    MODE_SKEPTICAL,
    ModeInputs,
    select_initial_mode,
    transition_mode,
)


class TestModeEngine(unittest.TestCase):
    def test_initial_crash_goes_contrite(self) -> None:
        inputs = ModeInputs(crash_detected=True)
        self.assertEqual(select_initial_mode(inputs), MODE_CONTRITE)

    def test_initial_missing_demo_or_conjectures(self) -> None:
        inputs = ModeInputs(has_demo=False)
        self.assertEqual(select_initial_mode(inputs), MODE_CURIOUS)
        inputs = ModeInputs(conjectures_present=False)
        self.assertEqual(select_initial_mode(inputs), MODE_CURIOUS)

    def test_initial_repeated_failures(self) -> None:
        inputs = ModeInputs(repeated_verifier_failures=True)
        self.assertEqual(select_initial_mode(inputs), MODE_SKEPTICAL)

    def test_initial_privilege_boundary(self) -> None:
        inputs = ModeInputs(about_to_cross_privilege_boundary=True)
        self.assertEqual(select_initial_mode(inputs), MODE_PARANOID)
        inputs = ModeInputs(about_to_cross_privilege_boundary=True, preference_missing=True)
        self.assertEqual(select_initial_mode(inputs), MODE_DEFERENTIAL)

    def test_calm_transitions(self) -> None:
        inputs = ModeInputs(user_idk=True)
        self.assertEqual(transition_mode(MODE_CALM, inputs), MODE_CURIOUS)
        inputs = ModeInputs(verifiers_regress=True)
        self.assertEqual(transition_mode(MODE_CALM, inputs), MODE_SKEPTICAL)

    def test_skeptical_transitions(self) -> None:
        inputs = ModeInputs(hyperthesis_high=True)
        self.assertEqual(transition_mode(MODE_SKEPTICAL, inputs), MODE_PARANOID)
        inputs = ModeInputs(verified_and_bounded=True)
        self.assertEqual(transition_mode(MODE_SKEPTICAL, inputs), MODE_CALM)

    def test_paranoid_transitions(self) -> None:
        inputs = ModeInputs(mitigations_installed=True)
        self.assertEqual(transition_mode(MODE_PARANOID, inputs), MODE_BOLD)

    def test_contrite_returns_previous(self) -> None:
        inputs = ModeInputs(state_consistent=True, previous_mode=MODE_CURIOUS)
        self.assertEqual(transition_mode(MODE_CONTRITE, inputs), MODE_CURIOUS)
        inputs = ModeInputs(state_consistent=False, previous_mode=MODE_CURIOUS)
        self.assertEqual(transition_mode(MODE_CONTRITE, inputs), MODE_CONTRITE)

    def test_petty_preempts(self) -> None:
        inputs = ModeInputs(suspected_reward_hack=True)
        self.assertEqual(transition_mode(MODE_CALM, inputs), MODE_PETTY)


if __name__ == "__main__":
    unittest.main()
