# Tennis Rally Definitions

Every individual shot, including serves, is coded.

| Type | Use Case | Notes |
| --------- | -------- | :---: |
| Number(s) | Direction & Depth | |
| Letter(s) | Shot Types & Error Types | |
| Symbol(s) | Miscellaneous, Other, and Error Types | @ (*unforced error*) <br> \+ (*approach shot*) |

## Sets/Tiebreaks

| Code | Description | In Other Words (*aka, i.e.*) | Example(s) |
| :--: | ----------- | ---------------------------- | ---------- |
| 0 | If the final set is an advantage set | not a tiebreak | Like non-US Open slams through 2018 and Roland Garros in 2019 |
| S | If the final set is a 10-point super-tiebreak | there are no regular games, *only* the super-tiebreak ||
| W | If tiebreaks are played at 8-all instead of 6-all || 1970s Wimbledon |
| V | If no tiebreaks are played at all | every set is an "advantage" set, played until someone wins by two games ||
| A | If the final set is decided by a 10-point super-tiebreak at a score of 6-all || 2019 Australian Open |
| T | If the final set is decided by a tiebreak at 12-all || 2019 Wimbledon |
| N | For NextGen Finals format (no-ad, sets to 4, standard tiebreak at 3-3) ||| 

***IMPORTANT**: On deuce "deciding points," use the Notes column to record whether it was a deuce-court or ad-court point.*

## Serves

This section will cover **Serve Direction**, **Serve Fault Types**, and **Serve Outcomes**.

### Serve Direction

***Note:** These numbers are the same in both the ad and deuce courts.*

| Number | Direction |
| :----: | --------- |
| 4 | out wide |
| 5 | body |
| 6 | down the T |
| 0 | unknown |

### Serve Fault Types

If the serve is a fault, a lowercase letter to indicate the type of fault. There are five types of faults:

| Code | Type | Note(s) |
| :--: | ---- | ------- |
| n | net | anything that goes into the net, including net cords that are not lets |
| w | wide | in either direction |
| d | deep ||
| x | wide and deep ||
| g | foot faults ||

#### Rare Serve Fault Types

| Code | Type | Note(s) |
| :--: | ---- | ------- |
| e | unknown type of fault | if you didn't see it, or the TV camera cut away |
| ! | shank | rare cases when players shank a serve, use `!` to indicate a shank, rather than the letter to indicate the type of error. |
| V | time violation | server commits a time violation and loses first serve |

#### Optional Serve Fault Types

| Code | Type | Note(s) |
| :--: | ---- | ------- |
| c | let serve | not necessary; discretion of the volunteer; can be repeated as many times as there are lets |
| + | serve-and-volley attempts | This can be used whether or not the serve goes in |

### Serve Outcomes

There are four categories for points that never progress past the serve:

| Code | Type                  | Description                             | Example(s) |
| :--: | :-------------------- | :-------------------------------------- | :--------- |
|   *  | ace                   | append `*` to the serve notation        | `5*` - a body serve ace |
|   #  | unreturnable          | append `#` to the serve notation        | `6#` - a serve down the T that the other player touches but cannot return |
|   #  | forced return error   | Code the return as shown in "Rally Sequence" along with the forced error notation (`#`)| `6f#` |
|   @  | unforced return error | Code the return as shown in "Rally Sequence" along with the unforced error notation (`@`) | `6f2d@` |

***Note:** As a general rule, "unreturnables" are points where the returner fails to get a full racquet on the ball (including shanks), get the return all the way to the net, or wildly misses. All other returns are forced or unforced errors.*

Differentiating between forced and unforced errors on the service return will always be a challenging subject because:

- The distinction relies on subjective judgment rather than objective rules
- Scorers assess factors like reaction time and shot pressure without universal standards
- Different tournaments use different criteria/factors

With that being said, very generally speaking:
- first-serve return errors are usually forced
- second-serve return errors are often unforced

However, especially in the men's game, many second-serve return errors are forced.

## Rally Sequence

Each shot after the serve requires a two-character code.

Each rally shot (with the exception of service returns and point-ending "forced" errors) consists of:

- A letter indicating the shot type
- A number indicating the direction

### Shot Types

Here are the letters to indicate shot types. Note that for most types of shots, there are different letter codes for the forehand and backhand sides.

