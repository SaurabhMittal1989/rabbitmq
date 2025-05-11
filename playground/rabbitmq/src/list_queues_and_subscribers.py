import requests
from requests.auth import HTTPBasicAuth


def rest_queue_list(user='guest', password='guest', host='localhost', port=15672, virtual_host=None):
    url = 'http://%s:%s/api/queues/%s' % (host, port, virtual_host or '')
    response = requests.get(url, auth=(user, password))
    queues = [q['name'] for q in response.json()]
    return queues


def list_consumers(queue_name, user='guest', password='guest', host='localhost', port=15672, virtual_host='%2F'):
    api_queues = 'http://' + host + ':' + str(port) + '/api/queues/' + virtual_host + '/' + queue_name
    res = requests.get(api_queues, auth=HTTPBasicAuth(user, password))
    res_json = res.json()
    # Number of consumers
    return res_json['consumer_details']


if __name__ == "__main__":
    queues = rest_queue_list()
    for queue in sorted(queues):
        print(queue)
        consumers = list_consumers(queue_name=queue)
        print([(consumer["consumer_tag"] if len(consumer) else None) for consumer in consumers])
