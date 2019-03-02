#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt
# This library contains constant values.
from hlt import constants
# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position
# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

log_LEVEL = "i"
TURNCOUNT = 500
TURN = 0
EMERGENCY = False
""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("L4TTiCe v4")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))
""" <<<Game Loop>>> """

ship_INTENT = {}
ship_BACKUP = 5

GAME_STATE = 0
shipyard_inuse = False

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map
    TURN += 1
    if GAME_STATE == 0:
        MAP_SIZE = game_map.width
        logging.info("MAP SIZE : "+str(MAP_SIZE))
        if MAP_SIZE == 64:
            TURNCOUNT = 500
        elif MAP_SIZE == 56:
            TURNCOUNT = 475
        elif MAP_SIZE == 48:
            TURNCOUNT = 450
        elif MAP_SIZE == 40:
            TURNCOUNT == 425
        elif MAP_SIZE == 32:
            TURNCOUNT == 400
        GAME_STATE = 1

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
    queued_coords = []
    logging.info("Refreshing Inventory Co-ordinates...")
    my_deposit_coords = [item.position for item in list(me.get_dropoffs())] + [me.shipyard.position]
    my_ship_coords = [item.position for item in list(me.get_ships())]
    logging.info("Ship Coords :" + str(my_ship_coords))
    logging.info("depo Coords :" + str(my_deposit_coords))
    logging.info("Instructing Ships...")

    shipyard_inuse = False

    for ship in me.get_ships():
        if ship.id not in ship_INTENT:
            logging.info("Initializing Ship #" + str(ship.id))
            ship_INTENT[ship.id] = "COLLECT"

        logging.info("Processing Ship #" + str(ship.id))
        logging.info("INTENT\t: " + str(ship_INTENT[ship.id]))
        logging.info("COORDS\t: " + str(ship.position))

        if ship_INTENT[ship.id] == "COLLECT":
            ship_surrounding_coord = ship.position.get_surrounding_cardinals() + [ship.position]
            ship_surrounding_coord_DB = {}
            # ship_surrounding_coord[ Direction.North ] = Its Position in map like (25, 30)
            for index, direction in enumerate(directions):
                ship_surrounding_coord_DB[direction] = ship_surrounding_coord[index]
            ship_surrounding_coord_haliteDB = {}
            # ship_surrounding_coord_haliteDB[ Direction.North ] = Halite in that Location
            for direction in ship_surrounding_coord_DB:
                position = ship_surrounding_coord_DB[direction]
                halite_count = game_map[position].halite_amount
                if ship_surrounding_coord_DB[direction] not in queued_coords:
                    if direction == Direction.Still:
                        # Biasing Current location to encourage Collecting
                        halite_count = halite_count * 2
                    ship_surrounding_coord_haliteDB[direction] = halite_count

            if log_LEVEL == 'v':
                logging.info("Halite on-Board  : " + str(ship.halite_amount))
                logging.info("Halite on-Origin-Cell  : " + str(round(0.1 * game_map[ship.position].halite_amount, 2)))
            preferred_direction = max(ship_surrounding_coord_haliteDB, key=ship_surrounding_coord_haliteDB.get)
            if ship.halite_amount < round(0.1 * game_map[ship.position].halite_amount, 2):
                preferred_direction = Direction.Still
                logging.info("Insufficient Halite to move. HALTING.")
            elif preferred_direction != Direction.Still and game_map[
                    ship.position + Position(*preferred_direction)].is_occupied:
                logging.info("Collision imminent...")
                while game_map[ship.position + Position(*preferred_direction)].is_occupied and len(
                        ship_surrounding_coord_DB.keys()) > 0:
                    logging.info("Attempting to reroute")
                    logging.info("Possible Routes : " + str(ship_surrounding_coord_haliteDB))
                    logging.info("Elimintate route : " + str(preferred_direction))
                    ship_surrounding_coord_haliteDB.pop(preferred_direction, None)
                    preferred_direction = max(ship_surrounding_coord_haliteDB, key=ship_surrounding_coord_haliteDB.get)
                    if preferred_direction == Direction.Still:
                        break
            queued_coords.append(ship_surrounding_coord_DB[preferred_direction])
            logging.info("Queued Coord : " + str(ship_surrounding_coord_DB[preferred_direction]))
            command_queue.append(ship.move(preferred_direction))

            if ship.halite_amount >= constants.MAX_HALITE * 0.80:
                logging.info("Switching INTENT to Deposit Mode")
                ship_INTENT[ship.id] = "DEPOSIT"

        elif ship_INTENT[ship.id] == "DEPOSIT":
            predicted_move = game_map.naive_navigate(ship, me.shipyard.position)
            next_pos = ship.position + Position(*predicted_move)
            if next_pos not in queued_coords:
                queued_coords.append(next_pos)
                command_queue.append(ship.move(predicted_move))
                # logging.info("Queued Coord : " + str(ship_surrounding_coord_DB[predicted_move]))
                if predicted_move == Direction.Still:
                    logging.info("Switching INTENT to Collect Mode")
                    ship_INTENT[ship.id] = "COLLECT"

    for coords in queued_coords:
        if coords == me.shipyard.position:
            shipyard_inuse=True
    for coords in my_ship_coords:
        if coords == me.shipyard.position:
            shipyard_inuse=True

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())
        logging.info("Deploying Ship")
    elif game.turn_number > 200 and me.halite_amount >= constants.SHIP_COST and not game_map[
        me.shipyard].is_occupied and ship_BACKUP > 0:
        if len(me.get_ships()) < 20 and game.turn_number < 350:
            if me.shipyard.position not in queued_coords:
                command_queue.append(me.shipyard.spawn())
                logging.info("Deploying Backup Ship")
                ship_BACKUP = ship_BACKUP - 1
                logging.info("Backup Ships available : " + str(ship_BACKUP))
            else:
                logging.info("Deferring Backup ship Deployment")
    elif game_map[me.shipyard].is_occupied and me.halite_amount >= constants.SHIP_COST:
        if not shipyard_inuse:
            logging.info("Enemy Blockade Detected")
            command_queue.append(me.shipyard.spawn())
            logging.info("Deploying Ship to break Blockade")

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
