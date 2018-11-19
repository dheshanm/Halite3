#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt
# This library contains constant values.
from hlt import constants
# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position
# This library allows you to generate random numbers.
import random
# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("Slatty")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_INTENT = {}

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]
    queued_coords = []

    for ship in me.get_ships():
        if ship.id not in ship_INTENT:
            logging.info("Initializing Ship #" + str(ship.id))
            ship_INTENT[ship.id] = "COLLECT"

        logging.info("Processing Ship #"+str(ship.id))
        logging.info("INTENT\t: "+str(ship_INTENT[ship.id]))

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
                        halite_count = halite_count*2
                    ship_surrounding_coord_haliteDB[direction] = halite_count

            preferred_direction = max(ship_surrounding_coord_haliteDB, key=ship_surrounding_coord_haliteDB.get)
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
                logging.info("Queued Coord : " + str(ship_surrounding_coord_DB[predicted_move]))
                if predicted_move == Direction.Still:
                    logging.info("Switching INTENT to Collect Mode")
                    ship_INTENT[ship.id]="COLLECT"


    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

