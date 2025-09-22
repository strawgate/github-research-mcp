from collections import defaultdict
from collections.abc import Sequence
from fnmatch import fnmatch
from typing import Self

from githubkit.versions.v2022_11_28.models import GitTree
from pydantic import BaseModel, Field, field_validator


def get_file_extension(file_path: str) -> str | None:
    if "." not in file_path:
        return None
    return file_path.split(".")[-1]


def matches_pattern(pattern: str, directory_path: str, file_path: str) -> bool:
    """If the pattern is a regex, it will be matched against the directory_path and file_path.
    if the pattern is not a regex, we do a simple contains check."""

    full_path = f"{directory_path}/{file_path}"

    return fnmatch(full_path, pattern)


def matches_include_exclude(full_path: str, include_patterns: list[str] | None, exclude_patterns: list[str] | None) -> bool:
    if exclude_patterns is not None:
        for exclude_pattern in exclude_patterns:
            if matches_pattern(pattern=exclude_pattern, directory_path=full_path, file_path=full_path):
                return False

    if include_patterns is not None:
        for include_pattern in include_patterns:
            if matches_pattern(pattern=include_pattern, directory_path=full_path, file_path=full_path):
                return True
        return False

    return True


def get_dir_and_file_from_path(path: str) -> tuple[str, str]:
    path_parts = path.split("/")
    directory_path = "/".join(path_parts[:-1])
    file_path = path_parts[-1]
    return directory_path, file_path


class RepositoryFileCountEntry(BaseModel):
    extension: str
    count: int

    @staticmethod
    def sort(entries: list["RepositoryFileCountEntry"]) -> list["RepositoryFileCountEntry"]:
        return sorted(entries, key=lambda x: x.count, reverse=True)

    @staticmethod
    def sort_and_truncate(entries: list["RepositoryFileCountEntry"], top_n: int = 50) -> list["RepositoryFileCountEntry"]:
        return RepositoryFileCountEntry.sort(entries=entries)[:top_n]


class RepositoryTreeDirectory(BaseModel):
    path: str
    files: list[str]

    @property
    def file_paths(self) -> list[str]:
        return [f"{self.path}/{file}" for file in self.files]

    def to_filtered_directory(
        self,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
    ) -> "RepositoryTreeDirectory":
        files: list[str] = [
            file
            for file in self.files
            if matches_include_exclude(
                full_path=f"{self.path}/{file}",
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )
        ]

        return RepositoryTreeDirectory(path=self.path, files=files)

    @property
    def depth(self) -> int:
        return len(self.path.split("/"))

    @property
    def count_files(self) -> int:
        return len(self.files)

    def count_file_extensions(self) -> list[RepositoryFileCountEntry]:
        count_by_extension: dict[str, int] = defaultdict(int)

        for file in self.files:
            if extension := get_file_extension(file):
                count_by_extension[extension] += 1

        return [RepositoryFileCountEntry(extension=extension, count=count) for extension, count in count_by_extension.items()]


