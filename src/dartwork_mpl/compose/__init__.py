"""Where slices meet: one module per slice that needs another.

A slice imports only the platform. ``compose/<slice>.py`` is the public form
of what that slice offers when it needs other slices: it calls the slices'
surfaces in order and passes one slice's functions to another as typed
arguments. It decides nothing. Only the package root imports it.
"""

__all__: list[str] = []
