# Arcus Assignment
usage: `python main.py <binary file> <pattern file> <output file>`

This assignment demonstrates pattern matching in a binary file. Inputs:
* A binary file to search
* A json file with patterns

The JSON file can be one of two forms:
* A dictionary where each pattern is mapped to a name (ie: `{"\\x00\\x01": "zero_one"}`.)
* A list of patterns, where each pattern will be named after its index in the list.

Each pattern can be in one of three forms:
* A "plain pattern", where each two characters will only match a byte matching the character's hex value. For example, the pattern `"DEADBEEF"` will only match the the sequence `b'\xde\xad\xbe\xef'` (`[222, 173, 190, 239]`). Whitespaces can be inserted into this pattern arbitrarily.
* A "nonstandard pattern", this pattern is is only formed of explicit literal characters and double capital letters or question marks. Where question marks match any byte and capital letters are wildcards that can be repeated. For example, the pattern `"\x20XXYY??XXYY"` will match a 6-byte pattern: the first is a `\x20` byte, the second, third, and fourth bytes can be any bytes, by the last two bytes must be equal to the second and third bytes. To prevent confusion with plain patterns, only the letters G-Z are acceptable as patterns.
* A "Regular pattern", this pattern must begin with a plus sign `+` (which is discarded). The remainder of the pattern is parsed as a binary regular expression pattern as-is.
# Known Issues/Quirks
* Pattern group names must not include an underscore.
* All the patterns must compile in a single REGEX expression, specifically, no two regex patterns may use named groups of the same name.
* overlapping matches will not display.
    * this can be fixed by replacing the regular expression engine with that of the regex package.