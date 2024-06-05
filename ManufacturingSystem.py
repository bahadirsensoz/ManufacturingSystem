import simpy
import random
import pandas as pd


class Shift:
    def __init__(self, env, start_time, end_time):
        self.env = env
        self.start_time = start_time
        self.end_time = end_time
        self.is_active = False
        self.process = env.process(self.run())

    def run(self):
        while True:
            now = self.env.now % 24
            if now < self.start_time:
                yield self.env.timeout(self.start_time - now)
            elif now >= self.start_time and now < self.end_time:
                self.is_active = True
                yield self.env.timeout(self.end_time - now)
                self.is_active = False
                yield self.env.timeout(24 - (self.end_time - now))
            else:
                self.is_active = False
                yield self.env.timeout(24 - now + self.start_time)


class ManufacturingSystem:
    def __init__(self, env, machine_count=2, shift_start=8, shift_end=20):
        self.env = env
        self.raw_materials = simpy.Store(env)
        self.machining = simpy.Resource(env, capacity=machine_count)
        self.assembly = simpy.Resource(env, capacity=2)
        self.quality_control = simpy.Resource(env, capacity=1)
        self.packaging = simpy.Resource(env, capacity=1)
        self.shift = Shift(env, start_time=shift_start, end_time=shift_end)

        # Metrics
        self.total_products_produced = 0
        self.waiting_times = {
            'machining': [],
            'assembly': [],
            'quality_control': [],
            'packaging': []
        }

    def load_raw_material(self, raw_material):
        yield self.raw_materials.put(raw_material)
        print(f'Loaded raw material at {self.env.now}')

    def machining_process(self, part):
        with self.machining.request() as request:
            yield request
            start_time = self.env.now
            machining_time = random.uniform(4, 6)
            yield self.env.timeout(machining_time)
            wait_time = self.env.now - start_time
            self.waiting_times['machining'].append(wait_time)
            print(f'Machined part at {self.env.now}')
            if random.random() < 0.1:  # 10% failure rate
                repair_time = random.uniform(1, 3)
                yield self.env.timeout(repair_time)
                print(f'Machine repaired at {self.env.now}')

    def assembly_process(self, part):
        with self.assembly.request() as request:
            yield request
            start_time = self.env.now
            assembly_time = random.uniform(2, 4)
            yield self.env.timeout(assembly_time)
            wait_time = self.env.now - start_time
            self.waiting_times['assembly'].append(wait_time)
            print(f'Assembled part at {self.env.now}')

    def quality_control_process(self, product):
        with self.quality_control.request() as request:
            yield request
            start_time = self.env.now
            qc_time = random.uniform(1, 2)
            yield self.env.timeout(qc_time)
            wait_time = self.env.now - start_time
            self.waiting_times['quality_control'].append(wait_time)
            print(f'Quality checked product at {self.env.now}')

    def packaging_process(self, product):
        with self.packaging.request() as request:
            yield request
            start_time = self.env.now
            packaging_time = random.uniform(0.5, 1.5)
            yield self.env.timeout(packaging_time)
            wait_time = self.env.now - start_time
            self.waiting_times['packaging'].append(wait_time)
            print(f'Packaged product at {self.env.now}')
            self.total_products_produced += 1

    def run_production(self, product_type):
        while True:
            if self.shift.is_active:
                raw_material = f'raw_material_{product_type}'
                yield self.env.process(self.load_raw_material(raw_material))
                yield self.env.process(self.machining_process(raw_material))
                yield self.env.process(self.assembly_process(raw_material))
                yield self.env.process(self.quality_control_process(raw_material))
                yield self.env.process(self.packaging_process(raw_material))
                yield self.env.timeout(1)
            else:
                yield self.env.timeout(1)


def run_simulation(env, system, product_types):
    for product_type in product_types:
        env.process(system.run_production(product_type))


def run_scenario(machine_count, shift_start, shift_end, product_types):
    env = simpy.Environment()
    system = ManufacturingSystem(env, machine_count, shift_start, shift_end)
    run_simulation(env, system, product_types)
    env.run(until=200)
    print(
        f'Completed scenario with {machine_count} machines, shift {shift_start}-{shift_end}, products: {product_types}')

    return system


# Running different scenarios and collecting results
results = []

scenarios = [
    (2, 8, 20, ['A', 'B']),
    (3, 6, 18, ['A', 'B']),
    (1, 7, 19, ['A', 'B', 'C'])
]

for scenario in scenarios:
    machine_count, shift_start, shift_end, product_types = scenario
    system = run_scenario(machine_count, shift_start, shift_end, product_types)
    results.append({
        'Scenario': f'{machine_count} machines, shift {shift_start}-{shift_end}, products: {product_types}',
        'Total Products Produced': system.total_products_produced,
        'Average Waiting Time (Machining)': sum(system.waiting_times['machining']) / len(
            system.waiting_times['machining']) if system.waiting_times['machining'] else 0,
        'Average Waiting Time (Assembly)': sum(system.waiting_times['assembly']) / len(
            system.waiting_times['assembly']) if system.waiting_times['assembly'] else 0,
        'Average Waiting Time (Quality Control)': sum(system.waiting_times['quality_control']) / len(
            system.waiting_times['quality_control']) if system.waiting_times['quality_control'] else 0,
        'Average Waiting Time (Packaging)': sum(system.waiting_times['packaging']) / len(
            system.waiting_times['packaging']) if system.waiting_times['packaging'] else 0
    })

# Displaying the results
df = pd.DataFrame(results)
print(df)

# Optionally, save the results to a CSV file
df.to_csv('simulation_results.csv', index=False)
