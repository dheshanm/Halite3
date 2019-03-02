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

import numpy as np

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("L4TTiCe beta")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """
log_LEVEL = "i"

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
    # Collect Updated Data
    logging.info("Refreshing Inventory Co-ordinates...")
    my_deposit_coords = [item.position for item in list(me.get_dropoffs())] + [me.shipyard.position]
    my_ship_coords = [item.position for item in list(me.get_ships())]
    logging.info("Ship Coords :" + str(my_ship_coords))
    logging.info("depo Coords :" + str(my_deposit_coords))
    logging.info("Instructing Ships...")

    for ship in me.get_ships():
        logging.info("Processing Ship #"+str(ship.id))

        # area of the Map, each ship Analyses or Cosiders for its next Move
        minimap_SIZE = 16
        ship_data_matrix = []   # Data collected by this ship for each coord. in its Area-of-Interest
        # Data of Interest : Halite Amount, any ship in its vicinity, if its a DEPOSIT spot (if so, its Owner)

        for y in range(-minimap_SIZE, minimap_SIZE+1):
            row_DATA = []
            for x in range(-minimap_SIZE, minimap_SIZE+1):
                coords = game_map[ship.position + Position(x,y)]
                log_buffer = "Analyzing coord : "+str(coords)

                halite_onCoord = round( coords.halite_amount / constants.MAX_HALITE, 2)
                ship_onCoord = coords.ship
                depo_onCoord = coords.structure

                if halite_onCoord is None:
                    halite_onCoord = 0

                if ship_onCoord is None:
                    ship_onCoord = 0
                else:
                    if log_buffer != "" and log_LEVEL == 'v':
                        logging.info(log_buffer)
                        log_buffer = ""
                    if log_LEVEL == 'v':
                        logging.info("Ship Encountered ")
                    if coords.position in my_ship_coords:
                        SHIP_Ownership = 1
                        if log_LEVEL == 'v':
                            logging.info("Ship determined Friendly")
                    else:
                        SHIP_Ownership = -1
                        if log_LEVEL == 'v':
                            logging.info("Ship determined Hostile")
                    ship_onCoord = round(SHIP_Ownership * (ship_onCoord.halite_amount / constants.MAX_HALITE), 2)

                if depo_onCoord is None:
                    depo_onCoord = 0
                else:
                    if log_buffer != "" and log_LEVEL == 'v':
                        logging.info(log_buffer)
                        log_buffer = ""
                    if log_LEVEL == 'v':
                        logging.info("Depo Encountered ")
                    if coords.position in my_deposit_coords:
                        DEPO_Ownership = 1
                        if log_LEVEL == 'v':
                            logging.info("Depo determined Friendly")
                    else:
                        DEPO_Ownership = -1
                        if log_LEVEL == 'v':
                            logging.info("Depo determined Hostile")
                    depo_onCoord = DEPO_Ownership

                row_DATA.append((halite_onCoord, ship_onCoord, depo_onCoord))
            ship_data_matrix.append(row_DATA)

        if game.turn_number == 5:
            with open("temp.log", 'w') as log:
                log.write(str(ship_data_matrix))

        np.save(f"gameplay/{game.turn_number}.npy", ship_data_matrix)

        command_queue.append(ship.move(Direction.North))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if len(me.get_ships()) < 1:
        if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
            command_queue.append(me.shipyard.spawn())
            logging.info("Authorized commissioning of Ship.")

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