| Code | Type | Note(s) |
| :--: | ---- | ------- |
| f | forehand groundstroke | excluding slices, chips, etc. |
| b | backhand groundstroke | excluding slices, chips, etc. |
| r | forehand slice | including defensive chips, but not drop shots |
| s | backhand slice | including defensive chips, but not drop shots |
| v | forehand volley | *see below for an optional additional code to indicate a stop volley/drop volley* |
| z | backhand volley | *see below for an optional additional code to indicate a stop volley/drop volley* |
| o | standard overhead/smash ||
| p | "backhand" overhead/smash ||
| u | forehand drop shot ||
| y | backhand drop shot ||
| l | forehand lob ||
| m | backhand lob ||
| h | forehand half-volley ||
| i | backhand half-volley ||
| j | forehand swinging volley ||
| k | backhand swinging volley ||
| t | all trick shots | including behind-the-back, between-the-legs, and "tweeners." |
| q | any unknown shot ||

### Shot Direction

**Shot direction is not required**. Here are the numbers to indicate direction:

| Number | Description |
| :----: | ----------- |
| 1 | to a right-hander's forehand side / left-hander's backhand side |
| 2 | down the middle of the court |
| 3 | to a right-hander's backhand side / left-hander's forehand side |
| 0 | unknown direction |

***Note:** "Down the middle" represents a little more than one third of the court.  While we shouldn't worry about excessive precision,
 it may be helpful to think of `2` as representing the middle 40% of the court, while `1` and `3` each represent an outer 30%. It may be easier to think of a "down the middle" shot as a typical rallying shot, even though it may require the other player to move a step or two in either direction.*

