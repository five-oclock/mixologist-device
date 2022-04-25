from flask import Flask, request
from pymemcache.client import base
from mixologist import Mixologist, Job
import click
import logging
import json

app = Flask(__name__)


cache = base.Client(('localhost', 11211))

machine = Mixologist(12, 12, cache)

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
    if not 0 <= res < machine.num_res:
        logging.info("No valid reservoir with id %s", res)
    else:
        if machine.get_res(res).quantity + amount > machine.max:
            amount = machine.max - machine.get_res(res).quantity
        
        machine.fill(res, amount)
        logging.info("Filled reservoir %s with %s ozs", res, amount)

@app.cli.command('change')
@click.argument("res")
@click.argument("ingredient")
def change_liqure(res, ingredient):
    if not 0 <= res < machine.num_res:
        logging.info("No valid reservoir with id %s", res)
    else:
        machine.change_ingredient(res, ingredient)


############################################################################
#API Routing
############################################################################
@app.before_first_request
def startup():
    for i in range(machine.num_loc):
        cache.set('loc' + str(i), 0)

    for i in range(machine.num_res):
        machine.set_res_properties(i, i, machine.max)
    
    cache.set('state', json.loads({inv: machine.dump_state}))

@app.route('/api/v1/make-recipe', methods = ['POST'])
def app_make_drink():
    user = request.args.get('user')
    app.logger.info('Drink request received from user %s', user)

    loc = machine.add_drink()

    if loc == -1:
        return json.dumps({'location': -1})
    
    recipe = json.loads(request.args.get('recipe'))

    all_ingredients = True
    for r in recipe:
        exists = False
        for i in range(machine.num_res):
            if machine.get_res(i).ingredient == r['ingredient-id']:
                if machine.get_res(i).quantity >= r['amount']:
                    exists = True
        all_ingredients = all_ingredients and exists

    if not all_ingredients:
        return json.dumps({'location': -2})

    for r in recipe:
        for i in range(machine.num_res):
            if machine.get_res(i).ingredient == r['ingredient-id']:
                machine.pour(i, r['amount'])

    machine.set_thread(loc, Job(loc, 20, app))
    cache.set('state', json.loads({'inv': machine.dump_state}))

    response = {'200': {'location': loc}}
    return json.dumps(response)

@app.route('/api/v1/location', methods = ['GET'])
def app_get_status():
    loc = int(request.args.get('Location Number'))
    status = None
    progress = -1

    if not 0 <= loc < machine.num_loc:
        response = {'status': status, 'progress':progress}
        return json.dumps(response)


    if machine.get_thread(loc) != None and machine.get_thread(loc).is_alive():
        status = 'making'
        progress = machine.get_thread(loc).get_progress()
    elif machine.get_loc(loc).get_occupied() == True:
        status = 'done'
        progress = 1
    else:
        status = 'open'

    cache.set('state', json.loads({'inv': machine.dump_state}))
    response = {'200': {'status': status, 'progress':progress}}
    return json.dumps(response)

@app.route('/api/v1/inventory', methods = ['GET'])
def app_get_inventory():
    inv = machine.dump_state()

    response = {'inventory': inv}
    return json.dumps(response)