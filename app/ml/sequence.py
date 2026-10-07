"""First-order Markov model of legitimate behavioural state sequences.

Fitted on legitimate training events only. `nll` is the mean negative log-likelihood
of a recent state sequence: high values mean the *order* of recent actions is unusual.
"""
import numpy as np
from .features import N_TOKENS


class SequenceModel:
    def __init__(self, log_start, log_trans):
        self.log_start, self.log_trans = np.asarray(log_start), np.asarray(log_trans)

    @classmethod
    def fit(cls, sequences, alpha=1.0):
        start = np.full(N_TOKENS, alpha)
        trans = np.full((N_TOKENS, N_TOKENS), alpha)
        for seq in sequences:
            start[seq[0]] += 1
            for a, b in zip(seq, seq[1:]):
                trans[a, b] += 1
        return cls(np.log(start / start.sum()), np.log(trans / trans.sum(axis=1, keepdims=True)))

    def nll(self, seq):
        if len(seq) < 2:
            return float(-self.log_start[seq[0]])
        return float(-np.mean([self.log_trans[a, b] for a, b in zip(seq, seq[1:])]))