class RepositoryTree(BaseModel):
    directories: list[RepositoryTreeDirectory]
    files: list[str]
    truncated: bool = Field(
        default=False,
        description="Whether the results have been truncated. If true, the results do not contain all files.",
    )

    @field_validator("directories")
    @classmethod
    def validate_directories(cls, v: list[RepositoryTreeDirectory]) -> list[RepositoryTreeDirectory]:
        return [directory for directory in v if directory.files]

    @classmethod
    def from_git_tree(cls, git_tree: GitTree) -> Self:
        directories: dict[str, RepositoryTreeDirectory] = {}
        files: list[str] = []

        for tree_item in git_tree.tree:
            if tree_item.type == "tree":
                directories[tree_item.path] = RepositoryTreeDirectory(path=tree_item.path, files=[])

        for tree_item in git_tree.tree:
            if tree_item.type == "blob":
                if tree_item.size is not None and tree_item.size == 0:
                    continue
                # Split the path into directories and file
                directory_path, file_path = get_dir_and_file_from_path(tree_item.path)

                if directory := directories.get(directory_path):
                    directory.files.append(file_path)
                    continue

                files.append(file_path)

        return cls(directories=[directory for directory in directories.values() if directory.files], files=files)

    def check_files_not_in_tree(self, files: Sequence[str] | set[str], case_insensitive: bool = True) -> list[str]:
        """Given a list of files, return the files that are not in the tree. If all of the files are in the tree,
        return an empty list."""

        files_in_tree: set[str] = {file.lower() if case_insensitive else file for file in self.file_paths()}

        files_to_check: set[str] = {file.lower() if case_insensitive else file for file in files}

        return list(files_to_check.difference(files_in_tree))

    def check_files_in_tree(self, files: Sequence[str] | set[str], case_insensitive: bool = True) -> list[str]:
        """Given a list of files, return the files that are in the tree. If none of the files are in the tree,
        return an empty list."""

        files_in_tree: set[str] = {file.lower() if case_insensitive else file for file in self.file_paths()}

        files_to_check: set[str] = {file.lower() if case_insensitive else file for file in files}

        return list(files_to_check.intersection(files_in_tree))

    def file_paths(self) -> list[str]:
        """Return all files in the tree."""
        all_file_paths: list[str] = self.files

        for directory in self.directories:
            all_file_paths.extend(directory.file_paths)

        return all_file_paths

    @property
    def count_files(self) -> int:
        return len(self.files) + sum(directory.count_files for directory in self.directories)

    def count_file_extensions(self, top_n: int = 50) -> list[RepositoryFileCountEntry]:
        count_by_extension: dict[str, int] = defaultdict(int)
        for directory in self.directories:
            for entry in directory.count_file_extensions():
                count_by_extension[entry.extension] += entry.count

        for file in self.files:
            if extension := get_file_extension(file):
                count_by_extension[extension] += 1

        return RepositoryFileCountEntry.sort_and_truncate(
            entries=[RepositoryFileCountEntry(extension=extension, count=count) for extension, count in count_by_extension.items()],
            top_n=top_n,
        )

    def truncate(self, limit_results: int) -> "RepositoryTree":
        if len(self.files) > limit_results:
            return RepositoryTree(files=self.files[:limit_results], directories=[], truncated=True)

        truncated_directories: list[RepositoryTreeDirectory] = []

        truncated: bool = False

        for directory in self.directories:
            current_count = sum(len(directory.files) for directory in truncated_directories) + len(self.files)

            if len(directory.files) + current_count <= limit_results:
                truncated_directories.append(directory)
                continue

            truncated = True
            remaining_count = limit_results - current_count

            if remaining_count == 0:
                break

            truncated_directories.append(RepositoryTreeDirectory(path=directory.path, files=directory.files[:remaining_count]))

        return RepositoryTree(files=self.files, directories=truncated_directories, truncated=truncated)


class FilteredRepositoryTree(RepositoryTree):
    include_patterns: list[str] | None = Field(
        default=None,
        description="The patterns to check file paths against. File paths matching any of these patterns will be included in the results.",
    )
    exclude_patterns: list[str] | None = Field(
        default=None,
        description="The patterns to check file paths against. File paths matching any of these patterns will be excluded.",
    )

    @classmethod
    def from_repository_tree(
        cls,
        repository_tree: RepositoryTree,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
    ) -> Self:
        files = [
            file
            for file in repository_tree.files
            if matches_include_exclude(
                full_path=file,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )
        ]

        directories: list[RepositoryTreeDirectory] = [
            directory.to_filtered_directory(
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )
            for directory in repository_tree.directories
        ]

        return cls(
            directories=directories,
            files=files,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )


class PrunedRepositoryTree(RepositoryTree):
    depth: int

    @classmethod
    def from_repository_tree(cls, repository_tree: RepositoryTree, depth: int) -> Self:
        return cls(
            directories=[directory for directory in repository_tree.directories if directory.depth <= depth],
            files=repository_tree.files,
            depth=depth,
        )
