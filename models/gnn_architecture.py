"""
PyTorch Geometric (PyG) Fraud Ring Graph Neural Network Architecture
=====================================================================
Detects money laundering cycles, smurfing rings, and mule networks
by aggregating neighborhood topology and transaction volume across accounts.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from torch_geometric.nn import SAGEConv, GCNConv
    HAS_PYG = True
except ImportError:
    HAS_PYG = False


class FraudGraphSAGE(nn.Module):
    """
    GraphSAGE binary classifier for node-level fraud detection.
    Aggregates structural degree signals and volume flows from 1-hop and 2-hop neighbors.
    """
    def __init__(self, in_channels: int = 3, hidden_channels: int = 64, out_channels: int = 1, dropout: float = 0.2):
        super().__init__()
        self.dropout = dropout

        if HAS_PYG:
            self.conv1 = SAGEConv(in_channels, hidden_channels, aggr="mean")
            self.conv2 = SAGEConv(hidden_channels, hidden_channels // 2, aggr="mean")
            self.conv3 = SAGEConv(hidden_channels // 2, out_channels, aggr="mean")
            self.use_pyg = True
        else:
            # Fallback pure PyTorch neighborhood aggregation layer if PyG C-bindings differ
            self.use_pyg = False
            self.linear1 = nn.Linear(in_channels * 2, hidden_channels)
            self.linear2 = nn.Linear(hidden_channels * 2, hidden_channels // 2)
            self.linear3 = nn.Linear((hidden_channels // 2) * 2, out_channels)

    def _fallback_aggregate(self, x, edge_index, linear_layer):
        # x: [num_nodes, feat_dim]
        # edge_index: [2, num_edges]
        num_nodes = x.size(0)
        src, dst = edge_index[0], edge_index[1]

        # Aggregate neighbor features into destination nodes
        aggr = torch.zeros_like(x)
        counts = torch.zeros((num_nodes, 1), device=x.device, dtype=x.dtype)
        aggr.index_add_(0, dst, x[src])
        counts.index_add_(0, dst, torch.ones((src.size(0), 1), device=x.device, dtype=x.dtype))
        counts = torch.clamp(counts, min=1.0)
        mean_aggr = aggr / counts

        # Concatenate self and neighbor representations
        combined = torch.cat([x, mean_aggr], dim=-1)
        return linear_layer(combined)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        x: [num_nodes, in_channels]
        edge_index: [2, num_edges]
        returns: [num_nodes, 1] raw logits
        """
        if self.use_pyg:
            # Layer 1
            h = self.conv1(x, edge_index)
            h = F.relu(h)
            h = F.dropout(h, p=self.dropout, training=self.training)

            # Layer 2
            h = self.conv2(h, edge_index)
            h = F.relu(h)
            h = F.dropout(h, p=self.dropout, training=self.training)

            # Layer 3 (Output Logits)
            out = self.conv3(h, edge_index)
        else:
            # Layer 1
            h = self._fallback_aggregate(x, edge_index, self.linear1)
            h = F.relu(h)
            h = F.dropout(h, p=self.dropout, training=self.training)

            # Layer 2
            h = self._fallback_aggregate(h, edge_index, self.linear2)
            h = F.relu(h)
            h = F.dropout(h, p=self.dropout, training=self.training)

            # Layer 3
            out = self._fallback_aggregate(h, edge_index, self.linear3)

        return out

