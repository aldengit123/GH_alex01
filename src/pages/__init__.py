"""
页面对象模块
包含各业务页面的Page Object
"""

from .deposit_page import DepositPage
from .agent_page import AgentPage
from .sports_page import SportsPage
from .activity_page import ActivityPage

__all__ = [
    'DepositPage',
    'AgentPage',
    'SportsPage',
    'ActivityPage',
]
