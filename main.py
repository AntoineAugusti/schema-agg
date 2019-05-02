import os

import giturlparse
from semver import VersionInfo
from git import Repo as GitRepo


class ValidationException(Exception):
    def __init__(self, repo, message=None):
        if message is None:
            message = "An error occured with repo: %s" % repo
        super(ValidationException, self).__init__(message)
        self.repo = repo


class NoTagsException(ValidationException):
    pass


class MissingFileException(ValidationException):
    pass


class InvalidVersionException(ValidationException):
    pass


class TableSchemaValidator(object):
    def __init__(self, repo):
        super(TableSchemaValidator, self).__init__()
        self.repo = repo

    def validate():
        pass


class Repo(object):
    def __init__(self, git_url):
        super(Repo, self).__init__()
        parsed_git = giturlparse.parse(git_url)
        self.git_url = git_url
        self.repo = None
        self.owner = parsed_git.owner
        self.name = parsed_git.name

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
        if os.path.isdir(self.clone_dir):
            print("pull")
            git_repo = GitRepo(self.clone_dir)
            git_repo.remotes.origin.pull("refs/heads/master:refs/heads/origin")
        else:
            print("clone")
            git_repo = GitRepo.clone_from(self.git_url, self.clone_dir)

        self.repo = git_repo

    def tags(self):
        if len(self.repo.tags) == 0:
            raise NoTagsException(self.repo)
        return [self.parse_version(t.name) for t in self.repo.tags]

    def checkout_tag(self, tag):
        self.repo.git.checkout(tag)

    def parse_version(self, version):
        try:
            return VersionInfo.parse(version.replace("v", ""))
        except ValueError:
            raise InvalidVersionException(
                self.repo, "Version was invalid: %s" % version
            )


git_url = "https://github.com/AntoineAugusti/test-schema.git"
repo = Repo(git_url)
repo.clone_or_pull()
print(repo.tags(), repo.slug)
