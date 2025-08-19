"""
Services package for Diet NFL Betting application

Contains service classes for external API integrations and business logic.
"""

from .espn_service import ESPNService, update_nfl_games

__all__ = ['ESPNService', 'update_nfl_games']