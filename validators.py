import os
import shutil
import json

import exceptions

import tableschema
import frontmatter


class BaseValidator(object):
    def __init__(self, repo):
        super(BaseValidator, self).__init__()
        self.repo = repo
        self.git_repo = repo.git_repo

    def validate(self):
        self.check_file_exists("README.md")

    def extract(self):
        raise NotImplementedError

    def move_files(self, files):
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

        for filename, src_filepath in files.items():
            if src_filepath is None:
                continue
            front_matter = self.front_matter_for(filename)
            # Add YAML front matter if required
            if front_matter is not None:
                content = frontmatter.dumps(
                    frontmatter.load(src_filepath, **front_matter)
                )
                with open(self.target_filepath(filename), "w") as f:
                    f.write(content)
            else:
                shutil.copyfile(src_filepath, self.target_filepath(filename))

    @property
    def data_dir(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(current_dir, "data")

    @property
    def target_dir(self):
        return os.path.join(self.data_dir, self.repo.slug, self.repo.current_version)

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

    def front_matter_for(self, filename):
        return None


class TableSchemaValidator(BaseValidator):
    SCHEMA_FILENAME = "schema.json"

    def __init__(self, repo):
        super(TableSchemaValidator, self).__init__(repo)

    def validate(self):
        super(TableSchemaValidator, self).validate()
        self.check_file_exists(self.SCHEMA_FILENAME)
        self.check_schema(self.SCHEMA_FILENAME)
        self.check_extra_keys()

    def extract(self):
        files = {
            self.SCHEMA_FILENAME: self.filepath_or_none(self.SCHEMA_FILENAME),
            "README.md": self.filepath_or_none("README.md"),
            "CHANGELOG.md": self.filepath_or_none("CHANGELOG.md"),
        }
        self.move_files(files)

    def check_extra_keys(self):
        keys = [
            "title",
            "description",
            "author",
            "contact",
            "version",
            "created",
            "updated",
            "homepage",
        ]
        for key in [k for k in keys if k not in self.schema_json_data()]:
            message = "Key `%s` is a required key and is missing from %s" % (
                key,
                self.SCHEMA_FILENAME,
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

    def front_matter_for(self, filename):
        if filename == "README.md":
            version = self.repo.current_version
            permalink = "/%s/%s.html" % (self.repo.slug, version)
            json_data = self.schema_json_data()

            return {
                "permalink": permalink,
                "title": json_data["title"],
                "version": version,
                "homepage": json_data["homepage"],
            }
        return None

    def schema_json_data(self):
        with open(self.filepath(self.SCHEMA_FILENAME)) as f:
            return json.load(f)

    def metadata(self):
        json_data = self.schema_json_data()

        return {
            "slug": self.repo.slug,
            "title": json_data["title"],
            "type": self.repo.schema_type,
            "email": self.repo.email,
            "version": self.repo.current_version,
        }
