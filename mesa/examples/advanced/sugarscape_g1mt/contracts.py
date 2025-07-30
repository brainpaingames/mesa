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

    @property
    def per_step_rate(self) -> float:
        """
        Returns a comparable, per-step interest rate for any contract type.
        """
        if self.contract_type == ContractType.TERM_LOAN:
            if self.term_steps and self.term_steps > 0:
                # Convert the term rate to a simple per-step rate
                return self.effective_term_rate / self.term_steps
        elif self.contract_type == ContractType.DEMAND_DEPOSIT:
            if self.interest_schedule:
                # The stored deposit rate is already a per-step rate
                return self.interest_schedule[0]
        return 0.0