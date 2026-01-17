import unittest

from supervisor.mood_engine import (
    MOOD_BOLD,
    MOOD_CALM,
    MOOD_CONTRITE,
    MOOD_CURIOUS,
    MOOD_DEFERENTIAL,
    MOOD_PARANOID,
    MOOD_PETTY,
    MOOD_SKEPTICAL,
    MoodInputs,
    select_initial_mood,
    transition_mood,
)


class TestMoodEngine(unittest.TestCase):
    def test_initial_crash_goes_contrite(self) -> None:
        inputs = MoodInputs(crash_detected=True)
        self.assertEqual(select_initial_mood(inputs), MOOD_CONTRITE)

    def test_initial_missing_demo_or_conjectures(self) -> None:
        inputs = MoodInputs(has_demo=False)
        self.assertEqual(select_initial_mood(inputs), MOOD_CURIOUS)
        inputs = MoodInputs(conjectures_present=False)
        self.assertEqual(select_initial_mood(inputs), MOOD_CURIOUS)

    def test_initial_repeated_failures(self) -> None:
        inputs = MoodInputs(repeated_verifier_failures=True)
        self.assertEqual(select_initial_mood(inputs), MOOD_SKEPTICAL)

    def test_initial_privilege_boundary(self) -> None:
        inputs = MoodInputs(about_to_cross_privilege_boundary=True)
        self.assertEqual(select_initial_mood(inputs), MOOD_PARANOID)
        inputs = MoodInputs(about_to_cross_privilege_boundary=True, preference_missing=True)
        self.assertEqual(select_initial_mood(inputs), MOOD_DEFERENTIAL)

    def test_calm_transitions(self) -> None:
        inputs = MoodInputs(user_idk=True)
        self.assertEqual(transition_mood(MOOD_CALM, inputs), MOOD_CURIOUS)
        inputs = MoodInputs(verifiers_regress=True)
        self.assertEqual(transition_mood(MOOD_CALM, inputs), MOOD_SKEPTICAL)

    def test_skeptical_transitions(self) -> None:
        inputs = MoodInputs(hyperthesis_high=True)
        self.assertEqual(transition_mood(MOOD_SKEPTICAL, inputs), MOOD_PARANOID)
        inputs = MoodInputs(verified_and_bounded=True)
        self.assertEqual(transition_mood(MOOD_SKEPTICAL, inputs), MOOD_CALM)

    def test_paranoid_transitions(self) -> None:
        inputs = MoodInputs(mitigations_installed=True)
        self.assertEqual(transition_mood(MOOD_PARANOID, inputs), MOOD_BOLD)

    def test_contrite_returns_previous(self) -> None:
        inputs = MoodInputs(state_consistent=True, previous_mood=MOOD_CURIOUS)
        self.assertEqual(transition_mood(MOOD_CONTRITE, inputs), MOOD_CURIOUS)
        inputs = MoodInputs(state_consistent=False, previous_mood=MOOD_CURIOUS)
        self.assertEqual(transition_mood(MOOD_CONTRITE, inputs), MOOD_CONTRITE)

    def test_petty_preempts(self) -> None:
        inputs = MoodInputs(suspected_reward_hack=True)
        self.assertEqual(transition_mood(MOOD_CALM, inputs), MOOD_PETTY)


if __name__ == "__main__":
    unittest.main()
