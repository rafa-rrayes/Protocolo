import pygame
import random
import Enlace

# Initialize Pygame
pygame.init()

# Set the width and height of the screen
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))

# Set the title of the window
pygame.display.set_caption("Two Player Dodge Game")

# Define colors
black = (0, 0, 0)
white = (255, 255, 255)
red = (255, 0, 0)
green = (0, 255, 0)

# Define the player size and speed
player_width = 50
player_height = 50
player_speed = 5

# Define player positions
player1_x = screen_width // 4
player1_y = screen_height - player_height - 10
player2_x = 3 * screen_width // 4 - player_width
player2_y = screen_height - player_height - 10

# Define player movement variables
player1_move_x = 0
player2_move_x = 0

# Define obstacle properties
obstacle_width = 50
obstacle_height = 50
obstacle_speed = 7
obstacles = []

# Timer for obstacles
obstacle_timer = 0
obstacle_interval = 30  # The lower the value, the faster obstacles spawn

# Game clock
clock = pygame.time.Clock()

# Game loop flag
running = True

# Font for text display
font = pygame.font.SysFont(None, 55)

def draw_player(x, y, color):
    pygame.draw.rect(screen, color, [x, y, player_width, player_height])

def draw_obstacle(x, y):
    pygame.draw.rect(screen, red, [x, y, obstacle_width, obstacle_height])

def display_message(text, color, x, y):
    message = font.render(text, True, color)
    screen.blit(message, [x, y])
com = Enlace.Enlace('COM4', accept_all_objects=True, await_confirmation_objects=False)
com.open()
# Game loop
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Movement input for player 1 (WASD keys)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                player1_move_x = -player_speed
                com.send_object('Down_a')
            if event.key == pygame.K_d:
                com.send_object('Down_d')
                player1_move_x = player_speed

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a or event.key == pygame.K_d:
                player1_move_x = 0
                com.send_object('Up_a')
            if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                player2_move_x = 0
                com.send_object('Up_d')
    for move in com.get_objects():
        if move == 'Down_a':
            player2_move_x = -player_speed
        if move == 'Down_d':
            player2_move_x = player_speed
        if move == 'Up_a':
            player2_move_x = 0
        if move == 'Up_d':
            player2_move_x = 0

    # Update player positions
    player1_x += player1_move_x
    player2_x += player2_move_x

    # Ensure players stay within screen bounds
    player1_x = max(0, min(screen_width - player_width, player1_x))
    player2_x = max(0, min(screen_width - player_width, player2_x))

    # Spawn new obstacles at intervals
    obstacle_timer += 1
    if obstacle_timer >= obstacle_interval:
        obstacle_x = random.randint(0, screen_width - obstacle_width)
        obstacle_y = -obstacle_height
        obstacles.append([obstacle_x, obstacle_y])
        obstacle_timer = 0

    # Move obstacles down
    for obstacle in obstacles:
        obstacle[1] += obstacle_speed

    # Remove obstacles that go off the screen
    obstacles = [ob for ob in obstacles if ob[1] < screen_height]

    # Check for collisions with player 1
    for obstacle in obstacles:
        if (player1_x < obstacle[0] + obstacle_width and
            player1_x + player_width > obstacle[0] and
            player1_y < obstacle[1] + obstacle_height and
            player1_y + player_height > obstacle[1]):
            display_message("Player 2 Wins!", green, screen_width // 4, screen_height // 3)
            pygame.display.update()
            pygame.time.wait(2000)
            running = False

    # Check for collisions with player 2
    for obstacle in obstacles:
        if (player2_x < obstacle[0] + obstacle_width and
            player2_x + player_width > obstacle[0] and
            player2_y < obstacle[1] + obstacle_height and
            player2_y + player_height > obstacle[1]):
            display_message("Player 1 Wins!", green, screen_width // 4, screen_height // 3)
            pygame.display.update()
            pygame.time.wait(2000)
            running = False

    # Fill the screen with black
    screen.fill(black)

    # Draw players
    draw_player(player1_x, player1_y, white)
    draw_player(player2_x, player2_y, green)

    # Draw obstacles
    for obstacle in obstacles:
        draw_obstacle(obstacle[0], obstacle[1])

    # Update the screen
    pygame.display.update()

    # Set the game frame rate
    clock.tick(60)

# Quit Pygame
pygame.quit()
