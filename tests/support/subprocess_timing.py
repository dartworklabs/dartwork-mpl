"""Wall-clock bounds for tests that wait on a freshly started Python process.

A cold start (spawn, imports, an MCP handshake) is CPU bound, so it stretches
with the host's load. Main CI runs on ml-main, which it shares with other
projects' jobs: on 2026-11-14 its load was 320 on 64 cores, and a 30 s
handshake bound, a 20 s marker bound and a 2 s render timeout each overran in
main runs 43517408460 and 43518814853.

Measured the same day on ml-a6000 (32 cores) on the paths these tests take,
idle and beside 160 equal-priority busy loops (the same 5x oversubscription):

==============================================  =======  ============
path                                            idle     5x load
==============================================  =======  ============
``dartwork-mpl-mcp``: spawn, initialize, exit   1.5 s    5.1-22.6 s
stdio server: spawn to an initialized client    1.4 s    3.3-11.9 s
render child: request to its first marker       0.5 s    1.3-6.4 s
render runner: spawn to the first user line     0.2 s    0.7-2.6 s
==============================================  =======  ============

ml-main ran past the 5x figures (over 30 s for the handshake), so each bound
is about twice the worst time scaled to it. They stop a hung test; none of
them is a speed claim, and a test that passes waits only as long as the work
takes, except where it needs a timeout to fire (``RUNNER_TIMEOUT_S``).
"""

COLD_START_S = 60.0
"""Bound one cold start up to an MCP handshake, its exit or a child's marker."""

RUNNER_TIMEOUT_S = 8.0
"""Render timeout for a test that needs it to fire after the user code began.

The runner imports pyplot before the first user line, so a 2 s timeout fired
before a loaded child got there. A test with this timeout waits all of it.
"""
