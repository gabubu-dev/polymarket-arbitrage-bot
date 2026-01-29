"""
Twitter/X intelligence gathering for competitive analysis.

Uses the `bird` CLI to search for Polymarket bots, track successful traders,
and extract winning strategies.
"""

import logging
import json
import subprocess
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class BotDiscovery:
    """Represents a discovered bot/trader on Twitter."""
    twitter_handle: str
    display_name: str
    bio: str
    win_rate: Optional[float]
    total_trades: Optional[int]
    avg_profit: Optional[float]
    strategies_used: List[str]
    market_categories: List[str]
    discovery_date: datetime
    last_checked: datetime
    confidence_score: float
    tweet_url: Optional[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['discovery_date'] = self.discovery_date.isoformat()
        data['last_checked'] = self.last_checked.isoformat()
        return data


@dataclass
class StrategyInsight:
    """Represents a discovered trading strategy insight."""
    strategy_name: str
    description: str
    success_rate: float
    market_categories: List[str]
    source_handle: str
    tweet_url: str
    discovered_at: datetime
    confidence: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['discovered_at'] = self.discovered_at.isoformat()
        return data


class TwitterIntelligence:
    """
    Monitors Twitter/X for competitive intelligence on Polymarket bots.
    
    Searches for successful bots, extracts their strategies, and benchmarks
    our performance against the competition.
    """
    
    def __init__(self, config: Dict[str, Any], data_dir: str = "data"):
        self.logger = logging.getLogger("TwitterIntelligence")
        self.config = config.get('twitter_intelligence', {})
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Intelligence storage
        self.intelligence_file = self.data_dir / "competitive_intelligence.json"
        self.discovered_bots: List[BotDiscovery] = []
        self.strategy_insights: List[StrategyInsight] = []
        
        # Search queries
        self.search_queries = self.config.get('search_queries', [
            "polymarket bot",
            "polymarket trading bot",
            "prediction market bot",
            "polymarket strategy",
            "polymarket arbitrage",
            "polymarket win rate"
        ])
        
        # Load existing intelligence
        self._load_intelligence()
        
        # Last search timestamps
        self.last_search: Dict[str, datetime] = {}
        self.search_cooldown = timedelta(hours=6)  # Search every 6 hours
        
        self.logger.info("TwitterIntelligence initialized")
    
    def _load_intelligence(self) -> None:
        """Load existing competitive intelligence from disk."""
        if self.intelligence_file.exists():
            try:
                with open(self.intelligence_file, 'r') as f:
                    data = json.load(f)
                
                # Parse bot discoveries
                for bot_data in data.get('discovered_bots', []):
                    bot_data['discovery_date'] = datetime.fromisoformat(bot_data['discovery_date'])
                    bot_data['last_checked'] = datetime.fromisoformat(bot_data['last_checked'])
                    self.discovered_bots.append(BotDiscovery(**bot_data))
                
                # Parse strategy insights
                for insight_data in data.get('strategy_insights', []):
                    insight_data['discovered_at'] = datetime.fromisoformat(insight_data['discovered_at'])
                    self.strategy_insights.append(StrategyInsight(**insight_data))
                
                self.logger.info(
                    f"Loaded {len(self.discovered_bots)} bots and "
                    f"{len(self.strategy_insights)} insights from intelligence file"
                )
            except Exception as e:
                self.logger.error(f"Error loading intelligence: {e}")
    
    def _save_intelligence(self) -> None:
        """Save competitive intelligence to disk."""
        try:
            data = {
                'discovered_bots': [bot.to_dict() for bot in self.discovered_bots],
                'strategy_insights': [insight.to_dict() for insight in self.strategy_insights],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.intelligence_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug("Saved competitive intelligence")
        except Exception as e:
            self.logger.error(f"Error saving intelligence: {e}")
    
    def search_polymarket_bots(self) -> List[BotDiscovery]:
        """
        Search Twitter for Polymarket bots and traders.
        
        Returns:
            List of newly discovered bots
        """
        new_discoveries = []
        
        for query in self.search_queries:
            # Check cooldown
            last_search = self.last_search.get(query)
            if last_search and (datetime.now() - last_search) < self.search_cooldown:
                self.logger.debug(f"Skipping query '{query}' (cooldown)")
                continue
            
            try:
                self.logger.info(f"Searching Twitter for: '{query}'")
                tweets = self._bird_search(query, max_results=20)
                
                for tweet in tweets:
                    bot = self._parse_bot_from_tweet(tweet)
                    if bot and not self._is_known_bot(bot.twitter_handle):
                        new_discoveries.append(bot)
                        self.discovered_bots.append(bot)
                        self.logger.info(
                            f"Discovered new bot: @{bot.twitter_handle} "
                            f"(win rate: {bot.win_rate or 'unknown'})"
                        )
                
                self.last_search[query] = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error searching for '{query}': {e}")
        
        if new_discoveries:
            self._save_intelligence()
        
        return new_discoveries
    
    def _bird_search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Execute bird CLI search command.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of tweet dictionaries
        """
        try:
            # Execute bird search with JSON output
            cmd = [
                "bird", "search", query,
                "--json",
                "-n", str(max_results)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"Bird search failed: {result.stderr}")
                return []
            
            # Parse JSON output (bird outputs JSONL - one JSON per line)
            tweets = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        tweet = json.loads(line)
                        tweets.append(tweet)
                    except json.JSONDecodeError:
                        continue
            
            return tweets
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Bird search timeout for query: {query}")
            return []
        except Exception as e:
            self.logger.error(f"Error executing bird search: {e}")
            return []
    
    def _parse_bot_from_tweet(self, tweet: Dict) -> Optional[BotDiscovery]:
        """
        Parse bot information from a tweet.
        
        Looks for mentions of win rates, strategies, and performance metrics.
        """
        try:
            author = tweet.get('author', {})
            handle = author.get('username', '')
            display_name = author.get('name', '')
            bio = author.get('description', '')
            text = tweet.get('text', '')
            tweet_url = tweet.get('url', '')
            
            if not handle:
                return None
            
            # Extract metrics using regex patterns
            win_rate = self._extract_win_rate(text + ' ' + bio)
            total_trades = self._extract_trade_count(text + ' ' + bio)
            avg_profit = self._extract_profit(text + ' ' + bio)
            
            # Extract strategies mentioned
            strategies = self._extract_strategies(text + ' ' + bio)
            
            # Extract market categories
            categories = self._extract_categories(text + ' ' + bio)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(
                win_rate, total_trades, strategies, text
            )
            
            # Only create bot discovery if we found meaningful data
            if win_rate or total_trades or strategies or 'polymarket' in text.lower():
                return BotDiscovery(
                    twitter_handle=handle,
                    display_name=display_name,
                    bio=bio,
                    win_rate=win_rate,
                    total_trades=total_trades,
                    avg_profit=avg_profit,
                    strategies_used=strategies,
                    market_categories=categories,
                    discovery_date=datetime.now(),
                    last_checked=datetime.now(),
                    confidence_score=confidence,
                    tweet_url=tweet_url
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error parsing tweet: {e}")
            return None
    
    def _extract_win_rate(self, text: str) -> Optional[float]:
        """Extract win rate percentage from text."""
        patterns = [
            r'win rate[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s+win rate',
            r'success rate[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s+successful'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_trade_count(self, text: str) -> Optional[int]:
        """Extract total trade count from text."""
        patterns = [
            r'(\d+)\s+trades',
            r'(\d+)\s+positions',
            r'traded\s+(\d+)\s+times'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_profit(self, text: str) -> Optional[float]:
        """Extract average profit from text."""
        patterns = [
            r'\$(\d+(?:\.\d+)?)\s+profit',
            r'profit[:\s]+\$(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*%\s+returns?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_strategies(self, text: str) -> List[str]:
        """Extract strategy names from text."""
        strategies = []
        
        strategy_keywords = [
            'arbitrage', 'momentum', 'whale tracking', 'whale follow',
            'latency', 'spread trading', 'sentiment', 'probability',
            'market making', 'scalping', 'mean reversion'
        ]
        
        text_lower = text.lower()
        for keyword in strategy_keywords:
            if keyword in text_lower:
                strategies.append(keyword)
        
        return strategies
    
    def _extract_categories(self, text: str) -> List[str]:
        """Extract market categories from text."""
        categories = []
        
        category_keywords = {
            'politics': ['politics', 'election', 'presidential', 'senate'],
            'sports': ['sports', 'nfl', 'nba', 'soccer', 'football'],
            'crypto': ['crypto', 'bitcoin', 'ethereum', 'btc', 'eth'],
            'economics': ['economics', 'inflation', 'gdp', 'recession'],
            'entertainment': ['entertainment', 'oscars', 'grammy', 'movie']
        }
        
        text_lower = text.lower()
        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                categories.append(category)
        
        return categories
    
    def _calculate_confidence(self, win_rate: Optional[float], 
                            total_trades: Optional[int],
                            strategies: List[str],
                            text: str) -> float:
        """Calculate confidence score for a bot discovery."""
        score = 0.0
        
        # Win rate mentioned
        if win_rate:
            score += 0.4
            if win_rate > 60:
                score += 0.1
        
        # Trade count mentioned
        if total_trades:
            score += 0.3
            if total_trades > 100:
                score += 0.1
        
        # Strategies mentioned
        if strategies:
            score += 0.2
        
        # Polymarket explicitly mentioned
        if 'polymarket' in text.lower():
            score += 0.2
        
        return min(1.0, score)
    
    def _is_known_bot(self, handle: str) -> bool:
        """Check if bot handle is already discovered."""
        return any(bot.twitter_handle == handle for bot in self.discovered_bots)
    
    def extract_win_rates(self) -> Dict[str, float]:
        """
        Extract win rates from all discovered bots.
        
        Returns:
            Dictionary mapping handle to win rate
        """
        return {
            bot.twitter_handle: bot.win_rate
            for bot in self.discovered_bots
            if bot.win_rate is not None
        }
    
    def analyze_strategies(self) -> Dict[str, Any]:
        """
        Analyze common strategies used by successful bots.
        
        Returns:
            Strategy analysis with frequency and average success rates
        """
        strategy_data = {}
        
        for bot in self.discovered_bots:
            if bot.win_rate and bot.win_rate > 55:  # Only successful bots
                for strategy in bot.strategies_used:
                    if strategy not in strategy_data:
                        strategy_data[strategy] = {
                            'count': 0,
                            'avg_win_rate': 0.0,
                            'win_rates': []
                        }
                    
                    strategy_data[strategy]['count'] += 1
                    strategy_data[strategy]['win_rates'].append(bot.win_rate)
        
        # Calculate averages
        for strategy, data in strategy_data.items():
            if data['win_rates']:
                data['avg_win_rate'] = sum(data['win_rates']) / len(data['win_rates'])
                del data['win_rates']  # Remove raw data
        
        # Sort by frequency
        sorted_strategies = dict(
            sorted(strategy_data.items(), key=lambda x: x[1]['count'], reverse=True)
        )
        
        return sorted_strategies
    
    def benchmark_performance(self, our_win_rate: float, 
                            our_total_trades: int) -> Dict[str, Any]:
        """
        Benchmark our performance against discovered bots.
        
        Args:
            our_win_rate: Our bot's win rate
            our_total_trades: Our total number of trades
            
        Returns:
            Benchmarking analysis
        """
        if not self.discovered_bots:
            return {
                'rank': 'Unknown',
                'percentile': 0.0,
                'competitive_bots': 0,
                'better_than': 0,
                'worse_than': 0
            }
        
        # Get bots with win rates
        bots_with_rates = [
            bot for bot in self.discovered_bots 
            if bot.win_rate is not None
        ]
        
        if not bots_with_rates:
            return {
                'rank': 'Unknown',
                'percentile': 0.0,
                'competitive_bots': 0,
                'better_than': 0,
                'worse_than': 0
            }
        
        # Count bots we're better/worse than
        better_than = sum(1 for bot in bots_with_rates if our_win_rate > bot.win_rate)
        worse_than = sum(1 for bot in bots_with_rates if our_win_rate < bot.win_rate)
        
        # Calculate percentile
        percentile = (better_than / len(bots_with_rates)) * 100
        
        # Find rank
        all_rates = sorted([bot.win_rate for bot in bots_with_rates], reverse=True)
        rank = len([r for r in all_rates if r > our_win_rate]) + 1
        
        return {
            'rank': f"{rank}/{len(bots_with_rates)}",
            'percentile': round(percentile, 1),
            'competitive_bots': len(bots_with_rates),
            'better_than': better_than,
            'worse_than': worse_than,
            'top_bot_win_rate': max(bot.win_rate for bot in bots_with_rates),
            'avg_competitor_win_rate': sum(bot.win_rate for bot in bots_with_rates) / len(bots_with_rates)
        }
    
    def get_top_performers(self, n: int = 5) -> List[BotDiscovery]:
        """Get top N performing bots by win rate."""
        sorted_bots = sorted(
            [bot for bot in self.discovered_bots if bot.win_rate],
            key=lambda b: b.win_rate,
            reverse=True
        )
        return sorted_bots[:n]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get intelligence gathering statistics."""
        return {
            'total_bots_discovered': len(self.discovered_bots),
            'bots_with_win_rates': len([b for b in self.discovered_bots if b.win_rate]),
            'total_strategy_insights': len(self.strategy_insights),
            'avg_win_rate': sum(b.win_rate for b in self.discovered_bots if b.win_rate) / max(1, len([b for b in self.discovered_bots if b.win_rate])),
            'last_search': max(self.last_search.values()).isoformat() if self.last_search else None
        }
