import mysql.connector
import random
import json

# Connect to the MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="sqluser",
    password="password",
    database="maze_game"
)

# Create tables for maze, player, inventory, and game state
cursor = db.cursor()

# Define SQL queries to create tables (customize as needed)
create_maze_table_query = """
CREATE TABLE IF NOT EXISTS maze (
    id INT AUTO_INCREMENT PRIMARY KEY,
    layout TEXT
)
"""
create_winner_table_query="""
CREATE TABLE IF NOT EXISTS winner (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    steps INT
)
"""

create_player_table_query = """
CREATE TABLE IF NOT EXISTS player (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    x INT,
    y INT,
    steps INT,
    inventory TEXT,
    winner BOOLEAN DEFAULT 0
)
"""

# Execute the create table queries
cursor.execute(create_maze_table_query)
cursor.execute(create_player_table_query)
cursor.execute(create_winner_table_query)

# Commit changes
db.commit()

# Generate a solvable maze using depth-first search algorithm
def generate_maze(width, height):
    maze = [['#' for _ in range(width)] for _ in range(height)]

    def is_valid(x, y):
        return 0 <= x < width and 0 <= y < height

    def visit(x, y):
        maze[y][x] = ' '
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(directions)
        for dx, dy in directions:
            nx, ny = x + dx * 2, y + dy * 2
            if is_valid(nx, ny) and maze[ny][nx] == '#':
                maze[y + dy][x + dx] = ' '
                visit(nx, ny)

    visit(1, 1)  # Start the generation from an odd cell
    maze[0][1] = 'S'
    maze[height - 1][width - 2] = 'E'  # Place the end point

    # Add keys A, B, and C and door D
    keys = ['A', 'B', 'C']
    while True:
        x = random.randint(1, width - 2)
        y = random.randint(1, height - 2)
        if maze[y][x] == ' ':
            item = keys.pop()
            maze[y][x] = item
            if not keys:
                break

    while True:
        x = random.randint(1, width - 2)
        y = random.randint(1, height - 2)
        if maze[y][x] == ' ':
            maze[y][x] = 'D'  # Locked door
            break

    return maze

# Check if the maze is solvable using depth-first search
def is_solvable(maze):
    start_x, start_y = None, None
    end_x, end_y = None, None

    # Find the start and end points
    for y in range(len(maze)):
        for x in range(len(maze[y])):
            if maze[y][x] == 'S':
                start_x, start_y = x, y
            elif maze[y][x] == 'E':
                end_x, end_y = x, y

    if start_x is None or end_x is None:
        return False

    stack = [(start_x, start_y)]
    visited = set()

    while stack:
        x, y = stack.pop()
        if x == end_x and y == end_y:
            return True

        if (x, y) in visited:
            continue

        visited.add((x, y))

        # Check neighboring cells
        neighbors = [(x + dx, y + dy) for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]]
        for nx, ny in neighbors:
            if 0 <= nx < len(maze[0]) and 0 <= ny < len(maze) and maze[ny][nx] != '#':
                stack.append((nx, ny))

    return False

# Modify the print_maze function to show items and the locked door
def print_maze(maze, player_x, player_y):
    for y, row in enumerate(maze):
        row_str = ''
        for x, cell in enumerate(row):
            if x == player_x and y == player_y:
                row_str += 'P'  # Player's position
            else:
                row_str += cell
        print(row_str)
# Load player data from the database
def load_player_from_db(db):
    cursor = db.cursor()
    cursor.execute("SELECT name, x, y, steps, inventory, winner FROM player WHERE id = 1")
    player_data = cursor.fetchone()

    if player_data is not None:
        name, x, y, steps, inventory_json, winner = player_data
        inventory = json.loads(inventory_json)
        return name, x, y, steps, inventory, winner
    else:
        return None, 0, 0, 0, [], False

# Save player data to the database
def save_player_to_db(db, name, x, y, steps, inventory, winner):
    cursor = db.cursor()
    inventory_json = json.dumps(inventory)
    cursor.execute("UPDATE player SET name = %s, x = %s, y = %s, steps = %s, inventory = %s, winner = %s WHERE id = 1", (name, x, y, steps, inventory_json, winner))
    db.commit()

def save_winner_to_db(db, name, steps):
    cursor=db.cursor()
    cursor.execute("INSERT INTO winner(name, steps) VALUES(%s,%s)",(name,steps))
    db.commit()
# Main game loop
def main():
    width, height = 21, 21  # Adjust maze size as needed (must be odd)
    maze = generate_maze(width, height)
    
    player_name, player_x, player_y, player_steps, player_inventory, winner = load_player_from_db(db)
    if player_name is None:
        player_name = input("Enter your name: ")
        print("Player data not found. Starting a new game...")
        player_x, player_y, player_steps, player_inventory, winner = 0, 0, 0, set(), False

    while True:
        print(f"Player: {player_name}, Steps: {player_steps}")
        print_maze(maze, player_x, player_y)
        move = input("Enter your move (u/d/l/r/q): ").lower()
        
        if move == 'q':
            break
        elif move == 'u':
            if player_y > 0 and maze[player_y - 1][player_x] != '#':
                player_y -= 1
                player_steps += 1
        elif move == 'd':
            if player_y < height - 1 and maze[player_y + 1][player_x] != '#':
                player_y += 1
                player_steps += 1
        elif move == 'l':
            if player_x > 0 and maze[player_y][player_x - 1] != '#':
                player_x -= 1
                player_steps += 1
        elif move == 'r':
            if player_x < width - 1 and maze[player_y][player_x + 1] != '#':
                player_x += 1
                player_steps += 1
        
        # Check for items and the locked door
        current_cell = maze[player_y][player_x]
        if current_cell in ['A', 'B', 'C']:
            print(f"Found key: {current_cell}")
            player_inventory.add(current_cell)
            maze[player_y][player_x] = ' '  # Remove the key from the maze
        elif current_cell == 'D':
            if {'A', 'B', 'C'}.issubset(player_inventory):
                print("You unlocked the door!")
                maze[player_y][player_x] = ' '  # Remove the door
        elif current_cell == 'E' and {'A', 'B', 'C'}.issubset(player_inventory):
            print("Congratulations! You reached the exit and won the game!")
            winner = True
            save_winner_to_db(db, player_name, player_steps)
            break
        
        # Save player data to the database
        save_player_to_db(db, player_name, player_x, player_y, player_steps, list(player_inventory), winner)

    # Close the database connection when done
    db.close()

if __name__ == "__main__":
    main()
