from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List

class ContractType(Enum):
    TERM_LOAN = auto()

class ContractStatus(Enum):
    DRAFT = auto()
    ACTIVE = auto()
    REPAID = auto()
    DEFAULTED = auto()

@dataclass
class Contract:
    # --- Fields without defaults must come first ---
    contract_type: ContractType
    creditor_id: int
    debtor_id: int
    principal: float
    term_steps: int
    issue_step: int

    # --- Fields with defaults come after ---
    interest_schedule: List[float] = field(default_factory=list)
    status: ContractStatus = ContractStatus.DRAFT
    
    # --- Convenience Properties ---
    @property
    def due_step(self) -> Optional[int]:
        if self.contract_type == ContractType.TERM_LOAN:
            return self.issue_step + self.term_steps
        return None

    @property
    def interest_amount(self) -> float:
        if self.contract_type == ContractType.TERM_LOAN:
            return sum(self.interest_schedule)
        return 0.0

    @property
    def total_repayment_amount(self) -> float:
        return self.principal + self.interest_amount

    @property
    def effective_term_rate(self) -> float:
        if self.principal == 0:
            return 0.0
        return self.interest_amount / self.principal