import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from tqdm import tqdm
import pandas as pd
from sklearn.model_selection import ParameterGrid
import os
import imageio
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from IPython.display import Image, display
import json

class Agent:
    def __init__(self, position, desired_speed, max_speed, vision_radius, width, height):
        self.position = np.array(position)
        self.velocity = np.zeros(2)
        self.desired_speed = desired_speed
        self.max_speed = max_speed
        self.vision_radius = vision_radius
        self.width = width
        self.height = height
        self.goal_position = np.random.rand(2) * [self.width, self.height]  
        self.path = []


class CrowdSimulator:
    def __init__(self, num_agents, width, height, model='social_force'):
        self.num_agents = num_agents
        self.width = width
        self.height = height
        self.model = model
        self.agents = [Agent(np.random.rand(2) * [width, height],
                             np.random.uniform(0.8, 1.2),
                             np.random.uniform(1.5, 2.0),
                             np.random.uniform(2.0, 3.0),
                             width, height) for _ in range(num_agents)] 
        self.time_step = 0.1
        self.step = 0  # Zmienna do zliczania kroków

        ### Parametry modelu
        self.social_force_strength = 1.2
        self.repulsion_strength = 0.9
        self.cellular_automata_prob = 0.7
        self.social_distance = 2.0
        self.obstacles = []


    def add_obstacle(self, x, y, width, height):
        self.obstacles.append((x, y, width, height))

    def update(self):
        self.step += 1 

        # Co 50 kroków przypisujemy nowy losowy cel agentowi
        if self.step % 50 == 0:
            for agent in self.agents:
                agent.goal_position = np.random.rand(2) * [self.width, self.height]

        if self.model == 'social_force':
            self._update_social_force()
        elif self.model == 'cellular_automata':
            self._update_cellular_automata()
        elif self.model == 'social_distance':
            self._update_social_distance()

        for agent in self.agents:
            agent.position = np.clip(agent.position, [0, 0], [self.width, self.height])

    def _update_social_force(self):
        positions = np.array([agent.position for agent in self.agents])
        velocities = np.array([agent.velocity for agent in self.agents])
    
        distances = cdist(positions, positions)
        np.fill_diagonal(distances, np.inf)
    
        # Siły społeczne
        diff = positions[:, np.newaxis] - positions
        with np.errstate(divide='ignore', invalid='ignore'):
            force_social = np.nan_to_num(np.sum(diff / distances[:, :, np.newaxis] ** 2, axis=1), nan=0, posinf=0, neginf=0)
    
        # Siły odpychające
        force_repulsion = np.exp(-distances / 0.5)[:, :, np.newaxis] * diff
        force_repulsion = np.sum(force_repulsion, axis=1)
    
        # Siła dążenia do celu (do losowego punktu)
        force_goal = np.array([agent.goal_position - agent.position for agent in self.agents])
    
        # Siła unikania przeszkód
        force_obstacle = self._calculate_obstacle_force()
    
        # Siła odpychającą od krawędzi
        edge_force = np.zeros_like(positions)
        edge_force[:, 0] = 1 / (positions[:, 0] + 1e-5) - 1 / (self.width - positions[:, 0] + 1e-5)
        edge_force[:, 1] = 1 / (positions[:, 1] + 1e-5) - 1 / (self.height - positions[:, 1] + 1e-5)
    
        # Suma sił
        total_force = (self.social_force_strength * force_social +
                       self.repulsion_strength * force_repulsion +
                       force_goal + force_obstacle +
                       0.5 * edge_force)
    
        # Aktualizacja prędkości i pozycji
        for i, agent in enumerate(self.agents):
            agent.velocity += total_force[i] * self.time_step
            speed = np.linalg.norm(agent.velocity)
            if speed > agent.max_speed:
                agent.velocity = agent.velocity / speed * agent.max_speed
    
            agent.path.append(agent.position.copy())


    def _calculate_obstacle_force(self):
        force_obstacle = np.zeros((self.num_agents, 2))
        for agent in self.agents:
            for obs in self.obstacles:
                dx = max(obs[0] - agent.position[0], 0, agent.position[0] - (obs[0] + obs[2]))
                dy = max(obs[1] - agent.position[1], 0, agent.position[1] - (obs[1] + obs[3]))
                distance = np.sqrt(dx ** 2 + dy ** 2)
                if distance < agent.vision_radius:
                    force = (agent.position - np.array([obs[0] + obs[2] / 2, obs[1] + obs[3] / 2])) / (
                            distance ** 2 + 1e-6)
                    force_obstacle[self.agents.index(agent)] += force
        return force_obstacle

    def _update_cellular_automata(self):
        grid = np.zeros((self.width, self.height))
        for agent in self.agents:
            x, y = agent.position.astype(int)
            grid[x, y] = 1

        for agent in self.agents:
            x, y = agent.position.astype(int)
            neighbors = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
            valid_neighbors = [(nx, ny) for nx, ny in neighbors
                               if 0 <= nx < self.width and 0 <= ny < self.height and grid[nx, ny] == 0]

            if valid_neighbors and np.random.random() < self.cellular_automata_prob:
                new_x, new_y = valid_neighbors[np.random.randint(len(valid_neighbors))]
                agent.position = np.array([new_x, new_y])

            agent.path.append(agent.position.copy())

    def _update_social_distance(self):
        positions = np.array([agent.position for agent in self.agents])
        distances = cdist(positions, positions)
        np.fill_diagonal(distances, np.inf)

        for i, agent in enumerate(self.agents):
            too_close = distances[i] < self.social_distance
            if np.any(too_close):
                move_direction = np.mean(agent.position - positions[too_close], axis=0)
                agent.position += move_direction * self.time_step
            agent.path.append(agent.position.copy())

    def simulate(self, steps):
        for step in tqdm(range(steps), desc="Simulating"):
            self.update()
            if step % 10 == 0:
                print(f"Step {step}: {[agent.position for agent in self.agents[:5]]}")
        return [agent.path for agent in self.agents]


