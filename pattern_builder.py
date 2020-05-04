import re
from collections import Mapping, Iterable
from itertools import count
from json import load


class BinaryMultiPattern:
    """
    A class that holds multiple binary patterns and compiles them together
    """
    def __init__(self, check_regular_patterns=True):
        """
        :param check_regular_patterns: if set to true, each regex pattern will be checked for correctness before
         being added.
        """
        self.sub_patterns = []  # each pattern is converted to a (non-compiled) binary regex pattern
        self.sub_pattern_names = []

        self.check_regular_patterns = check_regular_patterns
        self._known_group_names = set() if check_regular_patterns else None

        self.compiled = None  # this variable will store the compiled, composed pattern of all the sub-patterns

    def _next_pattern_marker(self):
        # each sub-pattern is identified by an empty named group with a unique name.
        # this function gets the empty group pattern to append to the end of the sub-pattern
        return b'(?P<_' + bytes(str(len(self.sub_patterns)), 'ascii') + b'>)'

    @staticmethod
    def _from_plain_pattern(pattern: str):
        """
        generate a regex pattern from a plaintext pattern, or raise ValueError on failure
        """
        if not re.fullmatch(
                r"[0-9a-fA-F\s]+",
                pattern
        ):
            raise ValueError("string is not a plain pattern")
        return re.escape(bytes.fromhex(pattern))

    def _from_nonstandard_pattern(self, pattern):
        """
        generate a regex pattern from a nonstandard pattern, or raise ValueError on failure
        """
        if not re.fullmatch(
                r"(\\x[0-9a-f]{2}|((?P<half>[G-Z?])(?P=half)))+",
                pattern
        ):
            raise ValueError("string is not a nonstandard pattern")

        # since we want to introduce multiple named groups that need to compile alongside other non-standard patterns,
        # we need each named group to have different name, we will use the sub-pattern index to differentiate
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

        # replace all XX tokens with regex patterns
        re_pattern = re.sub(
            r"([G-Z?])\1",
            replace,
            pattern
        )
        # weirdly enough, this is probably the best way to turn escaped \x chars to actual byte values.
        return eval("b'" + re_pattern + "'", {'__builtins__': None})

    def _from_re_pattern(self, pattern: str):
        """
        generate a regex pattern from a regular pattern, or raise ValueError on failure
        """
        if not pattern.startswith("+"):
            raise ValueError("regex pattern must start with plus sign")
        pattern = pattern[1:]
        ret = eval("b'" + pattern + "'", {'__builtins__': None})
        if self.check_regular_patterns:
            # check hat we compile
            try:
                compiled = re.compile(ret)
            except re.error as e:
                raise ValueError from e
            names = set(compiled.groupindex.keys())
            # check that none of the group names are forbidden
            if any(('_' in g) for g in names):
                # todo this restriction can be relaxed if necessary
                raise ValueError("group names cannot include an underscore")
            # check that none of the group names repeat
            if self._known_group_names.intersection(names):
                raise ValueError("repeated group names")
            self._known_group_names.update(names)
        return ret

    def add_pattern(self, pattern, name):
        """
        Add a pattern with a name to the multi-pattern
        """
        # try each pattern parsing in order of complexity
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
        """
        compile the multi-pattern into one compiled regular expression
        """
        self.compiled = re.compile(b'|'.join(self.sub_patterns))

    def user_groups(self):
        """
        :return: an iterator of pairs for each user defined named capture group
         where the first value is the display name for the capture group and the second is the key for the group in
         matches
        """
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
        """
        :return: an iterator over all the matched patterns in src. Each match will yield the name of the matched
        sub-pattern, as well as the Match object.
        """
        if self.compiled is None:
            self.compile()
        for match in self.compiled.finditer(src):
            sub_index = int(match.lastgroup[1:])
            yield self.sub_pattern_names[sub_index], match

    @classmethod
    def from_file(cls, file):
        """
        Import patterns from open json file
        """
        ret = cls()

        patterns_obj = load(file)
        if isinstance(patterns_obj, Mapping):
            patterns = patterns_obj.items()
        elif isinstance(patterns_obj, Iterable):
            # in case of list, each pattern is named after its index
            patterns = zip(patterns_obj, map(str, count()))
        else:
            raise TypeError("patterns file must be either a list or dict")

        for (pattern, name) in patterns:
            ret.add_pattern(pattern, name)
        return ret
