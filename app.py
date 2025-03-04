import streamlit as st
from streamlit_option_menu import option_menu
import psutil
import platform
import pynvml
from datetime import datetime
import plotly.graph_objects as go
import time
from tabulate import tabulate
from collections import deque
import plotly.graph_objs as go
import os
import platform

def get_disk_usage():
    if os.name == 'nt':  # Windows
        return psutil.disk_usage('C:\\')
    else:  # Unix-like
        return psutil.disk_usage('/')

# Usage in your code
disk_percent = get_disk_usage().percent

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def system_overview():
    st.title("System Overview")

    # System Information
    st.header("System Information")
    uname = platform.uname()
    system_info = {
        "System": uname.system,
        "Node Name": uname.node,
        "Release": uname.release,
        "Version": uname.version,
        "Machine": uname.machine,
        "Processor": uname.processor
    }
    
    st.table(system_info.items())

    # CPU Information
    st.header("CPU Information")
    cpu_freq = psutil.cpu_freq()
    cpu_info = {
        "Physical Cores": psutil.cpu_count(logical=False),
        "Total Cores": psutil.cpu_count(logical=True),
        "Max Frequency": f"{cpu_freq.max:.2f} MHz",
        "Min Frequency": f"{cpu_freq.min:.2f} MHz",
        "Current Frequency": f"{cpu_freq.current:.2f} MHz",
        "CPU Usage": f"{psutil.cpu_percent()}%"
    }
    
    st.table(cpu_info.items())

    # Memory Information
    st.header("Memory Information")
    svmem = psutil.virtual_memory()
    memory_info = {
        "Total": get_size(svmem.total),
        "Available": get_size(svmem.available),
        "Used": get_size(svmem.used),
        "Percentage": f"{svmem.percent}%",
        "Swap Total": get_size(psutil.swap_memory().total),
        "Swap Used": get_size(psutil.swap_memory().used)
    }
    
    st.table(memory_info.items())

    # Disk Information
    st.header("Disk Information")
    disk_info = []
    partitions = psutil.disk_partitions()
    
    for partition in partitions:
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                "Disk": partition.device,
                "Total Size": get_size(partition_usage.total),
                "Used": get_size(partition_usage.used),
                "Free": get_size(partition_usage.free),
                "Percentage": f"{partition_usage.percent}%"
            })
        except PermissionError:
            continue
    
    st.table(disk_info)

    # GPU Information
    st.header("GPU Information")
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            
            # Get device name without decoding
            device_name = pynvml.nvmlDeviceGetName(handle)
            
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            st.subheader(f"GPU: {device_name}")  # No need to decode
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Memory Total", get_size(memory_info.total))
                st.metric("Memory Free", get_size(memory_info.free))
            with col2:
                st.metric("Memory Used", get_size(memory_info.used))
                st.metric("GPU Utilization", f"{pynvml.nvmlDeviceGetUtilizationRates(handle).gpu}%")
        pynvml.nvmlShutdown()
    except pynvml.NVMLError:
        st.write("No NVIDIA GPU detected or NVIDIA drivers not installed")


    # Network Information
    # st.header("Network Information")
    # network_info_list = []
    
    # if_addrs = psutil.net_if_addrs()
    
    # for interface_name, interface_addresses in if_addrs.items():
    #     for addr in interface_addresses:
    #         if str(addr.family) == 'AddressFamily.AF_INET':
    #             network_info_list.append({
    #                 "Interface": interface_name,
    #                 "IP Address": addr.address,
    #                 "Netmask": addr.netmask,
    #                 "Broadcast IP": addr.broadcast
    #             })

    # if network_info_list:
    #     st.table(network_info_list)

