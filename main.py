from argparse import ArgumentParser
from json import dump
from mmap import mmap

from pattern_builder import PatternBuilder

parser = ArgumentParser()
parser.add_argument("source_file")
parser.add_argument("patterns_file")
parser.add_argument("output_path", default=None, nargs='?')

if __name__ == '__main__':
    args = parser.parse_args()
    with open(args.patterns_file) as patterns_file:
        builder = PatternBuilder.from_file(patterns_file)

    out = []

    builder.compile()
    var_groups = [k for k in builder.compiled.groupindex.keys() if not k.startswith("_")]

    with open(args.source_file, 'r+b') as file, \
            mmap(file.fileno(), 0) as mapped:
        for name, match in builder.match_all(mapped):
            vars_ = {}
            for vg in var_groups:
                v = match[vg]
                if v is not None:
                    vars_[vg] = v

            out.append({
                "start": match.start(),
                "end": match.end(),
                "match_name": name,
                "vars": vars_
            })

    if args.output_path:
        with open(args.output_path, 'w') as out_file:
            dump(out, out_file)
    else:
        for d in out:
            print(d)