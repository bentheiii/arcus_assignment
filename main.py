from argparse import ArgumentParser
from json import dump
from mmap import mmap

from pattern_builder import BinaryMultiPattern

parser = ArgumentParser()
parser.add_argument("source_file", help="the path to the binary file to search")
parser.add_argument("patterns_file", help="the path to the JSON file with regex patterns")
parser.add_argument("output_path", default=None, nargs='?',
                    help='optional path to write output (as json file). If ommited, the result will only print.')

if __name__ == '__main__':
    # todo doc
    args = parser.parse_args()
    with open(args.patterns_file) as patterns_file:
        builder = BinaryMultiPattern.from_file(patterns_file)

    out = []

    builder.compile()
    # we grab all the user groups that might be relevant to matches
    user_groups = list(builder.user_groups())

    with open(args.source_file, 'r+b') as file, \
            mmap(file.fileno(), 0) as mapped:
        for name, match in builder.match_all(mapped):
            # fill in only the relevant user groups for each tag
            # todo Improvement idea: instead of iterating through all user groups,
            #  only iterate through relevant user groups? For now the performance impact of this is minor
            vars_ = {}
            for group_name, group_key in user_groups:
                v = match[group_key]
                if v is not None:
                    vars_[group_name] = list(v)

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
