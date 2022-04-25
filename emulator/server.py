from flask import Flask, request
from pymemcache.client import base
from mixologist import Mixologist, Job
import click
import logging
import json
import requests

app = Flask(__name__)


cache = base.Client(('localhost', 11211))

machine = Mixologist(12, 12)

format = "[%(asctime)s]: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt='%H:%M:%S')

############################################################################
#CLI Definition
############################################################################
@app.cli.command('state')
def list_locations():
    #logging.info(machine.dump_state())
    logging.info('Current State: %s', ''.join(str(cache.get('loc' + str(i))) for i in range(machine.num_loc)))

@app.cli.command('fill')
@click.argument("res")
@click.argument("amount")
def fill_reservoir(res, amount):
    res = int(res)
    amount = int(amount)
    if not 0 <= res < machine.num_res:
        logging.info("No valid reservoir with id %s", res)
    else:
        state = json.loads(cache.get('state').decode('utf-8'))
        if state['inv'][res]['quantity'] + amount > machine.max:
            amount = machine.max - state['inv'][res]['quantity'] 

        state['inv'][res]['quantity'] += amount
        cache.set('state', json.dumps(state))
        logging.info("Queued fill at reservoir %s with %s ozs", res, amount)

@app.cli.command('change')
@click.argument("res")
@click.argument("ingredient")
@click.argument("amount")
def change_liqure(res, ingredient, amount):
    res = int(res)
    ingredient = int(ingredient)
    amount = int(amount)

    if not 0 <= res < machine.num_res:
        logging.info("No valid reservoir with id %s", res)
    else:
        state = json.loads(cache.get('state').decode('utf-8'))
        if amount > machine.max:
            amount = machine.max

        state['inv'][res]['ingredient-id'] = ingredient
        state['inv'][res]['quantity'] = amount
        cache.set('state', json.dumps(state))
        logging.info("Queued liqure change at reservoir %s with %s ozs", res, amount)
        
@app.cli.command('remove')
@click.argument('loc')
def remove_drink(loc):
    loc = int(loc)

    if not 0 <= loc < machine.num_loc:
        logging.info("No valid location with id %s", loc)
    else:
        p = {'Location Number': loc}
        res = requests.get('http://127.0.0.1:5000/api/v1/location', params=p)
        data = res.json()

        if data['200']['status'] == 'making':
            logging.info("Drink at location %s is in progress, cannot remove", loc)
        else:
            if cache.get('loc' + str(loc)).decode('utf-8') == '1':
                cache.set('remove_flag', 1)
                cache.set('remove_loc', loc)
                logging.info("Queued drink removal at location %s", loc)
            else:
                logging.info("No drink to remove at location %s", loc)


############################################################################
#API Routing
############################################################################
@app.before_first_request
def startup():
    for i in range(machine.num_loc):
        cache.set('loc' + str(i), 0)

    for i in range(machine.num_res):
        machine.set_res_properties(i, i, machine.max)
    
    state = machine.dump_state()
    cache.set('state', json.dumps({'inv': state}))
    cache.set('remove_flag', 0)


@app.before_request
def sync_cache():
    def ordered(obj):
        if isinstance(obj, dict):
            return sorted((k, ordered(v)) for k, v in obj.items())
        if isinstance(obj, list):
            return sorted(ordered(x) for x in obj)
        else:
            return obj

    a = json.loads(cache.get('state').decode('utf-8'))

    state = machine.dump_state()
    b = {'inv': state}

    if(ordered(a) != ordered(b)):
        app.logger.info('Cache out of sync')
        c_data = json.loads(cache.get('state').decode('utf-8'))
        machine.overwrite_state(c_data)
    
    if int(cache.get('remove_flag').decode('utf-8')) == 1:
        loc = int(cache.get('remove_loc').decode('utf-8'))
        machine.remove_drink(loc)
        cache.set('remove_flag', 0)

@app.after_request
def update_cache(response):
    state = machine.dump_state()
    cache.set('state', json.dumps({'inv': state}))
    return response


@app.route('/api/v1/make-recipe', methods = ['POST'])
def app_make_drink():
    req = request.json
    user = req['user']
    app.logger.info('Drink request received from user %s', user)

    loc = machine.add_drink()
    cache.set('loc' + str(loc), 1)

    if loc == -1:
        return {'location': -1}
    
    recipe = req['recipe']

    all_ingredients = True
    for r in recipe:
        exists = False
        for i in range(machine.num_res):
            if machine.get_res(i).ingredient == int(r['ingredient-id']):
                if machine.get_res(i).quantity >= int(r['amount']):
                    exists = True
        all_ingredients = all_ingredients and exists

    if not all_ingredients:
        return {'location': -2}

    for r in recipe:
        for i in range(machine.num_res):
            if machine.get_res(i).ingredient == int(r['ingredient-id']):
                machine.pour(i, int(r['amount']))

    machine.set_thread(loc, Job(loc, 20, app))

    response = {'200': {'location': loc}}
    return response

@app.route('/api/v1/location', methods = ['GET'])
def app_get_status():
    loc = int(request.args.get('Location Number'))
    status = None
    progress = -1

    if not 0 <= loc < machine.num_loc:
        response = {'status': status, 'progress':progress}
        return response


    if machine.get_thread(loc) != None and machine.get_thread(loc).is_alive():
        status = 'making'
        progress = machine.get_thread(loc).get_progress()
    elif machine.get_loc(loc).get_occupied() == True:
        status = 'done'
        progress = 1
    else:
        status = 'open'

    response = {'200': {'status': status, 'progress':progress}}
    return response

@app.route('/api/v1/inventory', methods = ['GET'])
def app_get_inventory():
    inv = machine.dump_state()

    response = {'inventory': inv}
    return response