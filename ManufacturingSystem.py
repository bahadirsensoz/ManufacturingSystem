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

        # Track machine setup for different products
        self.machine_setup = {i: None for i in range(machine_count)}
        self.setup_time = {i: 0 for i in range(machine_count)}

        # Metrics
        self.total_products_produced = 0
        self.total_waiting_times = {
            'machining': 0,
            'assembly': 0,
            'quality_control': 0,
            'packaging': 0
        }
        self.processed_parts = {
            'machining': 0,
            'assembly': 0,
            'quality_control': 0,
            'packaging': 0
        }

    def load_raw_material(self, raw_material):
        yield self.raw_materials.put(raw_material)
        print(f'Loaded raw material at {self.env.now}')

    def machining_process(self, part, product_type):
        with self.machining.request() as request:
            yield request
            machine_id = self.get_available_machine()
            if self.machine_setup[machine_id] != product_type:
                setup_time = random.uniform(0.5, 1.5)
                yield self.env.timeout(setup_time)
                self.machine_setup[machine_id] = product_type
                self.setup_time[machine_id] += setup_time

            start_time = self.env.now
            machining_time = random.uniform(4, 6)
            yield self.env.timeout(machining_time)
            wait_time = self.env.now - start_time
            self.total_waiting_times['machining'] += wait_time
            self.processed_parts['machining'] += 1
            print(f'Machined part for {product_type} at {self.env.now}')
            if random.random() < 0.1:  # 10% failure rate
                repair_time = random.uniform(1, 3)
                yield self.env.timeout(repair_time)
                print(f'Machine repaired at {self.env.now}')

    def assembly_process(self, part, product_type):
        with self.assembly.request() as request:
            yield request
            start_time = self.env.now
            assembly_time = random.uniform(2, 4)
            yield self.env.timeout(assembly_time)
            wait_time = self.env.now - start_time
            self.total_waiting_times['assembly'] += wait_time
            self.processed_parts['assembly'] += 1
            print(f'Assembled part for {product_type} at {self.env.now}')

    def quality_control_process(self, product, product_type):
        with self.quality_control.request() as request:
            yield request
            start_time = self.env.now
            qc_time = random.uniform(1, 2)
            yield self.env.timeout(qc_time)
            wait_time = self.env.now - start_time
            self.total_waiting_times['quality_control'] += wait_time
            self.processed_parts['quality_control'] += 1
            print(f'Quality checked product for {product_type} at {self.env.now}')

    def packaging_process(self, product, product_type):
        with self.packaging.request() as request:
            yield request
            start_time = self.env.now
            packaging_time = random.uniform(0.5, 1.5)
            yield self.env.timeout(packaging_time)
            wait_time = self.env.now - start_time
            self.total_waiting_times['packaging'] += wait_time
            self.processed_parts['packaging'] += 1
            print(f'Packaged product for {product_type} at {self.env.now}')
            self.total_products_produced += 1

    def run_production(self, product_type):
        while True:
            if self.shift.is_active:
                raw_material = f'raw_material_{product_type}'
                yield self.env.process(self.load_raw_material(raw_material))
                yield self.env.process(self.machining_process(raw_material, product_type))
                yield self.env.process(self.assembly_process(raw_material, product_type))
                yield self.env.process(self.quality_control_process(raw_material, product_type))
                yield self.env.process(self.packaging_process(raw_material, product_type))
                yield self.env.timeout(1)
            else:
                yield self.env.timeout(1)

    def get_available_machine(self):
        for i in range(len(self.machine_setup)):
            if self.machining.count < self.machining.capacity:
                return i
        return 0

def run_simulation(env, system, product_types):
    for product_type in product_types:
        env.process(system.run_production(product_type))

def run_scenario(machine_count, shift_start, shift_end, product_types):
    env = simpy.Environment()
    system = ManufacturingSystem(env, machine_count, shift_start, shift_end)
    print(f'Started scenario with {machine_count} machines, shift {shift_start}-{shift_end}, products: {product_types}')
    run_simulation(env, system, product_types)
    env.run(until=200)
    print(f'Completed scenario with {machine_count} machines, shift {shift_start}-{shift_end}, products: {product_types}')

    return system

# Running different scenarios and collecting results
results = []

scenarios = [
    (2, 8, 20, ['A', 'B']),
    (3, 6, 18, ['A', 'B']),
    (1, 7, 19, ['A', 'B', 'C']),
    (4, 6, 18, ['A']),
    (2, 8, 16, ['B', 'C']),
    (3, 9, 21, ['A', 'C']),
    (2, 7, 19, ['A', 'B', 'C']),
    (5, 5, 17, ['A', 'B', 'C', 'D']),
    (1, 8, 20, ['B', 'C', 'D', 'E']),
    (4, 8, 20, ['A', 'B', 'C'])
]

for scenario in scenarios:
    machine_count, shift_start, shift_end, product_types = scenario
    system = run_scenario(machine_count, shift_start, shift_end, product_types)

    avg_waiting_time_machining = system.total_waiting_times['machining'] / system.processed_parts['machining'] if system.processed_parts['machining'] > 0 else 0
    avg_waiting_time_assembly = system.total_waiting_times['assembly'] / system.processed_parts['assembly'] if system.processed_parts['assembly'] > 0 else 0
    avg_waiting_time_quality_control = system.total_waiting_times['quality_control'] / system.processed_parts['quality_control'] if system.processed_parts['quality_control'] > 0 else 0
    avg_waiting_time_packaging = system.total_waiting_times['packaging'] / system.processed_parts['packaging'] if system.processed_parts['packaging'] > 0 else 0

    # Print average waiting times for debugging
    print(f'Average Waiting Time (Machining): {avg_waiting_time_machining}')
    print(f'Average Waiting Time (Assembly): {avg_waiting_time_assembly}')
    print(f'Average Waiting Time (Quality Control): {avg_waiting_time_quality_control}')
    print(f'Average Waiting Time (Packaging): {avg_waiting_time_packaging}')

    results.append({
        'Machine Count': machine_count,
        'Shift Start': shift_start,
        'Shift End': shift_end,
        'Product Types': ', '.join(product_types),
        'Total Products Produced': system.total_products_produced,
        'Average Waiting Time (Machining)': f'{avg_waiting_time_machining:.2f}'.replace('.', ','),
        'Average Waiting Time (Assembly)': f'{avg_waiting_time_assembly:.2f}'.replace('.', ','),
        'Average Waiting Time (Quality Control)': f'{avg_waiting_time_quality_control:.2f}'.replace('.', ','),
        'Average Waiting Time (Packaging)': f'{avg_waiting_time_packaging:.2f}'.replace('.', ',')
    })

# Displaying the results
df = pd.DataFrame(results)
print(df)

# Save the results to a CSV file using semicolon as delimiter
df.to_csv('simulation_results.csv', index=False, sep=';')