def process_manager():
    st.title("Process Manager")
    
    # Create static elements outside the loop
    sort_by = st.radio("Sort by:", ("Memory Usage", "CPU Usage"), key="sort_option")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        show_memory = st.checkbox("Show Memory Usage", value=True, key="show_memory")
    with col2:
        show_cpu = st.checkbox("Show CPU Usage", value=True, key="show_cpu")
    with col3:
        show_status = st.checkbox("Show Status", value=True, key="show_status")
    
    # Create a placeholder for the table
    table_placeholder = st.empty()
    
    # Create input and button for killing process
    pid_to_kill = st.number_input("Enter PID to kill:", min_value=1, step=1, key="pid_input")
    kill_button = st.button("Kill Process", key="kill_button")
    
    while True:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'memory_percent', 'cpu_percent']):
            try:
                process = proc.info
                processes.append([
                    process['pid'],
                    process['name'],
                    f"{process['memory_percent']:.2f}%" if show_memory else "",
                    f"{process['cpu_percent']:.2f}%" if show_cpu else "",
                    process['status'] if show_status else ""
                ])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort processes based on user selection
        sort_index = 2 if sort_by == "Memory Usage" else 3
        processes.sort(key=lambda x: float(x[sort_index].strip('%') if x[sort_index] else 0), reverse=True)
        
        # Limit to top 20 processes
        processes = processes[:20]
        
        # Create the table
        headers = ["PID", "Name", "Memory Usage", "CPU Usage", "Status"]
        table = tabulate(processes, headers=headers, tablefmt="grid")
        
        # Update the table
        table_placeholder.code(table)
        
        # Handle process termination
        if kill_button:
            try:
                process = psutil.Process(pid_to_kill)
                process.terminate()
                st.success(f"Process with PID {pid_to_kill} has been terminated.")
            except psutil.NoSuchProcess:
                st.error(f"No process found with PID {pid_to_kill}")
            except psutil.AccessDenied:
                st.error(f"Access denied to terminate process with PID {pid_to_kill}")
        
        # Wait for 1 second before updating
        time.sleep(1)


def performance_graphs():
    st.title("Performance Graphs")

    # Initialize data storage
    time_window = 60  # 60 seconds of data
    cpu_data = deque(maxlen=time_window)
    cpu_cores_data = {core: deque(maxlen=time_window) for core in range(psutil.cpu_count(logical=True))}
    memory_data = deque(maxlen=time_window)
    disk_data = deque(maxlen=time_window)
    gpu_data = deque(maxlen=time_window)
    network_sent_data = deque(maxlen=time_window)
    network_recv_data = deque(maxlen=time_window)

    # Create placeholders for graphs
    cpu_placeholder = st.empty()
    cpu_cores_placeholder = st.empty()
    memory_placeholder = st.empty()
    disk_placeholder = st.empty()
    gpu_placeholder = st.empty()
    network_placeholder = st.empty()

    # Initialize NVML for GPU monitoring
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Assuming first GPU

    while True:
        # Collect performance data
        current_time = time.time()
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        # Collect CPU core usage
        cpu_cores_percent = psutil.cpu_percent(percpu=True)
        for core, percent in enumerate(cpu_cores_percent):
            cpu_cores_data[core].append((current_time, percent))

        # GPU usage
        gpu_utilization = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu

        # Network usage
        network_stats = psutil.net_io_counters()
        network_sent = network_stats.bytes_sent
        network_recv = network_stats.bytes_recv

        # Update data storage
        cpu_data.append((current_time, cpu_percent))
        memory_data.append((current_time, memory_percent))
        disk_data.append((current_time, disk_percent))
        gpu_data.append((current_time, gpu_utilization))
        network_sent_data.append((current_time, network_sent))
        network_recv_data.append((current_time, network_recv))

        # Create and update CPU graph
        cpu_fig = go.Figure(data=go.Scatter(x=[t for t, _ in cpu_data], 
                                            y=[d for _, d in cpu_data], 
                                            mode='lines', 
                                            name='CPU Usage',
                                            line=dict(color='blue'),
                                            fill='tozeroy',
                                            fillcolor='rgba(0, 0, 255, 0.1)'))
        cpu_fig.update_layout(title='CPU Usage', xaxis_title='Time', yaxis_title='Percentage')
        cpu_placeholder.plotly_chart(cpu_fig, use_container_width=True)

        # Create and update CPU cores graph
        cpu_cores_fig = go.Figure()
        core_names = [f'Core {core}' for core in range(len(cpu_cores_data))]
        core_values = [data[-1][1] if data else 0 for data in cpu_cores_data.values()]  # Get the latest value for each core

        cpu_cores_fig.add_trace(go.Bar(
            x=core_names,
            y=core_values,
            marker_color='blue',
            opacity=0.8
        ))

        cpu_cores_fig.update_layout(
            title='CPU Cores Usage',
            xaxis_title='Cores',
            yaxis_title='Percentage',
            yaxis=dict(range=[0, 100]),  # Set y-axis range from 0 to 100%
            bargap=0.2,  # Gap between bars
        )

        cpu_cores_placeholder.plotly_chart(cpu_cores_fig, use_container_width=True)

        # Create and update Memory graph
        memory_fig = go.Figure(data=go.Scatter(x=[t for t, _ in memory_data], 
                                               y=[d for _, d in memory_data], 
                                               mode='lines', 
                                               name='Memory Usage',
                                               line=dict(color='blue'),
                                               fill='tozeroy',
                                               fillcolor='rgba(0, 0, 255, 0.1)'))
        memory_fig.update_layout(title='Memory Usage', xaxis_title='Time', yaxis_title='Percentage')
        memory_placeholder.plotly_chart(memory_fig, use_container_width=True)

        # Create and update Disk graph
        disk_fig = go.Figure(data=go.Scatter(x=[t for t, _ in disk_data], 
                                             y=[d for _, d in disk_data], 
                                             mode='lines', 
                                             name='Disk Usage',
                                             line=dict(color='blue'),
                                             fill='tozeroy',
                                             fillcolor='rgba(0, 0, 255, 0.1)'))
        disk_fig.update_layout(title='Disk Usage', xaxis_title='Time', yaxis_title='Percentage')
        disk_placeholder.plotly_chart(disk_fig, use_container_width=True)

        # Create and update GPU graph
        gpu_fig = go.Figure(data=go.Scatter(x=[t for t, _ in gpu_data], 
                                            y=[d for _, d in gpu_data], 
                                            mode='lines', 
                                            name='GPU Usage',
                                            line=dict(color='blue'),
                                            fill='tozeroy',
                                            fillcolor='rgba(0, 0, 255, 0.1)'))
        gpu_fig.update_layout(title='GPU Usage', xaxis_title='Time', yaxis_title='Percentage')
        gpu_placeholder.plotly_chart(gpu_fig, use_container_width=True)

        # Create and update Network graph
        network_fig = go.Figure()
        network_fig.add_trace(go.Scatter(x=[t for t, _ in network_sent_data], 
                                         y=[d for _, d in network_sent_data], 
                                         mode='lines', 
                                         name='Bytes Sent',
                                         line=dict(color='blue'),
                                         fill='tozeroy',
                                         fillcolor='rgba(0, 0, 255, 0.1)'))
        network_fig.add_trace(go.Scatter(x=[t for t, _ in network_recv_data], 
                                         y=[d for _, d in network_recv_data], 
                                         mode='lines', 
                                         name='Bytes Received',
                                         line=dict(color='lightblue'),
                                         fill='tozeroy',
                                         fillcolor='rgba(173, 216, 230, 0.1)'))
        network_fig.update_layout(title='Network Usage', xaxis_title='Time', yaxis_title='Bytes')
        network_placeholder.plotly_chart(network_fig, use_container_width=True)

        # Wait for 1 second before updating
        time.sleep(1)

    # Shutdown NVML
    pynvml.nvmlShutdown()




