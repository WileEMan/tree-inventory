from __future__ import annotations
import os
import hashlib
import json
import logging
from pathlib import Path
from typing import Tuple, Union, Any

logger = logging.getLogger(__name__)

PathOrStr = Union[Path, str]
# HASH = hashlib._hashlib.HASH


def calculate_md5(dirname: PathOrStr, fname: PathOrStr) -> Any:
    """Calculate the MD5 of a single file."""
    hash_md5 = hashlib.md5()
    hash_md5.update(str(fname).encode("utf-8"))
    with open(Path(dirname) / fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    # print(f"MD5 of file '{fname}': {hash_md5.hexdigest()}")
    return hash_md5


def record_summary(record: dict):
    """A helper for displaying a succinct summary of one record.  It will
    generally be used for looking at a specific record and not the entire
    record tree.
    """

    ret = "{"
    for key in record:
        if key == "subdirectories":
            subdirectories = record[key]
            ret += f"\n\t{key}: subdirectories: "
            if len(subdirectories) < 10:
                ret += ", ".join([name for name in subdirectories])
            else:
                ret += f"{str(len(record[key]))} subdirectories (not shown)"
        else:
            ret += f"\n\t{key}: {str(record[key])}"
    ret += "\n}"
    return ret


def enumerate_dir(dir: Path) -> Tuple[list, list]:
    """Perform the basic enumeration of files and folders within a directory."""

    subdirectories = []
    files = []
    for name in os.listdir(dir):
        if os.path.isdir(dir / name):
            subdirectories.append(name)
        else:
            files.append(name)
    return files, subdirectories


def find_checksum_file(starting: Path):
    """If the user requests information or comparison about a folder, a first
    step will be to check whether there is a record file in the folder or at
    a higher-level than the folder.  This routine searches within the parent
    tree of the folder for a record file.  It returns None if there is no
    record file found.
    """
    attempt = starting / "tree_checksum.json"
    if attempt.exists():
        return attempt
    if starting.resolve() == starting.parent.resolve():
        # 'starting' is already the root...
        return None
    return find_checksum_file(starting.parent)


def read_checksum_file(checksum_file: Path) -> dict:
    """Read a record file."""
    with open(checksum_file, "rt") as fh:
        return json.load(fh)


def extract_record(root_record: dict, checksum_file: Path, target_path: Path):
    """Once a record file is found and read, it may be necessary to locate
    a particular subrecord within the record tree.  For example, if the user
    wants to compare folders /root/A/AA and /root/B/AA but the record files
    are at the level of "A" and "B", then we need to first read the top-level
    record files and then locate the subrecord for AA within each.
    """

    def descend_toward(target: tuple, base_record: dict):
        try:
            print(f"Descending toward: {target}")
            first_dir = target[0]
            if first_dir not in base_record["subdirectories"]:
                raise RuntimeError(
                    f"While searching for the subdirectory entry for: {target_path}"
                    + f"\nIn checksum record file: {checksum_file}"
                    + f"\nThe subdirectory: {first_dir}"
                    + f"\nWas not found in the record.  The checksum record might be out-of-date."
                )
            next_record = base_record["subdirectories"][first_dir]
            if len(target) == 1:
                return next_record
            return descend_toward(target[1:], next_record)
        except Exception as ex:
            raise RuntimeError(
                str(ex)
                + f"\nWhile descending records toward: {target}"
                + f"\nFrom base record: \n{record_summary(base_record)}"
            ) from ex

    logger.debug(f"target_path = {target_path}")
    logger.debug(f"checksum_file = {checksum_file}")
    logger.debug(f"checksum_file.parent = {checksum_file.parent}")
    rel_path = target_path.relative_to(checksum_file.parent)
    if str(rel_path) == ".":
        return rel_path, root_record
    logger.debug(f"rel_path = {rel_path}")
    logger.debug(f"Searching for record for target: {rel_path}")
    return rel_path, descend_toward(rel_path.parts, root_record)
