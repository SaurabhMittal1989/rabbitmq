import time
import  multiprocessing

p_list =[]


def start_consumer(queue_names):
    # dont block

    global p_list

    p = multiprocessing.Process(target=do_job,args=(queue_names,))
    p.start()
    p_list.append(p)

def do_job(queue_names):
    print(f"Starting Consumer {queue_names}")
    i=0
    while True:
        # blocking
        time.sleep(10)
        i=i+1
        print(f"{i} Consuming messages {queue_names}")


def stop_consumer(*args):
    print(f"Stopping Consumer {args}")
    time.sleep(2)
    global p_list
    for p in p_list:
        print(f"Terminating Consumer {p}")
        if  p.is_alive():
            p.terminate()
            print(f"Terminated Consumer {p}")

    print(f"Stopped Consumer")

def dummy_job():
    print("Started dummy job")

# r = multiprocessing.Process(target=dummy_job)
# r.start()