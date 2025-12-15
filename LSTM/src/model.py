import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class LSTMMDN(nn.Module):
    def __init__(self, num_segments: int, emb_dim: int, hidden_size: int, num_layers: int, K: int, num_features: int):
        super().__init__()
        self.K = K
        self.emb = nn.Embedding(num_segments, emb_dim)
        self.lstm = nn.LSTM(input_size=num_features + emb_dim,
                            hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 64)
        self.pi = nn.Linear(64, K)
        self.mu = nn.Linear(64, K)
        self.log_sigma = nn.Linear(64, K)

    def forward(self, x, seg_id):
        """
        x: (B, T, F)  where F=num_features
        seg_id: (B,)
        """
        B, T, Fdim = x.shape
        e = self.emb(seg_id)              # (B, emb_dim)
        e = e[:, None, :].expand(B, T, e.shape[-1])
        h_in = torch.cat([x, e], dim=-1)  # (B, T, F+emb_dim)

        out, _ = self.lstm(h_in)
        h = out[:, -1, :]
        h = F.relu(self.fc(h))

        pi = F.softmax(self.pi(h), dim=-1)
        mu = self.mu(h)
        sigma = torch.exp(self.log_sigma(h)).clamp(min=1e-4)
        return pi, mu, sigma


def mdn_nll(y, pi, mu, sigma):
    """
    y: (B, 1)  (normalized)
    """
    y = y.expand_as(mu)
    coef = 1.0 / (sigma * math.sqrt(2.0 * math.pi))
    exp_term = torch.exp(-0.5 * ((y - mu) / sigma) ** 2)
    comp = coef * exp_term
    mix = torch.sum(pi * comp, dim=-1).clamp(min=1e-12)
    return -torch.mean(torch.log(mix))
