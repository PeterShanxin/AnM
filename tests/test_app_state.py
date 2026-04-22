from pathlib import Path

from anm.app_state import FileSelectionModel, collect_pdf_files, is_generated_pdf, natural_sort_key


def test_natural_sort_key_orders_numbers_intuitively() -> None:
    names = ["page10.pdf", "page2.pdf", "page1.pdf"]
    assert sorted(names, key=natural_sort_key) == ["page1.pdf", "page2.pdf", "page10.pdf"]


def test_collect_pdf_files_ignores_generated_outputs(tmp_path: Path) -> None:
    (tmp_path / "page2.pdf").write_bytes(b"")
    (tmp_path / "page10.pdf").write_bytes(b"")
    (tmp_path / "annotatedMerged.pdf").write_bytes(b"")
    output = tmp_path / "output"
    output.mkdir()
    (output / "page1.pdf").write_bytes(b"")

    assert [path.name for path in collect_pdf_files(tmp_path)] == ["page2.pdf", "page10.pdf"]


def test_is_generated_pdf_marks_legacy_and_output_paths(tmp_path: Path) -> None:
    assert is_generated_pdf(tmp_path / "annotatedMerged.pdf")
    assert is_generated_pdf(tmp_path / "annotated_file.pdf")
    assert is_generated_pdf(tmp_path / "output" / "nested.pdf")


def test_file_selection_model_move_and_include(tmp_path: Path) -> None:
    paths = []
    for name in ["one.pdf", "two.pdf", "three.pdf"]:
        path = tmp_path / name
        path.write_bytes(b"")
        paths.append(path)

    model = FileSelectionModel()
    assert model.add_files(paths) == 3

    model.set_included([1], False)
    model.move([2], -1)

    rows = model.get_display_rows()
    assert rows[1][1] == "three.pdf"
    assert rows[2][0] == "No"
