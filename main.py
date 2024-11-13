from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

class NetworkScheduler:
    def __init__(self):
        self.devices = set()
        self.connections = defaultdict(set)
        self.original_packets = {}  # Packets originated by each device
        self.forwarding_paths = defaultdict(list)  # List of paths each packet must take
        self.total_transmissions = defaultdict(lambda: defaultdict(int))  # {sender: {receiver: count}}
        self.interference_graph = defaultdict(set)
        self.shortest_path = defaultdict(lambda: defaultdict(int)) # {node: {node: count }}
        
    def add_device(self, device_id: str, packets: int) -> None:
        """Add a device with its original packets per frame."""
        self.devices.add(device_id)
        self.original_packets[device_id] = packets
        
    def add_transmission_path(self, sender: str, receiver: str) -> None:
        """Add a directional transmission path from sender to receiver."""
        if sender not in self.devices or receiver not in self.devices:
            raise ValueError("Both sender and receiver must be added as devices first")
        self.connections[sender].add(receiver)

    def _calculate_shortest_path_between_all_nodes(self) -> None:  # Floyd–Warshall algorithm
        inf = 1e9 # infinity 
        shortest_path = defaultdict(lambda: defaultdict(int))
        for i in self.devices:
            for j in self.devices:
                shortest_path[i][j] = inf
        
        for i in self.devices:
            shortest_path[i][i] = 0
        
        for sender in self.devices:
            for receiver in self.connections[sender]:
                shortest_path[sender][receiver] = 1
                shortest_path[receiver][sender] = 1

        for k_device in self.devices:
            for i_device in self.devices:
                for j_device in self.devices:
                    shortest_path[i_device][j_device] = min(shortest_path[i_device][j_device], 
                                                                shortest_path[i_device][k_device] + shortest_path[k_device][j_device])
        self.shortest_path = shortest_path

    def _calculate_forwarding_requirements(self) -> None:
        """Calculate all forwarding paths and required transmissions."""
        self.total_transmissions.clear()
        
        # First, add original packet transmissions
        for sender in self.devices:
            for receiver in self.connections[sender]:
                self.total_transmissions[sender][receiver] = self.original_packets[sender]
        
        # Then calculate forwarding requirements using BFS for each source-destination pair
        for source in self.devices:
            packets = self.original_packets[source]
            if packets == 0:
                continue
                
            # Find all paths from this source
            visited = set()
            queue = deque([(source, [source])])
            
            while queue:
                current, path = queue.popleft()
                
                # For each neighbor of the current node
                for next_node in self.connections[current]:
                    if next_node not in path:  # Avoid cycles
                        new_path = path + [next_node]
                        self.forwarding_paths[source].append(new_path)
                        
                        # Add forwarding requirement
                        if len(new_path) > 2:  # If path requires forwarding
                            for i in range(len(new_path) - 1):
                                sender = new_path[i]
                                receiver = new_path[i + 1]
                                if i > 0:  # This is a forwarding transmission
                                    self.total_transmissions[sender][receiver] += packets
                                    
                        queue.append((next_node, new_path))
        
    def _build_interference_graph(self) -> None:
        """Build interference graph based on network topology."""
        # Create list of all required transmissions
        transmissions = []
        for sender in self.devices:
            for receiver, count in self.total_transmissions[sender].items():
                for _ in range(count):
                    transmissions.append((sender, receiver))
        
        # Create nodes in interference graph for each transmission
        for i, trans1 in enumerate(transmissions):
            sender1, receiver1 = trans1
            for j, trans2 in enumerate(transmissions):
                if i >= j:
                    continue
                    
                sender2, receiver2 = trans2
                
                # Transmissions interfere if:
                # 1. They share a sender
                # 2. They share a receiver
                # 3. A receiver in one is a sender in another
                if (sender1 == sender2 or
                    receiver1 == receiver2 or
                    sender1 == receiver2 or
                    sender2 == receiver1):
                    self.interference_graph[i].add(j)
                    self.interference_graph[j].add(i)
        
        self.transmissions = transmissions
        
    def _color_graph(self) -> Dict[int, int]:
        """Color the interference graph using a greedy algorithm."""
        colors = {}
        
        # Sort nodes by degree for better coloring
        nodes = sorted(self.interference_graph.keys(), 
                      key=lambda x: len(self.interference_graph[x]),
                      reverse=True)
        
        for node in nodes:
            used_colors = {colors[neighbor] 
                         for neighbor in self.interference_graph[node] 
                         if neighbor in colors}
            
            color = 0
            while color in used_colors:
                color += 1
            colors[node] = color
            
        return colors
        
    def generate_schedule(self) -> List[List[Tuple[str, str]]]:
        """Generate an optimized transmission schedule."""
        self._calculate_shortest_path_between_all_nodes()
        self._calculate_forwarding_requirements()
        self._build_interference_graph()
        colors = self._color_graph()
        
        # Group transmissions by time slot (color)
        schedule = defaultdict(list)
        for trans_id, color in colors.items():
            schedule[color].append(self.transmissions[trans_id])
            
        # Convert to list of time slots
        max_slot = max(colors.values()) if colors else -1
        final_schedule = []
        for slot in range(max_slot + 1):
            final_schedule.append(schedule[slot])
            
        return final_schedule
    
    def print_schedule(self, schedule: List[List[Tuple[str, str]]]) -> None:
        """Print the schedule in a readable format."""
        if not schedule:
            print("\nNo transmissions scheduled.")
            return
            
        print("\nTransmission Schedule:")
        print("---------------------")
        for time_slot, transmissions in enumerate(schedule):
            print(f"\nTime Slot {time_slot}:")
            for sender, receiver in transmissions:
                print(f"  {sender} → {receiver}")
        
        print("\nTransmission Requirements:")
        print("-------------------------")
        for sender in sorted(self.total_transmissions.keys()):
            for receiver, count in sorted(self.total_transmissions[sender].items()):
                print(f"{sender} → {receiver}: {count} transmission(s)")

# Example usage for the given topology
def example_usage():
    scheduler = NetworkScheduler()
    
    # Add devices (assuming 1 original packet each for simplicity)
    for device in ['A', 'B', 'C', 'D', 'E']:
        scheduler.add_device(device, 1)
    
    # Add transmission paths as shown in the image
    scheduler.add_transmission_path('A', 'B')
    scheduler.add_transmission_path('C', 'D')
    scheduler.add_transmission_path('B', 'E')
    scheduler.add_transmission_path('D', 'E')
    
    # Generate and print schedule
    schedule = scheduler.generate_schedule()
    scheduler.print_schedule(schedule)
    
if __name__ == "__main__":
    example_usage()