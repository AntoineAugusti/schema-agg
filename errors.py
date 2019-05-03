# -*- coding: utf-8 -*-
import json
from copy import deepcopy
from collections import defaultdict
from hashlib import md5

from exceptions import ValidationException


class ErrorsCache(object):
    CACHE_FILE = "cache/errors.json"

    def __init__(self):
        super(ErrorsCache, self).__init__()
        with open(self.CACHE_FILE) as json_file:
            self.errors = json.load(json_file)
        self.new_errors = deepcopy(self.errors)

    def has_new_errors(self, email, exceptions):
        if email not in self.errors:
            return True
        return self.errors[email] != self.hash(exceptions)

    def add_error(self, email, exceptions):
        self.new_errors[email] = self.hash(exceptions)

    def save_cache(self):
        with open(self.CACHE_FILE, "w") as outfile:
            json.dump(self.new_errors, outfile)

    def hash(self, exceptions):
        return md5(str(exceptions).encode("utf-8")).hexdigest()


class ErrorBag(object):
    def __init__(self):
        super(ErrorBag, self).__init__()
        self.errors_by_slug = defaultdict(list)
        self.errors_by_email = defaultdict(list)

    def add(self, exception):
        if not isinstance(exception, ValidationException):
            raise ValueError(
                "Exception should be a ValidationException got %s" % type(exception)
            )
        self.errors_by_slug[exception.repo.slug].append(exception)
        self.errors_by_email[exception.repo.email].append(exception)
