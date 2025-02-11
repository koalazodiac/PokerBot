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
        self.op = 2 #check/call
        self.prev_win_probability = 0
        self.hand_rankings = {
            (1, 1): 1, (13, 13): 2, (12, 12): 3, (11, 11): 4, (10, 10): 5,
            (1, 13): 6, (1, 12): 7, (1, 11): 8, (13, 12): 9, (1, 10): 10,
            # ... more hand rankings could be added
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
        has_two_pair = False
        for rank, count in rank_counts.items():
            if count == 2:
                if has_pair:
                    has_two_pair = True
                else: 
                    if rank >= 11 or rank == 1:
                        strength += 0.15
                        has_pair = True
                    else:
                        strength += 0.05  # Pair
                        has_pair = True
                
            elif count == 3:
                handed = hand[0].rank == hand[1].rank
                if handed:
                    strength += 0.5
                    has_three = True
                else: 
                    strength += 0.2  # Three of a kind
                    has_three = True
            elif count == 4:
                strength += 0.8  # Four of a kind
        
        # Full house
        if has_three and has_pair:
            strength += 0.7

        if has_two_pair:
            strength += 0.1
        
        # Flush and flush draws
        for suit_count in suit_counts.values():
            if suit_count >= 5:
                suited = hand[0].suit == hand[1].suit
                if suited:
                    strength += 0.8  # Flush
                else:
                    strength += 0.25
            # elif suit_count == 4:
            #     strength += 0.15  # Flush draw
        
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

        print("MYSTACK", my_stack)
        print("WINPROB", win_prob)
        print("Cards on table", state.cards)

        if my_stack >= 9500:
            return {'type':'call'}

        if win_prob >= 0.6:
            # kelly_fraction *= 3  # Bet 3x more if we have a dominant hand
            return {'type': 'raise', 'amount': 1000000}
        # elif win_prob > 0.5:
        #     kelly_fraction *= 2  # Bet 2x more with strong hands
        # Decision making

        if state.round == "pre-flop":
            if min_call_amount >= my_stack * 0.25:
                print("When opponent went ALL-IN")
                print(max_call_amount)

                if win_prob > 0.4:
                    return {'type': 'raise', 'amount': 1000000}
                else:
                    return {'type': 'fold'}
            
            if win_prob >= 0.65:
                # if kelly_fraction > 0.75:
                #     return {'type': 'raise', 'amount':int(kelly_fraction * my_stack)}  # Convert to big blinds
                return {'type': 'raise', 'amount': 1000000}
            else:
                if min_call_amount < my_stack * 0.1 or self.op != 1:  # If opponent bets small, always call
                    return {"type": "call"}
                return {'type': 'fold'}
        else:
            # Post-flop strategy
            if min_call_amount >= my_stack * 0.75:
                print("When opponent went ALL-IN")
                print(max_call_amount)

                if win_prob > 0.7:
                    return {'type': 'raise', 'amount':1000000}
                elif win_prob > 0.6:
                    return {'type': 'call'}
                if state.pot >= min_call_amount*0.8 or self.op != 1:
                    return {'type': 'call'}
                else:
                    return {'type': 'fold'}
            if min_call_amount >= 2000:
                if win_prob > 0.45:
                    return {'type': 'call'}

            if win_prob >= 0.6:
                return {'type': 'raise', 'amount': 1000000}
            
            # Default to call if we haven't improved
            self.prev_win_probability = win_prob
            if min_call_amount < 50:  # If opponent bets small, always call
                if win_prob > 0.3:
                    return {"type": "raise", "amount": 100}
                return {"type": "call"}
            if self.op == 1 and win_prob <= 0.35 and min_call_amount <= my_stack *0.1:
                return {'type': 'fold'}
            else:
                return {"type": "call"}


    def opponent_action(self, action, player):
        #print('opponent action?', action, player)
        if action.type == 'raise':
            self.op = 1
        elif action.type == 'call':
            self.op = 2
        elif action.type == 'fold':
            self.op = 3
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
