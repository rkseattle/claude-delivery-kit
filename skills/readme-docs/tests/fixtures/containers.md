<!-- expect errors=broken-link@9,broken-link@19,broken-link@26,broken-link@35 warnings=heading-skip -->
# widget

> ```sh
> pip install widget
> project-name --help

After a quote ends, its open fence is closed: this line is prose.
[after a quote's open fence](manual/missing-after-quote.md)

````markdown
> [!NOTE]
> ```sh
> make
> ```
[a link shown inside the markdown sample](manual/missing-in-sample.md)
````

[after the sample fence](manual/missing-after-sample.md)

<!--
```sh
old instructions
-->

[after a comment holding a fence](manual/missing-after-comment.md)

> a quoted note
---

### Deep heading after a thematic break, not after an H2

 - an indented list item

    [a continuation paragraph, not code](manual/missing-in-continuation.md)

## Install

## Usage

## License
