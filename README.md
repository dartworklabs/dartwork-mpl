<h1 align="center"><a href="https://mpl.dartwork.io">mpl.dartwork.io</a></h1>

<p align="center"><b>Examples, gallery and docs are on <a href="https://mpl.dartwork.io">mpl.dartwork.io</a>. Start there.</b></p>

---

# dartwork-mpl

Turn on the skill in your coding agent, say "draw this", get a beautiful
chart. A thin layer on matplotlib: `Figure` and `Axes` stay native.

## Start

```bash
uv add dartwork-mpl                                            # add it to your project
npx skills add dartworklabs/dartwork-mpl --skill dartwork-mpl  # the skill, with Node
uv run dartwork-mpl install                                    # or the same skill, without Node
```

Then ask your agent for a chart.

No project? `uvx dartwork-mpl install` copies the skill into the current
folder. With pip: `pip install dartwork-mpl`, then `dartwork-mpl install`.
`npx skills add` takes the skill from GitHub; pin it to your version with
`dartworklabs/dartwork-mpl#v0.10.2`. `--skill dartwork-mpl` keeps it to this
skill: the repository also holds its own development skill, which is not for
you. The skill tells the agent when the two differ.

## Developing

Contributors and their agents start at [`CLAUDE.md`](CLAUDE.md).

## License

See [`LICENSE`](LICENSE).
