# Dictionary

This is an overview of the points data.

## Point String Pattern

The general point string pattern for tennis is: `[Serve] --> [Return] ---> [Rally] ---> [Ending]`

Each part is encoded using:
- Numbers = court position
- Letters = shot type or outcome
- Symbols = point ending

### Serve Direction Number

| Code | Serve Direction Number |
| :--: | ---------------------- |
| 1 | Wide (Deuce) |
| 2 | Body (Deuce) |
| 3 | T (Deuce) |
| 4 | T (Ad) |
| 5 | Body (Deuce) |
| 6 | Wide (Deuce) |

### Serve Outcome Letter

| Code | Serve Outcome Letter |
| :--: | ---------------------- |
| n | In play |
| f | Fault |
| d | Double fault |
| C | Ace |
| w | Service winner |

### Rally Sequence Shot Types

| Code | Shot Type |
| :--: | ---------------------- |
| f | Forehand |
| b | Backhand |
| r | Forehand slice |
| v | Volley |
| o | Overhead |

### Directions

Think of the court as a keypad:
```
7 8 9
4 5 6
1 2 3
```

This tells you where the ball was hit. Here are some examples:

- **4b =** Backhand to left mid-court
- **1b =** Backhand crosscourt short
- **3f =** Forehand down the line

### Ending Sequence

| Code | Shot Type |
| :--: | ---------------------- |
| @ | Winner |
| # | Forced Error |
| ! | Unforced Error |
| * | Ace |
| + | Serve winner |

### Notes

Since the point string describes the action, the notes column is only used for:

- Let cords
- Hindrance
- Replay
- Medical timeout
- Overrule

## Step-by-step Example

Assume we have the point string sequence `5f28f2b1b1b2f3f3d@`, we can extract the following information:

| Identifier | Description |
| :--------: | ----------- |
| 5f  | Serve: Ad body, fault
| 28f | Second serve return: forehand to mid-deep
| 2b  | Backhand to center
| 1b  | Backhand crosscourt
| 1b  | Backhand crosscourt
| 2f  | Forehand center
| 3f  | Forehand down the line
| 3d@ | Forced error by opponent → winner for striker

## Data Overview

This section looks into the column names and schemas used for both matches and points.

### Tennis Matches

| Column | Description |
| ------ |-------------|
| **match_id** | Unique identifier for the match. Encodes date, tour (M/W), tournament, round, and both player names. |
| **Player 1** | Name of the first listed player (typically top of draw or server for first point). |
| **Player 2** | Name of the second listed player. |
| **Pl 1 hand** | Dominant playing hand of Player 1 (R = Right-handed, L = Left-handed). |
| **Pl 2 hand** | Dominant playing hand of Player 2 (R = Right-handed, L = Left-handed). |
| **Date** | Match date in *YYYYMMDD* format. |
| **Tournament** | Name of the tournament or event. |
| **Round** | Tournament round (e.g., R32, R16, QF, SF, F, RR). |
| **Time** | Local start time of the match (if available). |
| **Court** | Court name or court number where the match was played. |
| **Surface** | Playing surface (Hard, Clay, Grass, Carpet). |
| **Umpire** | Chair umpire assigned to the match. |
| **Best of** | Maximum number of sets for the match (3 or 5). |
| **Final TB?** | Indicates whether the final set used a tiebreak (Y/N or 1/0 depending on source). |
| **Charted by** | Username or ID of the person who manually charted the match data. |

### Tennis Players

| Column Name | Description |
|------------|-------------|
| **match_id** | Unique identifier for the match. Links each point to its parent match record in the matches table. |
| **Pt** | Sequential point number within the match, starting from 1 and incrementing for every rally played. |
| **Set1** | Number of sets won by Player 1 at the start of this point. |
| **Set2** | Number of sets won by Player 2 at the start of this point. |
| **Gm1** | Number of games won by Player 1 in the current set at the start of this point. |
| **Gm2** | Number of games won by Player 2 in the current set at the start of this point. |
| **Pts** | Current game score before the point is played (e.g., `0-0`, `15-30`, `40-AD`). |
| **Gm#** | Game number within the current set. |
| **TbSet** | Boolean indicator for whether this point is part of a tiebreak game (`True` = tiebreak, `False` = regular game). |
| **Svr** | Server indicator (`1` = Player 1 is serving, `2` = Player 2 is serving). |
| **1st** | Encoded result of the first serve, including direction, depth, and outcome (e.g., ace, fault, let). |
| **2nd** | Encoded rally sequence or second serve outcome if a second serve or rally occurred. |
| **Notes** | Optional annotations or special markers (e.g., challenges, net cords, unusual rulings). |
| **PtWinner** | Winner of the point (`1` = Player 1, `2` = Player 2). |
