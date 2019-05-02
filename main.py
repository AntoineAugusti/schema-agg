import os
import json

import giturlparse
import tableschema
from semver import VersionInfo
from git import Repo as GitRepo


class ValidationException(Exception):
    def __init__(self, repo, message=None):
        if message is None:
            message = "An error occured with repo: %s" % repo
        super(ValidationException, self).__init__(message)
        self.repo = repo
        self.tag = repo.current_tag


class GitException(ValidationException):
    pass


class NoTagsException(ValidationException):
    pass


class MissingFileException(ValidationException):
    pass


class InvalidVersionException(ValidationException):
    pass


class InvalidSchemaException(ValidationException):
    pass


class TableSchemaValidator(object):
    SCHEMA_FILENAME = "schema.json"

    def __init__(self, repo):
        super(TableSchemaValidator, self).__init__()
        self.repo = repo
        self.git_repo = repo.git_repo

    def validate(self):
        self.check_file_exists("README.md")
        self.check_file_exists(self.SCHEMA_FILENAME)
        self.check_schema(self.SCHEMA_FILENAME)
        # self.check_extra_keys(self.SCHEMA_FILENAME)

    def extract(self):
        return {
            "slug": self.repo.slug,
            "tag": str(self.repo.current_tag),
            "schema": self.file_content(self.SCHEMA_FILENAME),
            "readme": self.file_content("README.md"),
            "changelog": self.file_content("CHANGELOG.md"),
        }

    def check_extra_keys(self, filename):
        with open(self.filepath(filename)) as f:
            json_data = json.load(f)

        keys = [
            "title",
            "description",
            "author",
            "contact",
            "version",
            "created_at",
            "updated_at",
            "homepage",
        ]
        for key in [k for k in keys if k not in json_data]:
            message = "Key `%s` is a required key and is missing from %s" % (
                key,
                filename,
            )
            raise InvalidSchemaException(self.repo, message)

    def check_schema(self, filename):
        try:
            tableschema.validate(self.filepath(filename))
        except tableschema.exceptions.ValidationError as e:
            errors = "; ".join(e.errors)
            message = "Schema %s is not a valid TableSchema schema. Errors: %s" % (
                filename,
                errors,
            )
            raise InvalidSchemaException(self.repo, message)

    def check_file_exists(self, filename):
        if not os.path.isfile(self.filepath(filename)):
            message = "Required file %s was not found" % filename
            raise MissingFileException(self.repo, message)

    def file_content(self, filename):
        if not os.path.isfile(self.filepath(filename)):
            return None

        with open(self.filepath(filename), "r") as f:
            return f.read()

    def filepath(self, filename):
        return os.path.join(self.git_repo.working_dir, filename)


class Repo(object):
    def __init__(self, git_url):
        super(Repo, self).__init__()
        parsed_git = giturlparse.parse(git_url)
        self.git_url = git_url
        self.git_repo = None
        self.owner = parsed_git.owner
        self.name = parsed_git.name
        self.current_tag = None

    @property
    def clone_dir(self):
        return os.path.join(self.repo_dir, self.owner, self.name)

    @property
    def repo_dir(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(current_dir, "repos")

    @property
    def slug(self):
        return "%s/%s" % (self.owner, self.name)

    def clone_or_pull(self):
        try:
            if os.path.isdir(self.clone_dir):
                git_repo = GitRepo(self.clone_dir)
                git_repo.remotes.origin.pull("refs/heads/master:refs/heads/origin")
            else:
                git_repo = GitRepo.clone_from(self.git_url, self.clone_dir)
        except Exception:
            raise GitException(self, "Cannot clone or pull Git repository")

        self.git_repo = git_repo

    def tags(self):
        if len(self.git_repo.tags) == 0:
            raise NoTagsException(self)
        return [self.parse_version(t.name) for t in self.git_repo.tags]

    def checkout_tag(self, tag):
        try:
            self.git_repo.git.checkout(tag)
        except Exception:
            raise GitException(self, "Cannot checkout tag %s" % tag)
        self.current_tag = tag

    def parse_version(self, version):
        try:
            return VersionInfo.parse(version.replace("v", ""))
        except ValueError:
            raise InvalidVersionException(self, "Version was invalid: %s" % version)


git_url = "https://github.com/AntoineAugusti/test-schema.git"
repo = Repo(git_url)
repo.clone_or_pull()
print(repo.tags(), repo.slug)
for tag in repo.tags():
    repo.checkout_tag(tag)
    TableSchemaValidator(repo).validate()
    print(TableSchemaValidator(repo).extract())
