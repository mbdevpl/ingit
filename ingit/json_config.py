"""JSON-based configuration I/O."""

import json
import json.decoder
import os
import pathlib
import typing as t

JSON_INDENT = 2

JSON_ENSURE_ASCII = False


def normalize_path(path: t.Union[pathlib.Path, str]) -> t.Union[pathlib.Path, str]:
    if isinstance(path, str):
        return os.path.expanduser(os.path.expandvars(path))
    return pathlib.Path(normalize_path(str(path)))


def json_to_str(data: dict) -> str:
    assert isinstance(data, dict), type(data)
    return json.dumps(data, indent=JSON_INDENT, ensure_ascii=JSON_ENSURE_ASCII)


def str_to_json(text: str) -> dict:
    """Convert JSON string into an object."""
    try:
        return json.loads(text)
    except json.decoder.JSONDecodeError as err:
        lines = text.splitlines(keepends=True)
        raise ValueError('\n{}{}\n{}'.format(
            ''.join(lines[max(0, err.lineno - 10):err.lineno]), '-' * err.colno,
            ''.join(lines[err.lineno:min(err.lineno + 10, len(lines))]))) from err


def json_to_file(data: dict, path: pathlib.Path) -> None:
    """Save JSON object to a file."""
    assert isinstance(data, dict), type(data)
    assert isinstance(path, pathlib.Path), type(path)
    text = json_to_str(data)
    with open(normalize_path(str(path)), 'w', encoding='utf-8') as json_file:
        json_file.write(text)


def file_to_json(path: pathlib.Path) -> dict:
    """Create JSON object from a file."""
    with open(normalize_path(str(path)), 'r', encoding='utf-8') as json_file:
        text = json_file.read()
    try:
        data = str_to_json(text)
    except ValueError as err:
        raise ValueError('in file "{}"'.format(path)) from err
    return data
