import re
from collections import Mapping, Iterable
from itertools import count
from json import load


class PatternBuilder:
    def __init__(self, check_regular_patterns=True):
        self.sub_patterns = []
        self.sub_pattern_names = []

        self.check_regular_patterns = check_regular_patterns
        self._known_group_names = set() if check_regular_patterns else None

        self.compiled = None

    def _next_pattern_marker(self):
        return b'(?P<_' + bytes(str(len(self.sub_patterns)), 'ascii') + b'>)'

    @staticmethod
    def _from_plain_pattern(pattern: str):
        if not re.fullmatch(
                r"[0-9a-fA-F\s]+",
                pattern
        ):
            raise ValueError("string is not a plain pattern")
        return re.escape(bytes.fromhex(pattern))

    def _from_re_pattern(self, pattern: str):
        if not pattern.startswith("+"):
            raise ValueError("regex pattern must start with plus sign")
        pattern = pattern[1:]
        ret = eval("b'" + pattern + "'", {'__builtins__': None})
        if self.check_regular_patterns:
            try:
                compiled = re.compile(ret)
            except re.error as e:
                raise ValueError from e
            names = set(compiled.groupindex.keys())
            if any(('_' in g) for g in names):
                raise ValueError("group names cannot include an underscore")
            if self._known_group_names.intersection(names):
                raise ValueError("repeated group names")
            self._known_group_names.update(names)
        return ret

    def _from_nonstandard_pattern(self, pattern):
        if not re.fullmatch(
                r"(\\x[0-9a-f]{2}|((?P<half>[G-Z?])(?P=half)))+",
                pattern
        ):
            raise ValueError("string is not a nonstandard pattern")

        n = len(self.sub_patterns)

        seen_vars = set()

        def replace(match):
            token = match[1]
            if token == "?":
                return "."
            if token in seen_vars:
                return f"(?P={token}_{n})"
            else:
                seen_vars.add(token)
                return f"(?P<{token}_{n}>.)"

        re_pattern = re.sub(
            r"([G-Z?])\1",
            replace,
            pattern
        )
        return eval("b'" + re_pattern + "'", {'__builtins__': None})

    def add_pattern(self, pattern, name):
        trials = (
            self._from_plain_pattern,
            self._from_nonstandard_pattern,
            self._from_re_pattern
        )
        errs = []
        for trial in trials:
            try:
                re_pattern = trial(pattern)
            except (ValueError, SyntaxError) as e:
                errs.append(e)
                continue
            else:
                break
        else:
            raise ValueError(f'cannot parse pattern {pattern}:\n'+'\n'.join(str(e) for e in errs))

        re_pattern += self._next_pattern_marker()
        self.sub_patterns.append(re_pattern)
        self.sub_pattern_names.append(name)
        # invalidate the compiled pattern
        self.compiled = None

    def compile(self):
        self.compiled = re.compile(b'|'.join(self.sub_patterns))

    def user_groups(self):
        if self.compiled is None:
            self.compile()
        for group_key in self.compiled.groupindex.keys():
            r_ind = group_key.rfind("_")
            if r_ind == 0:
                continue
            if r_ind < 0:
                name = group_key
            else:
                name = group_key[:r_ind]
            yield name, group_key

    def match_all(self, src):
        if self.compiled is None:
            self.compile()
        for match in self.compiled.finditer(src):
            sub_index = int(match.lastgroup[1:])
            yield self.sub_pattern_names[sub_index], match

    @classmethod
    def from_file(cls, file):
        ret = cls()

        patterns_obj = load(file)
        if isinstance(patterns_obj, Mapping):
            patterns = patterns_obj.items()
        elif isinstance(patterns_obj, Iterable):
            patterns = zip(patterns_obj, map(str, count()))
        else:
            raise TypeError("patterns file must be either a list or dict")

        for (pattern, name) in patterns:
            ret.add_pattern(pattern, name)
        return ret
