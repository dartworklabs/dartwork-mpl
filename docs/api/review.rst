Review Loop
===========

One call for the render–inspect–revise loop: save the figure, keep every
validation finding, summarize what the figure shows and, for a revision, list
how that summary differs from the previous review. ``dm.review`` wraps
:func:`~dartwork_mpl.save_formats` and :func:`~dartwork_mpl.validate_figure`;
it adds no check, no fix and no style, and it never decides whether a change
was requested. ``review`` is listed in ``dartwork_mpl.EXPERIMENTAL``: its
summary fields may still change in a minor release.

Example
-------

.. snippet: no-run
.. code-block:: python

   import dartwork_mpl as dm

   r1 = dm.review(fig, "output/figure-v1")      # PNG + PDF + figure-v1.review.json
   r1.findings                                   # every validate_figure finding
   r1.complete                                   # False if a check could not run

   # The revision script redraws the figure with one asked change.
   r2 = dm.review(fig, "output/figure-v2", baseline="output/figure-v1",
                  allow=["axes[0].ylabel.*"])
   r2.changes      # every summary entry that differs, by path
   r2.unexpected   # the changes no allow= pattern covers

``complete`` means every check ran; it is not a pass. A failure to save raises
before any check runs. Change paths look like ``axes[0].ylabel.text``,
``axes[0].series[1].color``, ``figure.size_in``; in ``allow=`` patterns ``*``
is the only wildcard, so ``axes[*].position`` matches any Axes.

API
---

.. autofunction:: dartwork_mpl.review

.. autoclass:: dartwork_mpl.figure_review.Review
   :members: warnings, unexpected, to_dict

.. autoclass:: dartwork_mpl.figure_review.Change
   :members: to_dict
