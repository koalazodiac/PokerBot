#!/usr/bin/env python3
import asyncio
import argparse

from tg.bot import Bot
import time

parser = argparse.ArgumentParser(
    prog='Winning bot',
    description='A bot that WINS')

parser.add_argument('--port', type=int, default=1999,
                    help='The port to connect to the server on')
parser.add_argument('--host', type=str, default='localhost',
                    help='The host to connect to the server on')
parser.add_argument('--room', type=str, default='my-new-room',
                    help='The room to connect to')
parser.add_argument('--username', type=str, default='bot',
                    help='The username for this bot (make sure it\'s unique)')

args = parser.parse_args()

cnt = 0
# Always call
class TemplateBot(Bot):
    def __init__(self, host, port, room, username):
        super().__init__(host, port, room, username)
        self.prev_win_probability = 0
        self.hand_rankings = {
            (1, 1): 1, (13, 13): 2, (12, 12): 3, (11, 11): 4, (10, 10): 5,
            (9, 9): 6, (8, 8): 7, (7, 7): 8, (6, 6): 9, (5, 5): 10,
            (4, 4): 11, (3, 3): 12, (2, 2): 13,

            (1, 13): 14, (1, 12): 15, (1, 11): 16, (1, 10): 17, (13, 12): 18,
            (13, 11): 19, (13, 10): 20, (12, 11): 21, (12, 10): 22, (11, 10): 23,

            (10, 9): 24, (9, 8): 25, (8, 7): 26, (7, 6): 27, (6, 5): 28,
            (5, 4): 29, (4, 3): 30, (3, 2): 31
        }

    def calculate_preflop_strength(self, hand):
        # Convert hand to ranks for evaluation
        ranks = sorted([hand[0].rank, hand[1].rank], reverse=True)
        suited = hand[0].suit == hand[1].suit
        
        # Basic hand strength (0-1)
        if tuple(ranks) in self.hand_rankings:
            strength = (len(self.hand_rankings) - self.hand_rankings[tuple(ranks)]) / len(self.hand_rankings)
        else:
            strength = 0.2 if suited else 0.1  # Default lower strength for unranked hands
            
        return strength

    def calculate_postflop_strength(self, hand, board):
        # Simple probability calculation based on made hands
        all_cards = hand + board
        ranks = [card.rank for card in all_cards]
        suits = [card.suit for card in all_cards]
        
        # Check for pairs, trips, etc.
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
        # Count suits for flush detection
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Basic strength calculation
        strength = 0.2  # Base strength
        
        # Check for straight
        sorted_ranks = sorted(set(ranks))
        max_consecutive = 1
        current_consecutive = 1
        for i in range(1, len(sorted_ranks)):
            if sorted_ranks[i] == sorted_ranks[i-1] + 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        
        # Add strength for made hands
        has_three = False
        has_pair = False
        for count in rank_counts.values():
            if count == 2:
                strength += 0.2  # Pair
                has_pair = True
            elif count == 3:
                strength += 0.4  # Three of a kind
                has_three = True
            elif count == 4:
                strength += 0.8  # Four of a kind
        
        # Full house
        if has_three and has_pair:
            strength += 0.7
        
        # Flush and flush draws
        for suit_count in suit_counts.values():
            if suit_count >= 5:
                strength += 0.6  # Flush
            elif suit_count == 4:
                strength += 0.15  # Flush draw
        
        # Straight and straight draws
        if max_consecutive >= 5:
            strength += 0.5  # Straight
        elif max_consecutive == 4:
            strength += 0.1  # Open-ended straight draw
        
        # Normalize strength
        return min(strength, 1.0)

    def kelly_bet(self, win_prob, pot_size=1.0):
        # Basic Kelly Criterion calculation
        # f* = (bp - q) / b
        # where: b = odds received (pot size)
        #        p = probability of winning
        #        q = probability of losing (1-p)
        
        b = pot_size
        p = win_prob
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        return max(0, kelly_fraction)

    def act(self, state, hand):
        print('my turn')
        print(f"round: {state.round}")
        print(f"my hand: {hand[0].rank}, {hand[0].suit},{hand[1].rank}, {hand[1].suit}")
        
        #check_or_call_backup, 

        # Charles ChatGPT strat
        # Calculate current win probability
        if state.round == "pre-flop":
            win_prob = self.calculate_preflop_strength(hand)
        else:
            win_prob = self.calculate_postflop_strength(hand, state.cards)
        
        # Get pot size (simplified)
        pot_size = state.pot  # This should be calculated from actual pot
        
        # Calculate Kelly bet size
        kelly_fraction = self.kelly_bet(win_prob, pot_size)
        my_stack = next(player.stack for player in state.players if player.id == "BUBBLES")
        # **Passive Bot Exploit: Never Fold to Small Bets**
        min_call_amount = min([player.current_bet for player in state.players if player.id != "BUBBLES"], default=0)
        max_call_amount = max([player.current_bet for player in state.players if player.id != "BUBBLES"], default=0)

        

        if win_prob > 0.7:
            kelly_fraction *= 3  # Bet 3x more if we have a dominant hand
        elif win_prob > 0.5:
            kelly_fraction *= 2  # Bet 2x more with strong hands
        # Decision making

        if max_call_amount >= my_stack * 0.5:
            if win_prob > 0.80:
                return {'type': 'raise', 'amount':1000000}
            else:
                return {'type': 'fold'}
        if state.round == "pre-flop":
            if win_prob < 0.15:
                if min_call_amount < pot_size * 0.2:  # If opponent bets small, always call
                    return {"type": "call"}
                return {'type': 'fold'}
            elif kelly_fraction > 0.75:
                return {'type': 'raise', 'amount':int(kelly_fraction * my_stack)}  # Convert to big blinds
            else:
                return {'type': 'call'}
        else:
            # Post-flop strategy
            if win_prob > self.prev_win_probability:
                # Our hand improved, consider raising
                if kelly_fraction > 0.2:
                    return {'type': 'raise', 'amount': int(kelly_fraction * my_stack)}
            
            # Default to call if we haven't improved
            self.prev_win_probability = win_prob
            return {'type': 'call'}

        # #Chen Ru 
        # #if rank is high
        # if (((hand[0].rank in [10, 11, 12, 13]) or (hand[0].rank == 1))
        #     and ((hand[1].rank in [10, 11, 12, 13]) or (hand[1].rank == 1))):
        #     if hand[0].suit == hand[1].suit:
        #         if abs(hand[0].rank - hand[1].rank) == 1:
        #             return {'type': 'raise', 'amount': 180}
        #         return {'type': 'raise', 'amount': 150}

        #     elif abs(hand[0].rank - hand[1].rank) == 1:
        #         return {'type': 'raise', 'amount': 100}

        #     else:
        #         return {'type': 'fold'}
        # else:
        #     if (hand[0].suit == hand[1].suit):
        #         if abs(hand[0].rank - hand[1].rank) == 1:
        #             return {'type': 'raise', 'amount': 100}
        #         return {'type': 'raise', 'amount': 50}

        #     elif abs(hand[0].rank - hand[1].rank) == 1:
        #         return {'type': 'raise', 'amount': 25}

        #     else:
        #         return {'type': 'fold'}

        #concordia hacking team, Iron Triangle
        #Peter all-in strategy
        # return {'type': 'raise', 'amount' : 50000}

        # #check or call bot
        # return {'type': 'check'}

    def opponent_action(self, action, player):
        #print('opponent action?', action, player)
        pass

    def game_over(self, payouts):
        global cnt
        #print('game over', payouts)
        cnt += 1
        print(cnt)

    def start_game(self, my_id):
        self.my_id = my_id
        self.prev_win_probability = 0  # Reset probability tracking for new game

if __name__ == "__main__":
    bot = TemplateBot(args.host, args.port, args.room, args.username)
    asyncio.run(bot.start())
