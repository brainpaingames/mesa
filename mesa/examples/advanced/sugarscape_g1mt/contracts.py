# sugarscape_g1mt/contracts.py

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List

class ContractType(Enum):
    """Enum for the different types of financial contracts."""
    TERM_LOAN = auto()
    DEMAND_DEPOSIT = auto()

class ContractStatus(Enum):
    """Enum for the status of a contract."""
    DRAFT = auto()
    ACTIVE = auto()
    REPAID = auto()
    DEFAULTED = auto()
    CLOSED = auto()

@dataclass
class Contract:
    """A generic data object representing a financial agreement between two agents."""
    # --- Fields without defaults must come first ---
    contract_type: ContractType
    creditor_id: int
    debtor_id: int
    principal: float
    
    # --- Fields with defaults come after ---
    interest_schedule: List[float] = field(default_factory=list)
    status: ContractStatus = ContractStatus.DRAFT
    term_steps: Optional[int] = None
    issue_step: Optional[int] = None
    current_principal: float = 0.0

    def __post_init__(self):
        """Initializes stateful fields after the object has been created."""
        if self.current_principal == 0.0 and self.principal > 0.0:
            self.current_principal = self.principal
    
    # --- Convenience Properties ---
    @property
    def due_step(self) -> Optional[int]:
        """The step number on which a term loan is due for repayment."""
        if self.contract_type == ContractType.TERM_LOAN and self.issue_step is not None and self.term_steps is not None:
            return self.issue_step + self.term_steps
        return None

    @property
    def interest_amount(self) -> float:
        """The total interest amount for a term loan."""
        if self.contract_type == ContractType.TERM_LOAN:
            return sum(self.interest_schedule)
        # For demand deposits, interest is handled at withdrawal, not stored here.
        return 0.0

    @property
    def total_repayment_amount(self) -> float:
        """The total amount due for a term loan (principal + interest)."""
        return self.principal + self.interest_amount

    @property
    def effective_term_rate(self) -> float:
        """The effective interest rate over the entire term of a loan."""
        if self.principal == 0:
            return 0.0
        return self.interest_amount / self.principal