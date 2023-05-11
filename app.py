import boto
from flask import Flask, request, jsonify, make_response
import sqlite3
from sqlite3 import Error
import datetime
import os

#TODO: check timezone issue

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
    current_time = datetime.datetime.now()
    time_delta = (current_time - entrance_time).seconds
    return round(time_delta/60), round(FIFTEEN_MIN_PRICE * (time_delta/60)/15)

@app.route('/entry', methods=['POST'])
def entry():
    # print(request.json)
    print('--------------')
    print(request.args)
    plate = request.args.get('plate')
    parking_lot = request.args.get('parkingLot')
    time_of_entrance = datetime.datetime.now()
    ticket_id = None
    conn = get_db(create_table=True)
    if conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO tickets (plate_number, parking_lot) VALUES (?, ?)",
                     (plate, parking_lot))
        ticket_id = cur.lastrowid
        conn.commit()
        conn.close()
        # response = f"'ticket_id':{ticket_id}"
        return make_response(jsonify(ticket_id=ticket_id), 200)
    else:
        return make_response(jsonify(error="conection to database couldn't be initiated"), 404)


@app.route('/exit', methods=['POST'])
def exit():
    result = {}
    ticket_id = request.args.get('ticketId')
    conn = get_db()
    error = "conection to database couldn't be initiated"
    if conn:
        cur = conn.cursor()
        ticket_info = cur.execute('SELECT * FROM tickets WHERE ticket_id = ?',
                            (ticket_id,)).fetchone()
        if ticket_info:
            result['license_plate'] = ticket_info[2]
            result['parking_lot'] = ticket_info[3]

            entrance_time = datetime.datetime.strptime(ticket_info[1], '%Y-%m-%d %H:%M:%S')
            total_parked_time, charge = get_final_price(entrance_time)
            result['total_parked_time'] = f'{total_parked_time} minutes'
            result['charge'] = f'{charge} $'
            #delete the ticket
            delete = 'DELETE FROM tickets WHERE ticket_id=?'
            cur.execute(delete, (ticket_id,))
            conn.commit()
            return make_response(jsonify(**result), 200)
        else:
            error = "ticket doesn't exist"

    return make_response(jsonify(error=error), 404)

@app.route('/')
def hello():
    return jsonify(message='server is alive')