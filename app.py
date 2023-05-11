import boto
from flask import Flask, request, jsonify, make_response
import sqlite3
from sqlite3 import Error
import datetime
import os

CREATE_TBL_SQL = """CREATE TABLE if not exists tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    plate_number TEXT,
    parking_lot INTEGER 
);"""
HOURLY_PRICE = 10
FIFTEEN_MIN_PRICE = HOURLY_PRICE/4

app = Flask(__name__)
# display response as pretty json
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

def get_db(create_table=False, drop_last=False):
    """
    create a new connection to the db that will handle the parking lot data
    :return:
    """
    conn = None
    try:
        conn = sqlite3.connect('parkinglot_db.db')
    except Error as e:
        print(e)
    if conn:
        if drop_last or (not os.path.exists('parkinglot_db.db')):
            conn.execute("DROP TABLE IF EXISTS tickets;")
        conn.execute(CREATE_TBL_SQL)
    return conn

def get_final_price(entrance_time):
    """
    calculate the final price of the parking according to the amount of time.
    :param entrance_time: time of entrance
    :return: price of parking
    """
    current_time = datetime.datetime.now()
    time_delta = (current_time - entrance_time).seconds
    return round(time_delta/60), round(FIFTEEN_MIN_PRICE * (time_delta/60)/15)

@app.route('/entry', methods=['POST'])
def entry():
    """
    create an entry in the DB when a new car comes into the
    parking lot and save the given information
    :return: The ticket id of the arriving car.
    """
    plate = request.args.get('plate')
    parking_lot = request.args.get('parkingLot')
    # get connection to db and if cant return error
    conn = get_db(create_table=True)
    if conn:
        # add new ticket to db
        cur = conn.cursor()
        cur.execute("INSERT INTO tickets (plate_number, parking_lot) VALUES (?, ?)",
                     (plate, parking_lot))
        ticket_id = cur.lastrowid
        conn.commit()
        conn.close()
        # return successful response
        return make_response(jsonify(ticket_id=ticket_id), 200)
    else:
        # return error response
        return make_response(jsonify(error="conection to database couldn't be initiated"), 404)


@app.route('/exit', methods=['POST'])
def exit():
    """
    delete the entry of the exiting car and calculate the ticket price according to the
    tixket id
    :return: license plate, total parked time, the parking lot id and the charge (based on 15 minutes increments).
    """
    result = {}
    ticket_id = request.args.get('ticketId')
    # get connection to db and if cant return error
    conn = get_db()
    error = "connection to database couldn't be initiated"
    if conn:
        # retrieve ticket information from db
        cur = conn.cursor()
        ticket_info = cur.execute('SELECT * FROM tickets WHERE ticket_id = ?',
                            (ticket_id,)).fetchone()
        # if ticket was found we can calculate the price and return the information
        # otherwise, an error is returned that the ticket wasn't found.
        if ticket_info:
            result['license_plate'] = ticket_info[2]
            result['parking_lot'] = ticket_info[3]
            # calculate price
            entrance_time = datetime.datetime.strptime(ticket_info[1], '%Y-%m-%d %H:%M:%S')
            total_parked_time, charge = get_final_price(entrance_time)
            result['total_parked_time'] = f'{total_parked_time} minutes'
            result['charge'] = f'{charge} $'
            # delete the ticket
            delete = 'DELETE FROM tickets WHERE ticket_id=?'
            cur.execute(delete, (ticket_id,))
            conn.commit()
            # return successful response
            return make_response(jsonify(**result), 200)
        else:
            error = "ticket doesn't exist"
    # return error response
    return make_response(jsonify(error=error), 404)

@app.route('/')
def hello():
    """
    This function is just used to receive an update that the server is alive.
    """
    return jsonify(message='server is alive')