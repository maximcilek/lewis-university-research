import matplotlib
matplotlib.use("Agg")  # Headless backend for scripts
import matplotlib.pyplot as plt

# Example decoded rally
rally = [
    {'code': '4', 'description': 'wide'},
    {'code': 'b', 'description': 'backhand'},
    {'code': '2', 'description': 'middle'},
    {'code': '9', 'description': 'deep'},
    {'code': 'f', 'description': 'forehand'},
    {'code': '2', 'description': 'middle'},
    {'code': '7', 'description': 'service_box'},
    {'code': 'f', 'description': 'forehand'},
    {'code': '3', 'description': 'to_backhand_side'},
    {'code': '7', 'description': 'service_box'},
    {'code': 'b', 'description': 'backhand'},
    {'code': '3', 'description': 'to_backhand_side'},
    {'code': '9', 'description': 'deep'},
    {'code': 'f', 'description': 'forehand'},
    {'code': '3', 'description': 'to_backhand_side'},
    {'code': '8', 'description': 'midcourt'},
    {'code': 'y', 'description': 'backhand_drop'},
    {'code': '3', 'description': 'to_backhand_side'},
    {'code': 'n', 'description': 'net'},
    {'code': '@', 'description': 'unforced_return_error'}
]

# Define court dimensions (meters, approximate singles court)
court_length = 23.77
court_width = 8.23

# Map descriptions to x, y positions (simplified)
court_positions = {
    'forehand': (-2, 5),
    'backhand': (2, 5),
    'forehand_slice': (-2, 6),
    'backhand_slice': (2, 6),
    'forehand_drop': (-2, 18),
    'backhand_drop': (2, 18),
    'forehand_volley': (-2, 12),
    'backhand_volley': (2, 12),
    'overhead': (0, 15),
    'backhand_overhead': (2, 15),
    'trick_shot': (0, 10),
    'service_box': (0, 6),
    'midcourt': (0, 12),
    'deep': (0, 20),
    'net': (0, 1),
    'middle': (0, 10),
    'to_forehand_side': (-3, 10),
    'to_backhand_side': (3, 10),
    'wide': (3, 10),
    'ace': (0, 23),
    'unforced_return_error': (0, 23),
    'serve_and_volley_attempt': (0, 6),
    'unknown': (0, 10)
}

# Map shot types to colors
color_map = {
    'forehand': 'blue',
    'backhand': 'green',
    'forehand_slice': 'cyan',
    'backhand_slice': 'lime',
    'forehand_drop': 'magenta',
    'backhand_drop': 'pink',
    'forehand_volley': 'orange',
    'backhand_volley': 'brown',
    'overhead': 'red',
    'backhand_overhead': 'darkred',
    'trick_shot': 'purple',
    'service_box': 'gray',
    'midcourt': 'yellow',
    'deep': 'black',
    'net': 'gold',
    'middle': 'lightblue',
    'to_forehand_side': 'blue',
    'to_backhand_side': 'green',
    'wide': 'orange',
    'ace': 'red',
    'unforced_return_error': 'red',
    'serve_and_volley_attempt': 'gray',
    'unknown': 'silver'
}

# Prepare figure
plt.figure(figsize=(6, 14))
plt.title("Rally Shot Map (Headless)")
plt.xlim(-court_width/2-1, court_width/2+1)
plt.ylim(0, court_length+2)
plt.xlabel("Court Width (m)")
plt.ylabel("Court Length (m)")

# Plot the rally
x_coords, y_coords = [], []
for i, shot in enumerate(rally):
    desc = shot['description']
    x, y = court_positions.get(desc, (0, 10))
    x_coords.append(x)
    y_coords.append(y)
    plt.scatter(x, y, color=color_map.get(desc, 'black'), s=50)
    plt.text(x + 0.2, y + 0.2, f"{i+1}", fontsize=8)

# Connect shots
plt.plot(x_coords, y_coords, linestyle='--', color='red')

# Draw simplified net line
plt.axhline(0, color='k', linewidth=2)
plt.text(0, -0.5, "Net", ha='center')

# Save figure
plt.savefig("rally_plot.png", dpi=300, bbox_inches='tight')
print("Rally plot saved as rally_plot.png")