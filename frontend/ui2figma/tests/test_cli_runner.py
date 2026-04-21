from pathlib import Path

from frontend.ui2figma.run_text_to_ui import run_from_file


def test_run_from_file_returns_ready_for_codegen_true(tmp_path: Path):
    spec_file = tmp_path / "ui-spec.md"
    spec_file.write_text(
        '# project: demo\n## screen: Home\n- component: header title="Dashboard"\nstates: default',
        encoding="utf-8",
    )

    result = run_from_file(spec_file, review_decision="OK")

    assert result["ready_for_codegen"] is True
