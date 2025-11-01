"""
Performance Analysis Module
Calculates performance metrics and generates reports
"""

import pandas as pd
import numpy as np
from typing import List, Dict


class PerformanceAnalyzer:
    """Analyzes trading performance and calculates metrics"""
    
    def __init__(self, closed_trades: List[Dict], daily_equity_curve: List[Dict]):
        self.closed_trades = closed_trades
        self.daily_equity_curve = daily_equity_curve
    
    def calculate_basic_metrics(self) -> dict:
        """
        Calculate basic performance metrics
        
        Returns:
            dict: Basic metrics
        """
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'avg_r_multiple': 0
            }
        
        total_trades = len(self.closed_trades)
        winners = [t for t in self.closed_trades if t['pnl'] > 0]
        losers = [t for t in self.closed_trades if t['pnl'] <= 0]
        
        win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in self.closed_trades)
        avg_win = np.mean([t['pnl'] for t in winners]) if winners else 0
        avg_loss = np.mean([t['pnl'] for t in losers]) if losers else 0
        
        total_wins = sum(t['pnl'] for t in winners)
        total_losses = abs(sum(t['pnl'] for t in losers))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        avg_r_multiple = np.mean([t['r_multiple'] for t in self.closed_trades])
        
        return {
            'total_trades': total_trades,
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_r_multiple': avg_r_multiple
        }
    
    def calculate_risk_metrics(self) -> dict:
        """
        Calculate risk-adjusted metrics
        
        Returns:
            dict: Risk metrics
        """
        if not self.daily_equity_curve or len(self.daily_equity_curve) < 2:
            return {
                'cagr': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'calmar_ratio': 0
            }
        
        df = pd.DataFrame(self.daily_equity_curve)
        
        # Calculate daily returns
        df['returns'] = df['equity'].pct_change()
        
        # CAGR
        initial_equity = df['equity'].iloc[0]
        final_equity = df['equity'].iloc[-1]
        num_years = len(df) / 252  # Assuming 252 trading days per year
        
        if num_years > 0 and initial_equity > 0:
            cagr = (pow(final_equity / initial_equity, 1 / num_years) - 1) * 100
        else:
            cagr = 0
        
        # Max Drawdown
        cumulative = df['equity']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # Sharpe Ratio (annualized)
        returns = df['returns'].dropna()
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std()
        else:
            sharpe_ratio = 0
        
        # Sortino Ratio (annualized)
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0 and negative_returns.std() > 0:
            sortino_ratio = np.sqrt(252) * returns.mean() / negative_returns.std()
        else:
            sortino_ratio = 0
        
        # Calmar Ratio
        if max_drawdown != 0:
            calmar_ratio = cagr / abs(max_drawdown)
        else:
            calmar_ratio = 0
        
        return {
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio
        }
    
    def calculate_trade_statistics(self) -> dict:
        """
        Calculate trade-level statistics
        
        Returns:
            dict: Trade statistics
        """
        if not self.closed_trades:
            return {
                'avg_hold_days': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0,
                'exit_reasons': {}
            }
        
        avg_hold_days = np.mean([t['hold_days'] for t in self.closed_trades])
        
        # Calculate consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.closed_trades:
            if trade['pnl'] > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
        
        # Exit reasons breakdown
        exit_reasons = {}
        for trade in self.closed_trades:
            reason = trade['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        return {
            'avg_hold_days': avg_hold_days,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'exit_reasons': exit_reasons
        }
    
    def generate_full_report(self) -> dict:
        """
        Generate complete performance report
        
        Returns:
            dict: Complete performance report
        """
        basic_metrics = self.calculate_basic_metrics()
        risk_metrics = self.calculate_risk_metrics()
        trade_stats = self.calculate_trade_statistics()
        
        return {
            **basic_metrics,
            **risk_metrics,
            **trade_stats
        }
    
    def print_report(self):
        """Print formatted performance report"""
        report = self.generate_full_report()
        
        print("\n" + "=" * 60)
        print("PERFORMANCE REPORT")
        print("=" * 60)
        
        print("\n--- BASIC METRICS ---")
        print(f"Total Trades: {report['total_trades']}")
        print(f"Winners: {report['winners']}")
        print(f"Losers: {report['losers']}")
        print(f"Win Rate: {report['win_rate']:.2f}%")
        print(f"Total P&L: ₹{report['total_pnl']:,.2f}")
        print(f"Average Win: ₹{report['avg_win']:,.2f}")
        print(f"Average Loss: ₹{report['avg_loss']:,.2f}")
        print(f"Profit Factor: {report['profit_factor']:.2f}")
        print(f"Average R-Multiple: {report['avg_r_multiple']:.2f}R")
        
        print("\n--- RISK METRICS ---")
        print(f"CAGR: {report['cagr']:.2f}%")
        print(f"Max Drawdown: {report['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio: {report['sharpe_ratio']:.2f}")
        print(f"Sortino Ratio: {report['sortino_ratio']:.2f}")
        print(f"Calmar Ratio: {report['calmar_ratio']:.2f}")
        
        print("\n--- TRADE STATISTICS ---")
        print(f"Average Hold Days: {report['avg_hold_days']:.1f}")
        print(f"Max Consecutive Wins: {report['max_consecutive_wins']}")
        print(f"Max Consecutive Losses: {report['max_consecutive_losses']}")
        
        print("\n--- EXIT REASONS ---")
        for reason, count in report['exit_reasons'].items():
            print(f"{reason}: {count}")
        
        print("\n" + "=" * 60)
