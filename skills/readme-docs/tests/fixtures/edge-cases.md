<!-- expect errors=broken-link,placeholder warnings=absolute-path,absolute-path,fence-language -->
# widget

Write `<!--` to open an HTML comment; the rest of this file is still checked.
Inline code still counts: run `cd /home/someone/widget`, then `INSTALL-COMMAND`.
The --project-name option and a protocol-relative [mirror](//example.com/widget) are fine.

## Install
    [indented code right under a heading](manual/missing-under-heading.md)

```sh
cargo new project-name
cd /home/someone/project-name
```

    [an indented code block](manual/missing-in-indented-code.md)
	[a tab-indented code block](manual/missing-in-tab-code.md)

1. Build it:
    ```
    [inside a list-item fence](manual/missing-in-list-fence.md)
    ```
- a list item
    [a continuation line](manual/guide.md)

## Usage

Links with a query and a title: [guide](manual/guide.md?plain=1 "The guide").
A reference definition in angle brackets:

[guide-ref]: <manual/guide.md>

Wrong case, a 404 on GitHub: [license](license).

## License

MIT, see [LICENSE](LICENSE).
