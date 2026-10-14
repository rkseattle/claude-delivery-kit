<!-- expect errors=broken-link@14,broken-link@18,placeholder@9,placeholder@20 warnings=absolute-path@9 -->
# widget

A one-word footnote is not a link.[^1]

[^1]: Footnote.

<p align="center">
project-name INSTALL-COMMAND /Users/someone/widget
</p>

<!-- The parser turns the break inside the code span below into a space, so the link after it reports one line early: the documented limit. -->
Some `code
span` and <span
title="x">t</span> then [bad](manual/missing-after-multiline-span.md).

x ![alt
text](LICENSE) then [bad2](manual/missing-after-multiline-alt.md).

An ![SPDX-ID badge](LICENSE) here.

## Install

## Usage

## License
