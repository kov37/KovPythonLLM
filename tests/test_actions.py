"""Regression coverage for atomic action contracts."""

from KOV.contracts.actions import EditLinesAction


def test_edit_lines_allows_empty_replacement_for_range_deletion() -> None:
    action = EditLinesAction(
        workspace="candidate",
        path="tests/test_example.py",
        line_start=4,
        line_end=8,
        replacement_text="",
        expected_digest="0" * 64,
    )

    assert action.replacement_text == ""