def visualize_simulation(simulator, history):
    fig, ax = plt.subplots(figsize=(10, 10))

    if not os.path.exists('frames'):
        os.makedirs('frames')

    for i, frame in enumerate(tqdm(zip(*history), desc="Rendering")):
        ax.clear()
        x_positions = [pos[0] for pos in frame]
        y_positions = [pos[1] for pos in frame]

        if not x_positions or not y_positions:
            print(f"Warning: No positions to plot in frame {i}")
            continue

        ax.scatter(x_positions, y_positions)
        for obs in simulator.obstacles:
            rect = plt.Rectangle((obs[0], obs[1]), obs[2], obs[3], fill=True, color='gray')
            ax.add_patch(rect)
        ax.set_xlim(0, simulator.width)
        ax.set_ylim(0, simulator.height)

        canvas = FigureCanvas(fig)
        canvas.draw()
        plt.savefig(f'frames/frame_{i:04d}.png')

    plt.close(fig)

    print("Klatki zostały zapisane w folderze 'frames'.")
    create_gif('frames', 'crowd_simulation.gif', fps=10)


def calibrate_model(simulator, target_density, param_name, param_range):
    densities = []

    for param_value in param_range:
        setattr(simulator, param_name, param_value)
        history = simulator.simulate(100)
        final_positions = [path[-1] for path in history]
        density = len(final_positions) / (simulator.width * simulator.height)
        densities.append(density)

    best_param = param_range[np.argmin(np.abs(np.array(densities) - target_density))]
    return best_param


def validate_model(simulator, steps):
    history = simulator.simulate(steps)

    avg_speed = np.mean([np.mean(np.linalg.norm(np.diff(path, axis=0), axis=1)) for path in history])
    final_positions = [path[-1] for path in history]
    final_density = len(final_positions) / (simulator.width * simulator.height)

    return avg_speed, final_density

def save_simulation_data(simulator, avg_density, avg_speed, filename="simulation_data.json"):
    """Zapisuje dane symulacji do pliku JSON."""
    data = {
        "num_agents": simulator.num_agents,
        "width": simulator.width,
        "height": simulator.height,
        "model": simulator.model,
        "social_force_strength": simulator.social_force_strength,
        "repulsion_strength": simulator.repulsion_strength,
        "cellular_automata_prob": simulator.cellular_automata_prob,
        "social_distance": simulator.social_distance,
        "avg_density": avg_density,
        "avg_speed": avg_speed,
    }
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"Dane symulacji zapisano do pliku: {filename}")


def generate_statistics(simulator, history):
    avg_speed = np.mean([np.mean(np.linalg.norm(np.diff(path, axis=0), axis=1)) for path in history])
    densities = [len([path[i] for path in history]) / (simulator.width * simulator.height)
                 for i in range(len(history[0]))]
    avg_density = np.mean(densities)

    plt.figure(figsize=(10, 5))
    plt.plot(densities)
    plt.title('Gęstość tłumu w czasie')
    plt.xlabel('Krok symulacji')
    plt.ylabel('Gęstość')
    plt.savefig('density_over_time.png')
    plt.close()

    return avg_speed, avg_density


def create_gif(frame_folder, output_file='crowd_simulation.gif', fps=10):
    images = []
    for filename in sorted(os.listdir(frame_folder)):
        if filename.endswith(".png"):
            file_path = os.path.join(frame_folder, filename)
            images.append(imageio.imread(file_path))

    imageio.mimsave(output_file, images, fps=fps)
    print(f"GIF został zapisany jako {output_file}")

def parameter_sweep(simulator, param_grid):
    results = []
    for params in ParameterGrid(param_grid):
        for param, value in params.items():
            setattr(simulator, param, value)

        history = simulator.simulate(200)
        avg_speed, final_density = validate_model(simulator, 200)

        results.append({**params, 'avg_speed': avg_speed, 'final_density': final_density})

    df = pd.DataFrame(results)
    df = df.groupby(['social_force_strength', 'repulsion_strength', 'cellular_automata_prob']).mean().reset_index()
    return df


### Użycie symulatora
simulator = CrowdSimulator(num_agents=500, width=40, height=40, model='social_force')
simulator.add_obstacle(18, 18, 4, 4)
simulator.add_obstacle(30, 15, 4, 10)
simulator.add_obstacle(30, 7, 10, 4)
simulator.add_obstacle(18, 0, 7, 12)
simulator.add_obstacle(3, 12, 10, 3)
simulator.add_obstacle(10, 4, 3, 11)
simulator.add_obstacle(0, 0, 6, 6)
simulator.add_obstacle(0, 21, 12, 4)
simulator.add_obstacle(5, 30, 7, 4)
simulator.add_obstacle(17, 30, 10, 4)
simulator.add_obstacle(32, 30, 2, 7)
simulator.add_obstacle(32, 30, 5, 2)


### Kalibracja
target_density = 0.3
best_strength = calibrate_model(simulator, target_density, 'social_force_strength', np.linspace(0.5, 5, 10))
simulator.social_force_strength = best_strength

### Symulacja
history = simulator.simulate(200)

### Wizualizacja
visualize_simulation(simulator, history)

### Generowanie statystyk
avg_speed, avg_density = generate_statistics(simulator, history)
print(f"Średnia prędkość: {avg_speed:.2f}")
print(f"Średnia gęstość: {avg_density:.2f}")


save_simulation_data(simulator, avg_density, avg_speed)
### Wyświetl GIF
display(Image(filename='crowd_simulation.gif'))
