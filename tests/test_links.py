"""Check link extraction and ensure baseline exceptions cannot grow silently."""

from collections import Counter

from scripts.check_links import baseline_changes, local_targets


def test_local_targets_ignore_remote_anchor_and_fenced_examples() -> None:
    markdown = """[file](docs/file.md#section) ![image](<data/my image.png>)
[remote](https://example.org/file) [anchor](#section) [email](mailto:a@example.org)
```markdown
[example](missing.md)
```
[encoded](data/my%20image.png "title")
"""
    assert local_targets(markdown) == ["docs/file.md", "data/my image.png", "data/my image.png"]


def test_added_occurrences_are_rejected() -> None:
    key = ("docs/a.md", "missing.md")
    added, fixed = baseline_changes(Counter({key: 2}), Counter({key: 1}))
    assert added == Counter({key: 1})
    assert not fixed


def test_fixed_exceptions_require_baseline_cleanup() -> None:
    key = ("docs/a.md", "missing.md")
    added, fixed = baseline_changes(Counter(), Counter({key: 1}))
    assert not added
    assert fixed == Counter({key: 1})
