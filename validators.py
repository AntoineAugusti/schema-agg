import os
import shutil
import json
import tableschema

import exceptions


class TableSchemaValidator(object):
    SCHEMA_FILENAME = "schema.json"

    def __init__(self, repo):
        super(TableSchemaValidator, self).__init__()
        self.repo = repo
        self.git_repo = repo.git_repo

    @property
    def data_dir(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(current_dir, "data")

    @property
    def target_dir(self):
        tag = str(self.repo.current_tag)
        return os.path.join(self.data_dir, self.repo.slug, tag)

    def validate(self):
        self.check_file_exists("README.md")
        self.check_file_exists(self.SCHEMA_FILENAME)
        self.check_schema(self.SCHEMA_FILENAME)
        self.check_extra_keys(self.SCHEMA_FILENAME)

    def extract(self):
        files = {
            self.SCHEMA_FILENAME: self.filepath_or_none(self.SCHEMA_FILENAME),
            "README.md": self.filepath_or_none("README.md"),
            "CHANGELOG.md": self.filepath_or_none("CHANGELOG.md"),
        }

        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

        for filename, src_filepath in files.items():
            if src_filepath is not None:
                shutil.copyfile(src_filepath, self.target_filepath(filename))

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
            raise exceptions.InvalidSchemaException(self.repo, message)

    def check_schema(self, filename):
        try:
            tableschema.validate(self.filepath(filename))
        except tableschema.exceptions.ValidationError as e:
            errors = "; ".join(e.errors)
            message = "Schema %s is not a valid TableSchema schema. Errors: %s" % (
                filename,
                errors,
            )
            raise exceptions.InvalidSchemaException(self.repo, message)

    def check_file_exists(self, filename):
        if not os.path.isfile(self.filepath(filename)):
            message = "Required file %s was not found" % filename
            raise exceptions.MissingFileException(self.repo, message)

    def filepath_or_none(self, filename):
        if not os.path.isfile(self.filepath(filename)):
            return None

        return self.filepath(filename)

    def target_filepath(self, filename):
        return os.path.join(self.target_dir, filename)

    def filepath(self, filename):
        return os.path.join(self.git_repo.working_dir, filename)
