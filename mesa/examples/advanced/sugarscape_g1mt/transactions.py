# sugarscape_g1mt/transactions.py

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, List

# --- Core Data Structures for Economic Transactions ---

class AssetType(Enum):
    """A central registry for all transferable asset types in the simulation."""
    SUGAR = auto()
    DEMAND_DEPOSIT = auto()
    # EQUITY_SHARE = auto() # Future-proofing: New asset types will be added here.


@dataclass(frozen=True)
class TransferLeg:
    """
    A simple, immutable data object representing a single, one-way asset transfer.
    This is a "fact" or a "line item" in a larger transaction.
    """
    asset_type: AssetType
    amount: float
    source_agent_id: int
    dest_agent_id: int
    asset_id: Optional[int] = None # e.g., the contract_id for a DEMAND_DEPOSIT


# A TransactionManifest is the complete blueprint for a trade. It's a list of
# TransferLegs that should be executed atomically.
TransactionManifest = List[TransferLeg]
