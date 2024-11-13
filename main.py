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
        """Calculate all required transmissions based on packet flows."""
        self.total_transmissions.clear()
        
        # Compute in-degree for topological sorting
        in_degree = {device: 0 for device in self.devices}
        for sender in self.connections:
            for receiver in self.connections[sender]:
                in_degree[receiver] += 1
                
        # Initialize queue with devices having in-degree 0
        queue = deque([device for device in self.devices if in_degree[device] == 0])
        
        # Initialize packet counts: total_packets[device] = original_packets + received packets
        total_packets = defaultdict(int)
        for device in self.devices:
            total_packets[device] += self.original_packets.get(device, 0)
        
        while queue:
            current = queue.popleft()
            current_packets = total_packets[current]
            
            for neighbor in self.connections[current]:
                # Add current's packets to the neighbor's incoming packets
                total_packets[neighbor] += current_packets
                
                # Record the transmission
                self.total_transmissions[current][neighbor] += current_packets
                
                # Decrease in-degree and add to queue if zero
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        # Check for cycles
        if any(degree > 0 for degree in in_degree.values()):
            raise ValueError("Network topology contains cycles, which is not supported.")
        
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
    
    def optimize_schedule(self, schedule: List[List[Tuple[str, str]]]) -> List[List[List[Tuple[str, str]]]]:
        optimized_schedule = []

        # function to check if transmission 3 hops away
        def check_shortest_path(transmission1: Tuple[str, str], transmission2: Tuple[str, str]) -> int:
            path1 = self.shortest_path[transmission1[0]][transmission2[1]]
            path2 = self.shortest_path[transmission1[1]][transmission2[0]]

            return min(path1, path2)

        # optimizing transmission into one channel
        for time_slot, transmissions in enumerate(schedule):
            channel = []
            added_transmissions_check = {}
            for i in range(len(transmissions)):
                transmission_x = transmissions[i]

                # if transmission already added to one channel, then no need to iterate it 
                if transmission_x in added_transmissions_check:
                    continue
                
                added_transmissions_check[transmission_x] = True
                added_transmissions = [transmission_x]
                for j in range(i+1, len(transmissions)):
                    transmission_y = transmissions[j]
                    check = True

                    # iterate through all transmission in one channel
                    for k_transmission in added_transmissions:
                        path = check_shortest_path(transmission_y, k_transmission)
                        if path < 3:
                            check = False
                            break

                    # if shortest path is less than 3, then unite in one channel
                    if check:
                        added_transmissions.append(transmission_y)
                        added_transmissions_check[transmission_y] = True

                channel.append(added_transmissions)

            optimized_schedule.append(channel)

        return optimized_schedule

    def print_schedule(self, schedule: List[List[List[Tuple[str, str]]]]) -> None:
        """Print the schedule in a readable format."""
        if not schedule:
            print("\nNo transmissions scheduled.")
            return
            
        print("\nTransmission Schedule:")
        print("---------------------")
        for time_slot, channels in enumerate(schedule):
            print(f"\nTime Slot {time_slot}:")
            for channel_id, transmissions in enumerate(channels):
                print(f"   Channel Id {channel_id}")
                for sender, receiver in transmissions:
                    print(f"      {sender} → {receiver}")
        
        print("\nTransmission Requirements:")
        print("-------------------------")
        for sender in sorted(self.total_transmissions.keys()):
            for receiver, count in sorted(self.total_transmissions[sender].items()):
                print(f"{sender} → {receiver}: {count} transmission(s)")

# Example usage for the given topology
def example_usage():
    scheduler = NetworkScheduler()
    
    # Add devices (assuming 1 original packet each for simplicity)
    for device in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        scheduler.add_device(device, 1)
    
    # Add transmission paths
    scheduler.add_transmission_path('A', 'B')
    scheduler.add_transmission_path('A', 'C')
    scheduler.add_transmission_path('B', 'D')
    scheduler.add_transmission_path('C', 'D')
    scheduler.add_transmission_path('D', 'E')
    scheduler.add_transmission_path('E', 'F')
    scheduler.add_transmission_path('F', 'G')
    scheduler.add_transmission_path('G', 'H')
    
    # Generate and print schedule
    schedule = scheduler.generate_schedule()
    optimized_schedule = scheduler.optimize_schedule(schedule)
    scheduler.print_schedule(optimized_schedule)
    
if __name__ == "__main__":
    example_usage()