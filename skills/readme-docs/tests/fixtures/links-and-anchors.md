<!-- expect errors=broken-link@6,broken-link@9,broken-link@14,broken-link@16,broken-link@21,broken-link@22,broken-link@33 warnings= -->
# widget

Same-page anchors: [install](#install), [numbered](#notes-1), [third](#notes-2),
[rendered id](#user-content-usage), [punctuation](#c--net-support),
[html anchor](#custom), [top](#top), and [missing](#nowhere).

Other files: [guide](manual/guide.md#guide), [second guide](manual/guide_(v2).md#guide-version-2),
[source view line](manual/guide.md?plain=1#L1), and [missing section](manual/guide.md#nope).

<a id="custom"></a>

<p>
<a
  href="manual/missing-multiline.md">attribute on its own line</a>
<a href=manual/missing-unquoted.md>unquoted</a>
<a href="manual/a&amp;b.md">an entity in the name resolves</a>
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="manual/missing-dark.png 2x, LICENSE 1x">
  <img src="LICENSE" alt="logo" srcset="manual/logo,dark.png 1x, manual/missing-srcset.png 2x">
</picture>

<!--
[^old]: [a hidden footnote](manual/missing-in-hidden-footnote.md)
-->

A footnote with a second paragraph.[^long]

[^long]: The first paragraph is fine.

    The second paragraph links [nowhere](manual/missing-in-footnote-continuation.md).

## Install

## Notes

## Notes 1

## Notes

## C# & .NET support

## Usage

## License
