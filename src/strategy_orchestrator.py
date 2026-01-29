"""
Strategy orchestrator for combining multiple arbitrage strategies.

Manages execution of multiple strategies with proper resource allocation,
conflict resolution, and competitive intelligence integration.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class StrategyType(Enum):
    """Available strategy types."""
    LATENCY = "latency"
    SPREAD = "spread"
    MOMENTUM = "momentum"
    WHALE = "whale"


@dataclass
class StrategyConfig:
    """Configuration for a strategy."""
    enabled: bool
    priority: int  # 1-10, higher = more important
    max_positions: int
    capital_allocation: float  # Percentage of capital (0-1)
    min_opportunity_score: float


@dataclass
class StrategyOpportunity:
    """An opportunity from a specific strategy."""
    strategy: StrategyType
    market_id: str
    direction: str
    confidence: float
    expected_profit: float
    urgency: float
    capital_required: float
    opportunity_score: float
    raw_opportunity: any  # Original opportunity object
    timestamp: datetime


class StrategyOrchestrator:
    """
    Orchestrates multiple arbitrage strategies.
    
    Responsibilities:
    - Priority management between strategies
    - Capital allocation
    - Conflict resolution (avoid competing positions)
    - Opportunity filtering and ranking
    """
    
    def __init__(self, config: Dict):
        self.logger = logging.getLogger("StrategyOrchestrator")
        self.config = config
        
        # Strategy configurations
        self._strategies: Dict[StrategyType, StrategyConfig] = {}
        self._active_positions: Dict[str, StrategyType] = {}  # market_id -> strategy
        self._strategy_positions: Dict[StrategyType, Set[str]] = {  # strategy -> market_ids
            s: set() for s in StrategyType
        }
        
        self._setup_strategies()
    
    def _setup_strategies(self):
        """Setup strategy configurations from config dict."""
        strategy_map = {
            'latency': StrategyType.LATENCY,
            'spread': StrategyType.SPREAD,
            'momentum': StrategyType.MOMENTUM,
            'whale': StrategyType.WHALE
        }
        
        for key, strategy_type in strategy_map.items():
            if key in self.config:
                cfg = self.config[key]
                self._strategies[strategy_type] = StrategyConfig(
                    enabled=cfg.get('enabled', False),
                    priority=cfg.get('priority', 5),
                    max_positions=cfg.get('max_positions', 2),
                    capital_allocation=cfg.get('capital_allocation', 0.25),
                    min_opportunity_score=cfg.get('min_opportunity_score', 0.6)
                )
    
    def evaluate_opportunities(self,
                              opportunities: Dict[StrategyType, List]
                              ) -> List[StrategyOpportunity]:
        """
        Evaluate and rank opportunities from all strategies.
        
        Args:
            opportunities: Dict mapping strategy type to list of raw opportunities
            
        Returns:
            Sorted list of scored opportunities
        """
        scored = []
        
        for strategy_type, opps in opportunities.items():
            if strategy_type not in self._strategies:
                continue
            
            config = self._strategies[strategy_type]
            if not config.enabled:
                continue
            
            # Check if strategy has capacity
            current_positions = len(self._strategy_positions[strategy_type])
            if current_positions >= config.max_positions:
                continue
            
            for opp in opps:
                # Convert to standardized format
                scored_opp = self._score_opportunity(strategy_type, opp, config)
                
                if scored_opp.opportunity_score >= config.min_opportunity_score:
                    scored.append(scored_opp)
        
        # Sort by opportunity score (descending)
        scored.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        return scored
    
    def _score_opportunity(self,
                          strategy: StrategyType,
                          raw_opp: any,
                          config: StrategyConfig) -> StrategyOpportunity:
        """Convert raw opportunity to scored opportunity."""
        
        # Extract common fields based on opportunity type
        if hasattr(raw_opp, 'market_id'):
            market_id = raw_opp.market_id
        elif hasattr(raw_opp, 'polymarket_market_id'):
            market_id = raw_opp.polymarket_market_id
        else:
            market_id = 'unknown'
        
        # Get confidence
        confidence = getattr(raw_opp, 'confidence', 0.5)
        
        # Get expected profit
        expected_profit = getattr(raw_opp, 'expected_profit', 0)
        if not expected_profit and hasattr(raw_opp, 'edge_percent'):
            expected_profit = raw_opp.edge_percent / 100
        
        # Get urgency
        urgency = getattr(raw_opp, 'urgency', getattr(raw_opp, 'urgency_score', 0.5))
        
        # Get direction
        direction = getattr(raw_opp, 'direction', 'unknown')
        
        # Calculate opportunity score
        # Composite score based on: profit, confidence, urgency, strategy priority
        profit_score = min(1.0, expected_profit * 10)  # Scale profit
        confidence_score = confidence
        urgency_score = urgency
        priority_score = config.priority / 10
        
        # Weighted combination
        opportunity_score = (
            profit_score * 0.35 +
            confidence_score * 0.30 +
            urgency_score * 0.25 +
            priority_score * 0.10
        )
        
        # Penalize if market already has position from another strategy
        if market_id in self._active_positions:
            opportunity_score *= 0.3  # Significant penalty
        
        return StrategyOpportunity(
            strategy=strategy,
            market_id=market_id,
            direction=direction,
            confidence=confidence,
            expected_profit=expected_profit,
            urgency=urgency,
            capital_required=getattr(raw_opp, 'size_usd', 100),
            opportunity_score=opportunity_score,
            raw_opportunity=raw_opp,
            timestamp=datetime.now()
        )
    
    def select_best_opportunities(self,
                                  scored_opportunities: List[StrategyOpportunity],
                                  available_capital: float,
                                  max_positions: int) -> List[StrategyOpportunity]:
        """
        Select the best opportunities given capital and position constraints.
        
        Args:
            scored_opportunities: Sorted list of scored opportunities
            available_capital: Available capital for trading
            max_positions: Maximum total positions allowed
            
        Returns:
            List of selected opportunities to execute
        """
        selected = []
        remaining_capital = available_capital
        remaining_positions = max_positions - len(self._active_positions)
        
        # Track strategy usage
        strategy_usage: Dict[StrategyType, float] = {
            s: 0 for s in StrategyType
        }
        
        for opp in scored_opportunities:
            if remaining_positions <= 0:
                break
            
            if remaining_capital < opp.capital_required:
                continue
            
            # Check strategy capital allocation
            config = self._strategies.get(opp.strategy)
            if config:
                strategy_limit = available_capital * config.capital_allocation
                if strategy_usage[opp.strategy] + opp.capital_required > strategy_limit:
                    continue
            
            # Check for conflicts
            if self._has_conflict(opp, selected):
                continue
            
            # Select this opportunity
            selected.append(opp)
            remaining_capital -= opp.capital_required
            remaining_positions -= 1
            strategy_usage[opp.strategy] += opp.capital_required
        
        return selected
    
    def _has_conflict(self,
                     opp: StrategyOpportunity,
                     selected: List[StrategyOpportunity]) -> bool:
        """Check if opportunity conflicts with already selected opportunities."""
        # Conflict: same market with opposite direction
        for selected_opp in selected:
            if (opp.market_id == selected_opp.market_id and
                opp.direction != selected_opp.direction):
                return True
        
        # Conflict: same strategy on correlated markets (risk concentration)
        # This would require market correlation data - simplified for now
        
        return False
    
    def record_position_opened(self,
                              market_id: str,
                              strategy: StrategyType) -> None:
        """Record that a position was opened."""
        self._active_positions[market_id] = strategy
        self._strategy_positions[strategy].add(market_id)
    
    def record_position_closed(self, market_id: str) -> None:
        """Record that a position was closed."""
        if market_id in self._active_positions:
            strategy = self._active_positions[market_id]
            del self._active_positions[market_id]
            self._strategy_positions[strategy].discard(market_id)
    
    def get_strategy_allocations(self) -> Dict[StrategyType, Dict]:
        """Get current capital allocations by strategy."""
        result = {}
        
        for strategy, positions in self._strategy_positions.items():
            config = self._strategies.get(strategy)
            result[strategy] = {
                'enabled': config.enabled if config else False,
                'active_positions': len(positions),
                'max_positions': config.max_positions if config else 0,
                'capital_allocation': config.capital_allocation if config else 0
            }
        
        return result
    
    def get_active_strategy_for_market(self, market_id: str) -> Optional[StrategyType]:
        """Get which strategy has an active position in a market."""
        return self._active_positions.get(market_id)
    
    def incorporate_competitive_intel(self, 
                                    strategy_analysis: Dict[str, Any]) -> None:
        """
        Incorporate competitive intelligence into strategy weights.
        
        Adjusts strategy priorities based on what successful bots are using.
        
        Args:
            strategy_analysis: Analysis from TwitterIntelligence.analyze_strategies()
        """
        self.logger.info("Incorporating competitive intelligence into strategy weights")
        
        # Map strategy names to types
        strategy_map = {
            'arbitrage': StrategyType.SPREAD,
            'latency': StrategyType.LATENCY,
            'momentum': StrategyType.MOMENTUM,
            'whale tracking': StrategyType.WHALE,
            'whale follow': StrategyType.WHALE,
        }
        
        for strategy_name, data in strategy_analysis.items():
            avg_win_rate = data.get('avg_win_rate', 0)
            count = data.get('count', 0)
            
            # Map to our strategy type
            strategy_type = strategy_map.get(strategy_name.lower())
            if not strategy_type or strategy_type not in self._strategies:
                continue
            
            config = self._strategies[strategy_type]
            
            # Increase priority if strategy is popular and successful
            if avg_win_rate > 60 and count > 2:
                old_priority = config.priority
                config.priority = min(10, config.priority + 1)
                self.logger.info(
                    f"Boosted {strategy_type.value} priority: "
                    f"{old_priority} → {config.priority} "
                    f"(competitive avg win rate: {avg_win_rate:.1f}%)"
                )
            
            # Decrease priority if strategy is underperforming
            elif avg_win_rate < 50 and count > 2:
                old_priority = config.priority
                config.priority = max(1, config.priority - 1)
                self.logger.info(
                    f"Reduced {strategy_type.value} priority: "
                    f"{old_priority} → {config.priority} "
                    f"(competitive avg win rate: {avg_win_rate:.1f}%)"
                )
    
    def adapt_to_market_winners(self, 
                               top_performers: List[Any]) -> None:
        """
        Adapt strategy based on what top performing bots are doing.
        
        Args:
            top_performers: List of BotDiscovery objects from TwitterIntelligence
        """
        if not top_performers:
            return
        
        self.logger.info(f"Adapting strategy based on {len(top_performers)} top performers")
        
        # Collect categories used by top performers
        popular_categories = {}
        popular_strategies = {}
        
        for bot in top_performers:
            # Count market categories
            for category in bot.market_categories:
                popular_categories[category] = popular_categories.get(category, 0) + 1
            
            # Count strategies
            for strategy in bot.strategies_used:
                popular_strategies[strategy] = popular_strategies.get(strategy, 0) + 1
        
        # Log insights
        if popular_categories:
            top_categories = sorted(
                popular_categories.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            self.logger.info(
                f"Top market categories by winners: "
                f"{', '.join(f'{cat} ({cnt})' for cat, cnt in top_categories)}"
            )
        
        if popular_strategies:
            top_strategies = sorted(
                popular_strategies.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            self.logger.info(
                f"Top strategies by winners: "
                f"{', '.join(f'{strat} ({cnt})' for strat, cnt in top_strategies)}"
            )
    
    def prioritize_high_profit_plays(self,
                                    opportunities: List[StrategyOpportunity],
                                    min_profit_threshold: float = 0.05) -> List[StrategyOpportunity]:
        """
        Filter and prioritize opportunities with high profit potential.
        
        Profit-first approach: rank by (profit margin × volume × confidence)
        
        Args:
            opportunities: List of opportunities to filter
            min_profit_threshold: Minimum profit margin (5% default)
            
        Returns:
            Filtered and sorted list of high-profit opportunities
        """
        # Filter by minimum profit
        high_profit = [
            opp for opp in opportunities
            if opp.expected_profit >= min_profit_threshold
        ]
        
        # Re-score with profit emphasis
        for opp in high_profit:
            # Emphasize profit in scoring (70% weight on profit)
            profit_score = min(1.0, opp.expected_profit / 0.10)  # Normalize to 10% profit
            
            opp.opportunity_score = (
                profit_score * 0.70 +
                opp.confidence * 0.20 +
                opp.urgency * 0.10
            )
        
        # Sort by new profit-focused score
        high_profit.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        self.logger.info(
            f"Prioritized {len(high_profit)}/{len(opportunities)} "
            f"high-profit opportunities (>{min_profit_threshold*100}% margin)"
        )
        
        return high_profit


class ExecutionQueue:
    """
    Priority queue for trade execution.
    
    Ensures high-urgency opportunities get executed first.
    """
    
    def __init__(self, max_concurrent: int = 3):
        self.logger = logging.getLogger("ExecutionQueue")
        self.max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executing: Set[str] = set()
    
    async def submit(self, 
                    opportunity: StrategyOpportunity,
                    execute_fn) -> any:
        """
        Submit an opportunity for execution.
        
        Args:
            opportunity: The opportunity to execute
            execute_fn: Async function to execute the trade
            
        Returns:
            Execution result
        """
        # Priority is inverse of urgency (lower number = higher priority)
        priority = 1.0 - opportunity.urgency
        
        # Add to queue
        await self._queue.put((priority, opportunity, execute_fn))
        
        # Process queue
        return await self._process()
    
    async def _process(self):
        """Process the execution queue."""
        async with self._semaphore:
            if self._queue.empty():
                return None
            
            priority, opportunity, execute_fn = await self._queue.get()
            
            # Check not already executing for this market
            if opportunity.market_id in self._executing:
                return None
            
            self._executing.add(opportunity.market_id)
            
            try:
                result = await execute_fn(opportunity)
                return result
            except Exception as e:
                self.logger.error(f"Execution error: {e}")
                return None
            finally:
                self._executing.discard(opportunity.market_id)