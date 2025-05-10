# rabbitmq

## Setup:

Step 1: Install Redis
Step 2: Install  RabbitMQ 
Step 3: Install Terminator
Step 4: Start Redis
Step 5: StartRabbitmq => Make a consistent hash exchange

## Make Clients:
1. Redis Client
2. RabbitMq cLient

## Simplifications

1. Redis Leader Election: Leader prints 'I am Leader', Follower prints 'I am Leader'
2. Leader Callback Utils: get_assignment_config(), set assignment_config(), get_state(), , get_all_stopped(), get_all_running(), leader_callback()
3. Leader Callback()
4. Follower Utils: get_assignment_config(), get_state(), subscribe(), unsubscribe()
5. Follower Callback : print I am consuming
6. Make two threads: leader.py and follower.py code to run on 2 threads


![image](https://github.com/user-attachments/assets/eed7cb02-7731-4099-b6fa-08fda9d991a0)

![image](https://github.com/user-attachments/assets/352b2fc0-2dd9-4559-ba1d-48c4a4093ce9)



