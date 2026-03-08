# Designed for AI Agents

Perhaps the most critical issue with wrapper libraries in modern development workflows is **AI coding agent inefficiency**.

AI agents (like Cursor, GitHub Copilot, or conversational agents) face significant challenges when working with highly abstracted libraries:

- **Training data scarcity**: Less popular libraries have fewer examples in training data.
- **API uncertainty**: Agents may hallucinate non-existent methods or parameters.
- **Internal behavior opacity**: Agents cannot reliably predict how wrappers transform their inputs.
- **Version sensitivity**: Wrapper APIs change more frequently than matplotlib's stable core.

## AI-Native Visualization

dartwork-mpl is built from the ground up for **Vibe Coding** and AI-assisted development workflows.

Because we use pure matplotlib under the hood, coding agents already know exactly how to use it. matplotlib is arguably one of the most heavily represented libraries in any LLM's Python training data.

Agents can reliably:

- Generate correct matplotlib code
- Understand and modify existing matplotlib code
- Debug issues effectively
- Suggest optimizations based on established patterns

## Context Prompts vs. Predefined Functions

Instead of memorizing a library of specialized plot functions, you can describe what you want to an AI coding agent:

```text
"Create a publication-quality line plot with two y-axes,
use dartwork-mpl's scientific style, and optimize the layout"
```

The agent generates correct code because the underlying matplotlib API is well-known, and dartwork-mpl's utilities (`dm.style.use`, `dm.simple_layout`) are simple, predictable, and transparent.

### Efficient Collaboration Example

```python
# AI agents can reliably generate this because it's standard matplotlib
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(6)))
ax.plot(data['x'], data['y'], color='oc.blue5', label='Measurement')
ax.fill_between(data['x'], data['y_low'], data['y_high'],
                color='oc.blue2', alpha=0.3, label='Confidence')
ax.set_xlabel('Time [hours]')
ax.set_ylabel('Temperature [°C]')
ax.legend(loc='upper right', fontsize=dm.fs(-1))

# dartwork-mpl handles the tedious margin calculations
dm.simple_layout(fig)
```

By sticking to standard matplotlib for structure and providing thin styling/layout helpers, dartwork-mpl eliminates the friction between what you want to draw and what the AI understands how to code.
