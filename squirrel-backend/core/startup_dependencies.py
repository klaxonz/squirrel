from dataclasses import dataclass


@dataclass(frozen=True)
class StartupDependencyIssue:
    name: str
    error: str


_optional_issues: dict[str, StartupDependencyIssue] = {}


def reset_startup_dependency_issues() -> None:
    _optional_issues.clear()


def record_optional_startup_issue(name: str, exc: Exception) -> None:
    _optional_issues[name] = StartupDependencyIssue(name=name, error=str(exc))


def clear_optional_startup_issue(name: str) -> None:
    _optional_issues.pop(name, None)


def list_optional_startup_issues() -> list[StartupDependencyIssue]:
    return list(_optional_issues.values())
