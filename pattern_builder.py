import re
from collections import Mapping, Iterable
from itertools import count
from json import load


class PatternBuilder:
    def __init__(self):
        self.sub_patterns = []
        self.sub_pattern_names = []

        self.compiled = None

    def _next_pattern_marker(self):
        return b'(?P<_' + bytes(str(len(self.sub_patterns)), 'ascii') + b'>)'

    @staticmethod
    def _from_plain_pattern(pattern: str):
        # todo validate pattern
        return re.escape(bytes.fromhex(pattern))

    @staticmethod
    def _from_re_pattern(pattern: str):
        return eval("b'" + pattern + "'", {'__builtins__': None})

    @staticmethod
    def _from_nonstandard_pattern(pattern):
        raise NotImplementedError("todo")

    def add_pattern(self, pattern, name):
        trials = (
            self._from_plain_pattern,
            self._from_nonstandard_pattern,
            self._from_re_pattern
        )
        for trial in trials:
            try:
                re_pattern = trial(pattern)
            except (ValueError, SyntaxError, NotImplementedError):
                continue
            else:
                break
        else:
            raise ValueError(f'cannot parse pattern {pattern}')

        re_pattern += self._next_pattern_marker()
        self.sub_patterns.append(re_pattern)
        self.sub_pattern_names.append(name)
        # invalidate the compiled pattern
        self.compiled = None

    def compile(self):
        self.compiled = re.compile(b'|'.join(self.sub_patterns))

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
            patterns = zip(patterns_obj, count())
        else:
            raise TypeError("patterns file must be either a list or dict")

        for (pattern, name) in patterns:
            ret.add_pattern(pattern, name)
        return ret
