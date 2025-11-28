# =============================================================================
# CPU SCHEDULING SIMULATOR - Python Backend
# =============================================================================
# Run this file using:  python scheduler_api.py
# The server will start at: http://localhost:5000
# =============================================================================

from flask import Flask, request, jsonify

app = Flask(__name__)


# =============================================================================
# FIRST COME FIRST SERVE (FCFS) ALGORITHM
# =============================================================================
# → Non-preemptive scheduling
# → Processes execute strictly in the order they arrive
# → Each process runs fully until it completes
# =============================================================================
def fcfs(processes):
    # Sort processes by arrival time (AT)
    procs = sorted(processes, key=lambda x: x['at'])
    
    time = 0                     # Tracks current timeline
    gantt = []                   # Stores Gantt chart segments
    results = []                 # Stores per-process calculations
    
    for p in procs:
        # If CPU is idle before next arrival
        if time < p['at']:
            gantt.append({
                'id': 'Idle',    # Idle block for Gantt chart
                'start': time, 
                'end': p['at'], 
                'idle': True
            })
            time = p['at']
        
        # Process execution starts here
        start = time
        end = time + p['bt']
        
        # Calculate scheduling metrics
        ct = end                        # Completion Time
        tat = ct - p['at']              # Turnaround Time = CT - AT
        wt = tat - p['bt']              # Waiting Time = TAT - BT
        rt = start - p['at']            # Response Time = first start - AT
        
        # Add Gantt block
        gantt.append({
            'id': p['id'],
            'start': start,
            'end': end,
            'idx': p['idx']
        })
        
        # Record results for this process
        results.append({
            'id': p['id'],
            'at': p['at'],
            'bt': p['bt'],
            'ct': ct,
            'tat': tat,
            'wt': wt,
            'rt': rt,
            'idx': p['idx']
        })
        
        time = end  # Move global time forward
    
    # Sort results in original order for UI display
    results.sort(key=lambda x: x['idx'])
    
    return results, gantt, time



# =============================================================================
# ROUND ROBIN (RR) ALGORITHM
# =============================================================================
# → Preemptive scheduling
# → Each process gets equal time (quantum)
# → If burst time > quantum, process goes to back of queue
# → Ensures fairness among all processes
# =============================================================================
def round_robin(processes, quantum):

    # Create extended process list (track remaining burst time)
    procs = []
    for p in sorted(processes, key=lambda x: x['at']):
        procs.append({
            'id': p['id'],
            'at': p['at'],
            'bt': p['bt'],
            'remaining': p['bt'],     # Track leftover burst time
            'first_run': -1,          # To compute response time
            'idx': p['idx']
        })
    
    time = 0
    completed = 0
    n = len(procs)
    
    i = 0                # Tracks next arriving process index
    gantt = []           # Gantt chart blocks
    queue = []           # Ready queue
    
    # Add processes that arrive at time 0
    while i < n and procs[i]['at'] <= time:
        queue.append(procs[i])
        i += 1
    
    # Core scheduling loop
    while completed < n:
        # If queue empty, CPU is idle
        if not queue:
            if i < n:
                gantt.append({
                    'id': 'Idle',
                    'start': time,
                    'end': procs[i]['at'],
                    'idle': True
                })
                time = procs[i]['at']
                
                # Add arrivals during idle time
                while i < n and procs[i]['at'] <= time:
                    queue.append(procs[i])
                    i += 1
            continue
        
        # Pick first process in queue
        curr = queue.pop(0)
        
        # Mark response time (first time CPU touches process)
        if curr['first_run'] == -1:
            curr['first_run'] = time
            curr['rt'] = time - curr['at']
        
        # Execute for min(remaining, quantum)
        exec_time = min(curr['remaining'], quantum)
        start = time
        end = time + exec_time
        
        # Add Gantt block
        gantt.append({
            'id': curr['id'],
            'start': start,
            'end': end,
            'idx': curr['idx']
        })
        
        curr['remaining'] -= exec_time
        time = end
        
        # Add processes that arrived during execution
        while i < n and procs[i]['at'] <= time:
            queue.append(procs[i])
            i += 1
        
        # If process still has burst left, requeue it
        if curr['remaining'] > 0:
            queue.append(curr)
        else:
            # Process finished
            completed += 1
            curr['ct'] = time                        # Completion Time
            curr['tat'] = curr['ct'] - curr['at']    # Turnaround Time
            curr['wt'] = curr['tat'] - curr['bt']    # Waiting Time
    
    # Build output results
    results = []
    for p in procs:
        results.append({
            'id': p['id'],
            'at': p['at'],
            'bt': p['bt'],
            'ct': p['ct'],
            'tat': p['tat'],
            'wt': p['wt'],
            'rt': p['rt'],
            'idx': p['idx']
        })
    
    results.sort(key=lambda x: x['idx'])
    
    return results, gantt, time



# =============================================================================
# HELPER FUNCTION: Average Metrics
# =============================================================================
def calc_avg(results):
    n = len(results)
    return {
        'avg_tat': round(sum(r['tat'] for r in results) / n, 2),
        'avg_wt': round(sum(r['wt'] for r in results) / n, 2),
        'avg_rt': round(sum(r['rt'] for r in results) / n, 2)
    }



# =============================================================================
# API ENDPOINT (POST /calculate)
# Receives JSON:
# {
#   "processes": [ {"id":"P1", "at":0, "bt":5}, ... ],
#   "quantum": 2
# }
# Returns:
# - FCFS results
# - RR results
# - Gantt charts
# - Metrics
# =============================================================================
@app.route('/calculate', methods=['POST', 'OPTIONS'])
def calculate():
    # Handle CORS (for frontend requests)
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    data = request.json
    
    # Attach original index to each process
    processes = []
    for i, p in enumerate(data.get('processes', [])):
        processes.append({
            'id': p['id'],
            'at': p['at'],
            'bt': p['bt'],
            'idx': i
        })
    
    quantum = data.get('quantum', 2)
    
    if not processes:
        return jsonify({'error': 'No processes provided'}), 400
    
    # Run FCFS
    fcfs_res, fcfs_gantt, fcfs_time = fcfs(processes)
    
    # Run Round Robin
    rr_res, rr_gantt, rr_time = round_robin(processes, quantum)
    
    # Build JSON response
    response = jsonify({
        'fcfs': {
            'results': fcfs_res,
            'gantt': fcfs_gantt,
            'metrics': calc_avg(fcfs_res),
            'total': fcfs_time
        },
        'rr': {
            'results': rr_res,
            'gantt': rr_gantt,
            'metrics': calc_avg(rr_res),
            'total': rr_time
        }
    })
    
    # Add CORS headers
    response.headers.add('Access-Control-Allow-Origin', '*')
    
    return response



# =============================================================================
# RUN SERVER
# =============================================================================
if __name__ == '__main__':
    print("=" * 50)
    print("CPU Scheduling API Server")
    print("Running at: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, port=5000)
