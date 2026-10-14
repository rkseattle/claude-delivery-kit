<!-- expect errors=broken-link@12,broken-link@14,broken-link@16,broken-link@16,broken-link@18 warnings= -->
# widget

Use `<a href="manual/missing-in-code.md">` or `<img src="x.png">` here: inline code is text.
Old title: <!-- <h1>Old</h1> --> gone.
Some text <!-- TODO
replace INSTALL-COMMAND
--> and more.

A footnote whose text links somewhere.[^note]

[^note]: [guide](manual/missing-in-footnote.md)

<!-- note --> <img src="manual/missing.png" alt="a">

[a](manual/missing-one.md) and [b](manual/missing-two.md) on one line.

[x][r] and [y][r] share one broken reference.

[r]: manual/missing-reference.md

## Install

## Usage

## License

A fence left open to the end of the file is still code:

```sh
project-name --help
