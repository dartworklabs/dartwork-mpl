<h1 align="center"><a href="https://mpl.dartwork.io">mpl.dartwork.io</a></h1>

<p align="center"><b>Examples, gallery and docs are on <a href="https://mpl.dartwork.io">mpl.dartwork.io</a>. Start there.</b></p>

---

# dartwork-mpl

Turn on the skill in your coding agent, say "draw this", get a beautiful
chart. A thin layer on matplotlib: `Figure` and `Axes` stay native.

## Start

```bash
uv add --prerelease allow dartwork-mpl    # add it to your project
uv run dartwork-mpl install               # put the skill where agents look
```

Then ask your agent for a chart.

No project? `uvx --prerelease allow dartwork-mpl install` copies the skill into
the current folder. With pip: `pip install --pre dartwork-mpl`, then
`dartwork-mpl install`. (`--prerelease allow` / `--pre` until 0.8.0 is out.)

## Developing

Contributors and their agents start at [`CLAUDE.md`](CLAUDE.md).

## License

See [`LICENSE`](LICENSE).
