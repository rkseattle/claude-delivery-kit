<!-- expect errors=broken-link warnings= -->
# widget

## Install

````markdown
```sh
not a fence close
```
[inside a fence](docs/missing-in-fence.md)
````

~~~text
[inside a tilde fence](docs/missing-in-tilde.md)
~~~

## Usage

Inline code is not a link: `[x](docs/missing-in-code.md)`.
Angle-bracket destination: [guide](<manual/guide.md>).
Percent-encoded path: [guide](manual/gu%69de.md).
Reference definition below points at a missing file.

[missing]: docs/missing-reference.md

## License

MIT, see [LICENSE](LICENSE).
