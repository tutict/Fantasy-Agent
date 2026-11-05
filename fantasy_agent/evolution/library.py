"""Atomic decision records, with one workspace lock for index updates."""

import threading
from pathlib import Path

from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.evolution.contracts import EvolutionExperience, EvolutionReport, ExperienceIndex
from fantasy_agent.path_safety import assert_safe_path_segment, resolve_workspace_path


class EvolutionLibraryError(ValueError):
    """A damaged or unsaved record must never look like an empty library."""


_locks: dict[Path, threading.RLock] = {}
_locks_guard = threading.Lock()


def _lock(root: Path | str) -> threading.RLock:
    key = Path(root).resolve()
    with _locks_guard:
        return _locks.setdefault(key, threading.RLock())


def _path(relative: str, root: Path | str) -> Path:
    return resolve_workspace_path(relative, workspace_root=root)


def _report_path(experiment_id: str, root: Path | str) -> Path:
    assert_safe_path_segment(experiment_id, label="experiment_id")
    return _path(f"generated/evolution/experiments/{experiment_id}.json", root)


def _read(path: Path, model):
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as exc:
        raise EvolutionLibraryError(f"无法读取进化记录 {path.name!r}：{exc}") from exc
    try:
        return model.model_validate_json(raw)
    except ValueError as exc:
        raise EvolutionLibraryError(f"进化记录 {path.name!r} 已损坏，停止使用。") from exc


def _write(path: Path, model) -> None:
    try:
        write_atomic(path, model.model_dump_json(indent=2))
    except OSError as exc:
        raise EvolutionLibraryError(f"无法保存进化记录 {path.name!r}：{exc}") from exc


def save_report(report: EvolutionReport, *, workspace_root: Path | str) -> None:
    with _lock(workspace_root):
        _write(_report_path(report.experiment_id, workspace_root), report)


def load_report(experiment_id: str, *, workspace_root: Path | str) -> EvolutionReport | None:
    with _lock(workspace_root):
        report = _read(_report_path(experiment_id, workspace_root), EvolutionReport)
        if report is not None and report.experiment_id != experiment_id:
            raise EvolutionLibraryError("实验记录 id 与文件 id 不一致，停止使用。")
        return report


def list_experiences(*, workspace_root: Path | str) -> list[EvolutionExperience]:
    with _lock(workspace_root):
        index = _read(_path("generated/evolution/experiences.json", workspace_root), ExperienceIndex)
        return index.experiences if index else []


def save_experience(experience: EvolutionExperience, *, workspace_root: Path | str) -> None:
    assert_safe_path_segment(experience.id, label="experience_id")
    with _lock(workspace_root):
        existing = list_experiences(workspace_root=workspace_root)
        duplicate = next((item for item in existing if item.id == experience.id), None)
        if duplicate is not None:
            if duplicate != experience:
                raise EvolutionLibraryError("同一经验 id 对应不同内容。")
            return
        existing.append(experience)
        _write(_path("generated/evolution/experiences.json", workspace_root),
               ExperienceIndex(experiences=existing))