def battery_and_power_management():
    st.title("Battery and Power Management")

    # Check if battery is present
    battery = psutil.sensors_battery()
    if battery is None:
        st.warning("No battery detected. This might be a desktop computer.")
        return

    # Create placeholders for dynamic content
    battery_status = st.empty()
    battery_chart = st.empty()
    power_plan = st.empty()

    # Initialize data storage for battery percentage
    time_window = 60  # 60 seconds of data
    battery_data = deque(maxlen=time_window)

    while True:
        # Get current battery information
        battery = psutil.sensors_battery()
        percent = battery.percent
        power_plugged = battery.power_plugged
        
        # Update battery status
        status = "Charging" if power_plugged else "Discharging"
        battery_status.metric(
            "Battery Status", 
            f"{percent}% ({status})",
            f"{percent - battery_data[-1][1] if battery_data else 0:+.2f}%"
        )

        # Update battery data
        current_time = time.time()
        battery_data.append((current_time, percent))

        # Create and update battery chart
        fig = go.Figure(data=go.Scatter(
            x=[t for t, _ in battery_data],
            y=[d for _, d in battery_data],
            mode='lines+markers',
            name='Battery Percentage',
            line=dict(color='blue'),
            fill='tozeroy',
            fillcolor='rgba(0, 0, 255, 0.1)'
        ))
        fig.update_layout(
            title='Battery Percentage Over Time',
            xaxis_title='Time',
            yaxis_title='Percentage',
            yaxis=dict(range=[0, 100])
        )
        battery_chart.plotly_chart(fig, use_container_width=True)

        # Display current power plan (Note: This is a placeholder. Actual implementation may vary depending on the OS)
        power_plan.info("Current Power Plan: Balanced")

        # Estimate remaining battery time
        if not power_plugged:
            secs_left = battery.secsleft
            if secs_left != psutil.POWER_TIME_UNLIMITED:
                hours, minutes = divmod(secs_left, 3600)
                minutes, seconds = divmod(minutes, 60)
                st.info(f"Estimated time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            else:
                st.info("Battery time remaining: Calculating...")
        else:
            st.info("Power adapter is connected.")

        # Wait for 1 second before updating
        time.sleep(1)


def battery_and_power_management():
    st.title("Battery and Power Management")

    # Initialize NVML for GPU monitoring
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Assuming first GPU

    # Create placeholders for dynamic content
    power_usage = st.empty()
    battery_status = st.empty()
    battery_graph = st.empty()

    # Initialize data storage for battery percentage
    time_window = 60  # 60 seconds of data
    battery_data = deque(maxlen=time_window)

    def get_cpu_power():
        physical_cores = psutil.cpu_count(logical=False)
        freq = psutil.cpu_freq().current
        usage = psutil.cpu_percent(interval=1) / 100.0
        base_tdp = 35  # Assume a base TDP of 35W for a typical laptop CPU
        estimated_tdp = base_tdp * (freq / 2000)  # Adjust TDP based on frequency
        power = estimated_tdp * usage * physical_cores
        return max(power, 1.0)  # Ensure we always return at least 1W when the CPU is on

    def get_power_usage():
        cpu_power = get_cpu_power()
        ram_power = psutil.virtual_memory().percent * 0.3  # Rough estimate, 0.3W per GB at 100% usage
        gpu_power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # Convert mW to W
        return cpu_power, ram_power, gpu_power

    def update_power_usage():
        cpu_power, ram_power, gpu_power = get_power_usage()
        power_usage.markdown(f"""
        ### Power Usage Estimates:
        - CPU: {cpu_power:.2f} W
        - RAM: {ram_power:.2f} W
        - GPU: {gpu_power:.2f} W
        - Total: {cpu_power + ram_power + gpu_power:.2f} W
        """)

    def update_battery_status():
        battery = psutil.sensors_battery()
        if battery is None:
            battery_status.warning("No battery detected. This might be a desktop computer.")
            return None
        
        percent = battery.percent
        power_plugged = battery.power_plugged
        status = "Charging" if power_plugged else "Discharging"
        battery_status.metric(
            "Battery Status", 
            f"{percent}% ({status})",
            delta=None
        )

        current_time = datetime.now().strftime('%H:%M:%S')
        battery_data.append((current_time, percent))

        fig = go.Figure(data=go.Scatter(
            x=[t for t, _ in battery_data],
            y=[d for _, d in battery_data],
            mode='lines+markers',
            name='Battery Percentage',
            line=dict(color='blue'),
            fill='tozeroy',
            fillcolor='rgba(0, 0, 255, 0.1)'
        ))
        fig.update_layout(
            title='Battery Percentage Over Time',
            xaxis_title='Time',
            yaxis_title='Percentage',
            yaxis=dict(range=[0, 100])
        )
        battery_graph.plotly_chart(fig, use_container_width=True)

        if not power_plugged:
            secs_left = battery.secsleft
            if secs_left != psutil.POWER_TIME_UNLIMITED:
                hours, minutes = divmod(secs_left, 3600)
                minutes, seconds = divmod(minutes, 60)
                st.info(f"Estimated time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            else:
                st.info("Battery time remaining: Calculating...")
        else:
            if 'power_adapter_message_shown' not in st.session_state:
                st.info("Power adapter is connected.")
                st.session_state.power_adapter_message_shown = True


        return battery

    # Display current power plan (Note: This is a placeholder. Actual implementation may vary depending on the OS)
    st.info("Current Power Plan: Balanced")

    # Main loop for updating data
    update_interval = 5  # Update every 5 seconds
    for _ in range(12):  # Run for 1 minute (12 * 5 seconds)
        update_power_usage()
        battery = update_battery_status()
        if battery is None:
            break  # Exit loop if no battery is detected
        time.sleep(update_interval)

    # Shutdown NVML
    pynvml.nvmlShutdown()


def main():
    st.set_page_config(page_title="Task Manager", layout="wide")
    
    with st.sidebar:
        st.title("🖥️ Task Manager")
        
        selected = option_menu(
            menu_title="Navigation",
            options=["System Overview", "Process Manager", "Performance Graphs", "Battery & Power Management"],
            icons=["cpu", "list", "bar-chart", "toggle-off", "battery", "thermometer"],
            menu_icon="menu-button-wide",
            default_index=0,
            styles={
                "container": {"padding": "5px", "background-color": "#111111"},
                "icon": {"color": "#FF0000", "font-size": "20px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "color": "#FFFFFF"},
                "nav-link-selected": {"background-color": "#FF0000", "color": "#FFFFFF"},
            },
        )
    
    if selected == "System Overview":
        system_overview()
    elif selected == "Process Manager":
        process_manager()
    elif selected == "Performance Graphs":
        performance_graphs()
    elif selected == "Battery & Power Management":
        battery_and_power_management()

if __name__ == "__main__":
    main()
