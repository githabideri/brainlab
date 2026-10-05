"""scorer: frozen connectome circuit + learned drive/readout/heads.

Candidate-only decision scoring in the FlyBridge pattern (MIT,
swotstudio/FlyBridge): a fixed-wiring recurrent subcircuit with learned
per-edge gain, per-node leak/bias, a learned input drive, a readout over
the circuit's output nodes, and per-task linear heads that score a fixed
candidate list (argmax; low margin -> abstain). No action generation.
"""
from .circuit import Circuit, load_circuit
from .model import Scorer

__all__ = ["Circuit", "Scorer", "load_circuit"]