In general, shot direction should indicate the part of the court where the shot crossed (or would have crossed) the opponent's baseline.
- **Example:** If player A hits a wide serve in the deuce court and player B hits a crosscourt return, the ball might bounce in the middle of the court, but cross the baseline in the corner. In a case like this, the direction is `1` (to a right-hander's forehand), not a `2` (down the middle).

## Rally Endings

### Rally Ending Winner

| Code | Type | Description | Example(s) |
| :--: | ---- | ----------- | ---------- |
| * | Winner | Code the rally as shown above, and add a `*` (star/asterisk) to indicate a winner. | `f3*` - forehand winner down the line |

### Rally Ending Errors

Code the rally as shown above, *including* the shot that the loser tried to make. Add one of the error types to the end of the final shot:

| Code | Type |
| :--: | ---- |
| n | net |
| w | wide |
| d | deep |
| x | wide and deep |
| ! | shank |
| e | unknown |

Finally, add one of these two characters at the end:
- `@` (*unforced error*)
- `#` (*forced error*)

In the case of a rally-ending error, you can use up to four keystrokes to describe the error shot: `shot-type / direction / error type / forced or unforced` (e.g. `f1n#`)

For unforced errors:

- shot-type, error type, and the unforced symbol (`@`) are *required*
- direction (as on other shots after the serve) is optional

For forced errors:

- only shot-type and the forced error symbol (`#`) are required
  - `b#` is acceptable.
  - `b3d#` is also acceptable and contains more information

## Serve Return Depth (*optional*)

**Like shot direction, this is optional, but really, really nice to have!**

Return depth is very important, so when service returns are in, we add one additional character to indicate depth.

| Number | Description |
| ------ | ----------- |
| 7 | within the service boxes. |
| 8 | behind the service line, but closer to the service line than the baseline. | 
| 9 | closer to the baseline than the service line. |
| 0 | unknown depth |

Thus, service returns *require* three keystrokes: `[Shot Type][Shot Direction][Shot Depth]`

***Note:** You can always use `0` or omit a number for depth altogether when it is unknown.*

## Court Position (*optional*)

For the most part, the shot codes indicate court position.

If a player must return a drop shot, or hits a volley, swinging volley, or smash, he or she probably came to the net. If not, probably not. However, we may want to be more precise.

As with the other optional parts of this system, your chart can be analyzed without the use of the following four codes: `Approach Shot, Baseline/Net Position, Net Cord, Stop/Drop Volley`

***Note:** Court position is great to have, but it's the lowest priority of anything discussed up to this point.*

### Approach Shots

To indicate that a shot was an approach shot, add a plus sign (`+`) immediately after the shot code (e.g. `b+2` is a backhand approach down the middle).

This not only helps us identify net approaches, but it also allows us to identify passing shots and passing shot attempts.

As mentioned above, the plus sign (`+`) also indicates serve-and-volley attempts.

- `` `4+b27v1* `` is a point in which the serve was wide, the server followed it into the net, the returner hit a shallow reply, and the server finished the point with a volley winner.

### Baseline/Net Position

The following are assumed to have taken place at the net:

- volleys
- half-volleys
- swinging volleys 
- smashes

The following are assumed to be baseline shots:

- groundstrokes
- slices
- drop shots
- lobs
- trick shots

Use the minus sign (`-`) and equal sign (`=`) immediately after the shot code to indicate otherwise.

| Code | Type | Example(s) |
| :--: | ---- | ---------- |
| - | net | `f-1` = forehand to a (righty) opponent's forehand that took place near the net |
| = | baseline | `o=2` is a smash down the middle, hit from near the baseline |

### Net Cords

A semi-colon (`;`) can be added to any shot to indicate that it clipped the net cord.

- `f;1*` is a forehand winner to a (righty's) forehand side that hit the net cord.

### Stop Volleys/Drop Volleys

If a volley is hit so that it drops close to the net (like a drop shot), use the caret sign (`^`).

- `z^2*` is a backhand (`z`) stop volley (`^`) down the middle (`2`) winner (`*`).

## Unusual Situations

If for some reason you miss a point or two, that's ok.

Entering `S` in the 1st serve column (`first_srv_rally`) will give that point to the server. `R` gives the point to the returner.

If you miss several points and are unsure of the sequence go ahead and guess. Add a note to acknowledge the missing information.

### Point Penalties

One uncommon event of importance is the point penalty.  If, for whatever reason, a point penalty is levied on either player, use a single character code in the cell for first serve.

| Code | Type |
| :--: | ---- |
| P | point penalty against the server |
| Q | point penalty against the returner |

For now, this system ignores challenges and other overrules *EXCEPT*:

- When a player stops play to challenge or check a mark, there are two possibilities:
  - If she is right--that is, she challenges and the ball was out--code the shot as you otherwise would, as a forced or unforced error.
  - However, if she is wrong, use the code `C` to indicate the incorrect decision to stop the rally.
    - `6b29C` means "serve down the T, backhand deep up the middle play stopped for a challenge [which proved incorrect]"


***Note:** If a point is replayed from the beginning, simply delete the uncounted point and start over. If a challenge affects the result of a point, adjust what you've recorded to reflect the result of the challenge.*

### Notes

Finally, there is a `Notes` column available for the volunteer's use. For now, that's a catchall for everything that doesn't fit elsewhere.

As a general rule, if something happens between points (say, a medical time out, which follows the end of a game), record it in the notes column of the *preceding* point.

This includes, but is not limited to:

- Challenges
- medical timeouts
- rain delays
- on-court coaching
- time violation warnings
- anything you think is worthy of mention (*miscellaneous, etc., other*)

**IMPORTANT:** There's no pre-set format, but please avoid using commas in this column. Using commas can cause downstream issues when trying to parse the CSV file into something like a pandas DataFrame.

## Tips

- When you start learning this system, progress will be slow for a little while.
  - Try charting pre-recorded matches (there are lots of them on YouTube, for instance) and expect to use the pause and rewind buttons frequently.
- At first, ignore shot direction.
  - Stick to the shot types themselves to make sure you learn the shot codes, error indicators (`@` and `#`) and error codes.
- Next, incorporate shot direction (`1`, `2`, and `3`).
  - When you first include direction, I strongly recommend charting a match with two righties--no matter how much you love Rafa or Petra.
- Once you're comfortable with shot direction, try to add return depth (`7`, `8` and `9`).
  - This is probably the hardest part of the process, because you must code the serve and the three-keystroke return in such a short amount of time.
- Finally, include court position notations, for approach shots and other shots that take place in unusual court positions, such as baseline smashes.

- With some practice, you should be able to chart a match in real time.  
- The biggest obstacle to doing so is simply thinking too much.
  - If you stop to consider whether a groundstroke was down the middle or crosscourt, you'll miss the next shot.
  - This is particularly dangerous on the serve return. 
  - Don't be afraid to use the code for unknown direction (`0`) or omit it entirely.

- Note that this system includes "unknown" codes for just about every step of the process **(TO DO: check if `.` is included in the following codes)**.
  - If you miss the direction of a serve or shot, use `0.`
  - If you miss the type of shot, use `q.`
  - If a shot is out but you don't know in which direction, use `e.`
  - If you miss an entire point use:
    - `R` if the returner won
    - `S` if the server won
  - Sometimes broadcasts force you to use these notations.

- Networks will return to a match when the first point of a game is in progress while others will occasionally keep the camera on the server throughout an entire point.

- Unfortunately, some match charts will always be a bit incomplete.
  - However, having 95% of the data from a match is usually sufficient to identify patterns and tendencies, and 95% is way better than nothing.




---

- All + symbols indicate a player is moving toward the net.

Context differentiates them:

- If the + follows a serve, treat it as serve-and-volley.
- If the + follows a groundstroke, treat it as an approach shot.