from flask import Flask, request
from mixologist import Mixologist, Job
import logging
import json

app = Flask(__name__)


machine = Mixologist(12, 12)

format = "[%(asctime)s]: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt='%H:%M:%S')


############################################################################
#API Routing
############################################################################
@app.before_first_request
def startup():
    for i in range(machine.num_res):
        machine.set_res_properties(i, i, machine.max)
    

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

    response = {'200': {'status': status, 'progress':progress}}
    return json.dumps(response)

@app.route('/api/v1/inventory', methods = ['GET'])
def app_get_inventory():
    inv = machine.dump_state()

    response = {'inventory': inv}
    return json.dumps(response)