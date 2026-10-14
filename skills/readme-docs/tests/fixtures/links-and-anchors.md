<!-- expect errors=broken-link@5,broken-link@8,broken-link@13,broken-link@15,broken-link@23 warnings= -->
# widget

Same-page anchors: [install](#install), [twice](#notes-1), [punctuation](#c--net-support),
[html anchor](#custom), [top](#top), and [missing](#nowhere).

Other files: [guide](manual/guide.md#guide), [second guide](manual/guide_(v2).md#guide-version-2),
and [missing section](manual/guide.md#nope).

<a id="custom"></a>

<p>
<a
  href="manual/missing-multiline.md">attribute on its own line</a>
<a href=manual/missing-unquoted.md>unquoted</a>
<a href="manual/a&amp;b.md">an entity in the name resolves</a>
</p>

A footnote with a second paragraph.[^long]

[^long]: The first paragraph is fine.

    The second paragraph links [nowhere](manual/missing-in-footnote-continuation.md).

## Install

## Notes

## Notes

## C# & .NET support

## Usage

## License
