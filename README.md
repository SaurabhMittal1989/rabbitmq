# rabbitmq

## Setup:
Step 1: Install Redis
Step 2: Install  RabbitMQ 
Step 3: Install Terminator
Step 4: Start Redis
Step 5: StartRabbitmq => Make a consistent hash exchange

1. Redis Client
2. RabbitMq cLient
3. Redis Leader Election: Leader prints 'I am Leader', Follower prints 'I am Leader'
4. Leader Callback Utils: get_assignment_config(), set assignment_config(), get_state(), , get_all_stopped(), get_all_running(), leader_callback()
5. Leader Callback()
6. Follower Utils: get_assignment_config(), get_state(), subscribe(), unsubscribe()
7. Follower Callback : print I am consuming
8. Make two threads: leader.py and follower.py code to run on 2 threads


![image](https://github.com/user-attachments/assets/54cc4bc7-3391-4733-b5e2-cccc5140a54a)
