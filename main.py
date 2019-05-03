# -*- coding: utf-8 -*-
import os
from collections import defaultdict

import exceptions
from validators import TableSchemaValidator

import yaml
import giturlparse
from semver import VersionInfo
from git import Repo as GitRepo
from git.exc import GitError


class ErrorBag(object):
    def __init__(self):
        super(ErrorBag, self).__init__()
        self.errors_by_slug = defaultdict(list)
        self.errors_by_email = defaultdict(list)

    def add(self, exception):
        if not isinstance(exception, exceptions.ValidationException):
            raise ValueError(
                "Exception should be a ValidationException got %s" % type(exception)
            )
        self.errors_by_slug[exception.repo.slug].append(exception)
        self.errors_by_email[exception.repo.email].append(exception)


class Repo(object):
    SCHEMA_TYPES = ["tableschema"]

    def __init__(self, git_url, email, schema_type):
        super(Repo, self).__init__()
        parsed_git = giturlparse.parse(git_url)
        self.git_url = git_url
        self.email = email
        self.git_repo = None
        self.owner = parsed_git.owner
        self.name = parsed_git.name
        self.current_tag = None
        if schema_type not in self.SCHEMA_TYPES:
            raise exceptions.InvalidSchemaTypeException(
                self,
                "`%s` is not a supported schema type. Supported: %s"
                % (schema_type, ",".join(self.SCHEMA_TYPES)),
            )
        self.schema_type = schema_type

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
        except GitError:
            raise exceptions.GitException(self, "Cannot clone or pull Git repository")

        self.git_repo = git_repo

    def tags(self):
        if self.git_repo is None or len(self.git_repo.tags) == 0:
            raise exceptions.NoTagsException(self, "Cannot found tags")
        return [self.parse_version(t.name) for t in self.git_repo.tags]

    def checkout_tag(self, tag):
        try:
            self.git_repo.git.checkout(tag)
        except GitError:
            raise exceptions.GitException(self, "Cannot checkout tag %s" % tag)
        self.current_tag = tag

    def parse_version(self, version):
        try:
            return VersionInfo.parse(version.replace("v", ""))
        except ValueError:
            raise exceptions.InvalidVersionException(
                self, "Version was invalid: %s" % version
            )


errors = ErrorBag()

with open("repertoires.yml", "r") as f:
    config = yaml.safe_load(f)

for repertoire_slug, conf in config.items():
    print(conf)
    try:
        repo = Repo(conf["url"], conf["email"], conf["type"])
        repo.clone_or_pull()
    except exceptions.ValidationException as e:
        errors.add(e)
        continue

    try:
        tags = repo.tags()
    except exceptions.ValidationException as e:
        errors.add(e)
        continue

    for tag in tags:
        try:
            repo.checkout_tag(tag)
            TableSchemaValidator(repo).validate()
            TableSchemaValidator(repo).extract()
        except exceptions.ValidationException as e:
            errors.add(e)

print(errors.errors_by_slug)
print(errors.errors_by_email)
