from threading import Thread
import time
import json

format = '[%(asctime)s]: %(message)s'

class Mixologist():
    def __init__(self, num_res, num_loc, cache, max=60, units='oz'):
        self.max = max
        self.num_res = num_res
        self.res_pool = [Reservoir(i, max, units) for i in range(num_res)]
        self.num_loc = num_loc
        self.loc_pool = [Location() for _ in range(num_loc)]
        self.drinks_in_progress = 0
        self.cache = cache
    
    def add_drink(self):
        if self.drinks_in_progress >= self.num_loc:
            return -1

        for i in range(self.num_loc):
            if self.loc_pool[i].get_occupied() == False:
                self.cache.set('loc' + str(i), 1)
                self.loc_pool[i].set_occupied(True)
                self.drinks_in_progress += 1
                return i
    
        return -1

    #def remove_drink(self, loc):
        #if not 0 <= loc < self.num_loc:
            #return -1

        #self.loc_pool[loc].set_occupied(False)
        #self.cache.set('loc' + str(loc), 0)
        #self.drinks_in_progress -= 1

        #return 0

    def set_res_properties(self, res, ingredient, quantity):
        self.get_res(res).set_properties(ingredient, quantity)

    def get_thread(self, loc):
        return self.get_loc(loc).get_thread()

    def set_thread(self, loc, job):
        self.get_loc(loc).set_thread(job)

    def get_res(self, res):
        return self.res_pool[res]
    
    def pour(self, res, amount):
        self.get_res(res).pour(amount)

    def fill(self, res, amount):
        self.get_res(res).add(amount)

    def get_loc(self, loc):
        return self.loc_pool[loc]

    def dump_state(self):
        inv = list()

        for i in range(self.num_res):
            data = {
                "reservoir": i,
                "ingredient-id": self.get_res(i).ingredient, 
                "quantity": self.get_res(i).quantity,
                "units": self.get_res(i).units
                }
            inv.append(data)

        return inv

    def change_ingredient(self, res, id):
        self.get_res(res).set_properties(id, self.max)

class Reservoir():
    def __init__(self, id, max, units):
        self.id = id
        self.ingredient = -1
        self.quantity = 0
        self.max = max
        self.units = units
    
    def set_properties(self, ingredient, quantity):
        self.ingredient = ingredient
        if quantity > self.max:
            quantity = self.max
        self.quantity = quantity

    def pour(self, quantity):
        if quantity > self.quantity:
            return -1

        self.quantity -= quantity
        return 0

    def add(self, quantity):
        self.quantity += quantity

        if self.quantity > self.max:
            self.quantity = self.max

    def fill(self, quantity):
        self.quantity = self.max

class Location():
    def __init__(self):
        self.thread = None
        self.occupied = False
    
    def get_occupied(self):
        return self.occupied

    def set_occupied(self, o):
        self.occupied = o

    def get_thread(self):
        return self.thread

    def set_thread(self, t):
       self.thread = t
       t.start() 

    def clear_thread(self):
       self.thread = None

class Job(Thread):
    def __init__(self, loc, duration, app):
       Thread.__init__(self) 

       self.loc = loc
       self.duration = duration
       self.progress = 0
       self.app = app

    def run(self):
        self.app.logger.info('Starting drink at location %i', self.loc)

        for i in range(self.duration):
            time.sleep(1)
            self.progress += 1/self.duration

        self.progress = 1

        self.app.logger.info('Finished drink at location %i', self.loc)

    def get_progress(self):
        return self.progress

