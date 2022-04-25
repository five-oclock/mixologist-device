from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/api/v1/make-recipe/', methods = ['POST'])
def app_make_drink():
    req = request.json
    print(req)
    #user = req['user']
    #app.logger.info('Drink request received from user %s', user)

    #loc = machine.add_drink()

    #if loc == -1:
        #return json.dumps({'location': -1})
    
    #recipe = json.loads(req['recipe'])

    #all_ingredients = True
    #for r in recipe:
        #exists = False
        #for i in range(machine.num_res):
            #if machine.get_res(i).ingredient == r['ingredient-id']:
                #if machine.get_res(i).quantity >= r['amount']:
                    #exists = True
        #all_ingredients = all_ingredients and exists

    #if not all_ingredients:
        #return json.dumps({'location': -2})

    #for r in recipe:
        #for i in range(machine.num_res):
            #if machine.get_res(i).ingredient == r['ingredient-id']:
                #machine.pour(i, r['amount'])

    #machine.set_thread(loc, Job(loc, 20, app))
    #state = machine.dump_state()
    #cache.set('state', json.dumps({'inv': state}))

    #response = {'200': {'location': 0}}
    return "hello"