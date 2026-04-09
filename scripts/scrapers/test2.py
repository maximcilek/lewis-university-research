import pandas as pd

# Load your CSV
df = pd.read_csv("/home/mcilek/Github/maximcilek/lewis-university-research/data/canonical/tennisabstract/charting_points.csv")

# Filter tiebreak points
tiebreak_points = df[df['tiebreaker_set'] == 't']

# Group by match and find the max tiebreak number
# Check how many rows per match are marked as tiebreaks
tiebreak_points_per_match = tiebreak_points.groupby('match_id').size()
print(tiebreak_points_per_match.sort_values(ascending=False).head(10))


# Correct way:
max_tiebreak_points = tiebreak_points_per_match['num_tiebreak_points'].max()
print(max_tiebreak_points)