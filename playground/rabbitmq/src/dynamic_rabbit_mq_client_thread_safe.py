import pika
import threading
import time
import functools
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RABBITMQ_HOST = 'localhost'

class DynamicConsumer:
    def __init__(self, rabbitmq_host):
        self.rabbitmq_host = rabbitmq_host
        self.connection = None
        self.channel = None
        self._consuming_tags = {}  # {queue_name: consumer_tag}
        self._target_queues = set()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._consumer_thread = None
        self._is_consuming_loop_active = False # To track if start_consuming is active

    def _on_message(self, ch, method, properties, body, queue_name):
        logger.info(f"Received message from {queue_name}: {body.decode()}")
        try:
            # Simulate processing
            time.sleep(0.1) # Placeholder for actual work
            if ch.is_open: # Important check before acking
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Acked message from {queue_name}")
            else:
                logger.warning(f"Channel closed before acking message from {queue_name}. Message will be requeued.")
        except Exception as e:
            logger.error(f"Error processing or acking message from {queue_name}: {e}", exc_info=True)
            # Decide on nack or requeue strategy if ack fails

    def _ensure_connection_and_channel(self):
        """Ensures connection and channel are open. Returns True if successful."""
        try:
            if not self.connection or self.connection.is_closed:
                logger.info("Establishing new connection to RabbitMQ.")
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.rabbitmq_host,
                        blocked_connection_timeout=300, # Timeout for connection attempts
                        heartbeat=60 # Keep connection alive
                    )
                )
                logger.info("Connection established.")
                # If connection was re-established, channel is definitely gone
                self.channel = None
                self._consuming_tags = {} # Reset tags as old ones are invalid

            if not self.channel or self.channel.is_closed:
                logger.info("Opening new channel.")
                if not self.connection or self.connection.is_closed: # Should not happen if above is correct
                    logger.error("Cannot open channel, connection is closed.")
                    return False
                self.channel = self.connection.channel()
                self.channel.basic_qos(prefetch_count=1)
                logger.info("Channel opened.")
                # If channel was re-opened, consumer tags on it are gone
                self._consuming_tags = {} # Reset tags

            return True
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect/open channel: {e}")
            self.connection = None # Ensure it's marked as unusable
            self.channel = None
            return False
        except Exception as e:
            logger.error(f"Unexpected error in _ensure_connection_and_channel: {e}", exc_info=True)
            self.connection = None
            self.channel = None
            return False


    def _pika_thread_reconcile_subscriptions(self):
        """
        This method MUST be run in Pika's I/O thread (or the thread managing the BlockingConnection).
        It compares _target_queues with _consuming_tags and adjusts.
        """
        logger.debug(f"Pika Thread: Reconciling subscriptions. Current tags: {list(self._consuming_tags.keys())}, Target queues: {self._target_queues}")
        if not self.channel or self.channel.is_closed:
            logger.warning("Pika Thread: Channel not available for reconciliation. Will attempt reconnect in main loop.")
            # Trigger a potential reconnect by letting start_consuming fail or by returning
            # to the main consumer loop which will call _ensure_connection_and_channel
            if self.channel and self._is_consuming_loop_active:
                try:
                    # This is tricky with BlockingConnection if start_consuming is active.
                    # The goal is to make start_consuming return.
                    # Forcing a stop might be aggressive but necessary if channel died mid-consume.
                    logger.info("Pika Thread: Channel seems closed during reconciliation, attempting to stop consuming loop.")
                    self.channel.stop_consuming() # This might raise if channel truly gone
                except Exception as e_stop:
                    logger.error(f"Pika Thread: Error trying to stop_consuming on closed channel: {e_stop}")
            return # Exit reconciliation, main loop will handle channel/connection recovery

        try:
            current_subscribed_queues = set(self._consuming_tags.keys())
            # Use copies of target_queues for safety if it's modified elsewhere, though lock should protect
            with self._lock:
                target_queues_copy = self._target_queues.copy()

            queues_to_subscribe = target_queues_copy - current_subscribed_queues
            queues_to_unsubscribe = current_subscribed_queues - target_queues_copy

            # Unsubscribe
            for queue_name in queues_to_unsubscribe:
                consumer_tag = self._consuming_tags.pop(queue_name, None)
                if consumer_tag and self.channel.is_open: # Double check channel
                    try:
                        logger.info(f"Pika Thread: Unsubscribing from {queue_name} (tag: {consumer_tag})")
                        self.channel.basic_cancel(consumer_tag)
                        logger.info(f"Pika Thread: Successfully cancelled {consumer_tag} for {queue_name}")
                    except pika.exceptions.AMQPChannelError as e: # Channel might have closed during ops
                        logger.error(f"Pika Thread: Channel error cancelling {queue_name}: {e}. Marking channel for re-open.")
                        self.channel = None # Force re-open in main loop
                        return # Exit, let main loop handle
                    except Exception as e:
                        logger.error(f"Pika Thread: Error cancelling consumer for {queue_name} (tag: {consumer_tag}): {e}")
                elif not consumer_tag:
                    logger.warning(f"Pika Thread: No consumer tag found for {queue_name} during unsubscribe attempt.")

            # Subscribe
            for queue_name in queues_to_subscribe:
                if self.channel.is_open: # Double check channel
                    try:
                        # logger.info(f"Pika Thread: Declaring queue {queue_name}")
                        # self.channel.queue_declare(queue=queue_name, durable=True)
                        callback = functools.partial(self._on_message, queue_name=queue_name)
                        consumer_tag = self.channel.basic_consume(
                            queue=queue_name,
                            on_message_callback=callback,
                            auto_ack=False
                        )
                        self._consuming_tags[queue_name] = consumer_tag
                        logger.info(f"Pika Thread: Subscribed to {queue_name} with tag {consumer_tag}")
                    except pika.exceptions.AMQPChannelError as e: # Channel might have closed
                        logger.error(f"Pika Thread: Channel error subscribing to {queue_name}: {e}. Marking channel for re-open.")
                        self.channel = None # Force re-open in main loop
                        return # Exit, let main loop handle
                    except Exception as e:
                        logger.error(f"Pika Thread: Error subscribing to queue {queue_name}: {e}")
                else: # Channel closed mid-reconciliation
                    logger.error(f"Pika Thread: Channel closed before subscribing to {queue_name}. Will retry.")
                    self.channel = None # Mark for re-open
                    return # Exit, let main loop handle

            logger.debug(f"Pika Thread: Reconciliation complete. Current tags: {list(self._consuming_tags.keys())}")

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Pika Thread: Connection error during reconciliation: {e}")
            self.connection = None # Mark for re-connect
            self.channel = None
        except pika.exceptions.AMQPChannelError as e:
            logger.error(f"Pika Thread: Channel error during reconciliation: {e}")
            self.channel = None # Mark for re-open
        except Exception as e:
            logger.error(f"Pika Thread: Unexpected error during reconciliation: {e}", exc_info=True)


    def update_target_queues(self, new_target_queues: set):
        """
        Called by the external monitoring mechanism (from any thread).
        Schedules the reconciliation to happen in Pika's I/O thread.
        """
        reconcile_needed = False
        with self._lock:
            if self._target_queues != new_target_queues:
                logger.info(f"Monitor Thread: Updating target queues from {self._target_queues} to: {new_target_queues}")
                self._target_queues = new_target_queues.copy()
                reconcile_needed = True
            else:
                logger.debug(f"Monitor Thread: Target queues unchanged: {new_target_queues}")


        if reconcile_needed:
            if self.connection and self.connection.is_open and not self._stop_event.is_set():
                try:
                    self.connection.add_callback_threadsafe(self._pika_thread_reconcile_subscriptions)
                    logger.info("Monitor Thread: Scheduled subscription reconciliation.")
                except Exception as e:
                    logger.error(f"Monitor Thread: Error scheduling reconciliation: {e}. Reconciliation will be attempted by main loop.")
            elif not self._stop_event.is_set():
                logger.warning("Monitor Thread: Connection not available to schedule reconciliation. "
                               "Reconciliation will be attempted by main consumer loop on next cycle.")
            # If stopping, don't schedule new work.


    def _run_consumer_loop(self):
        """The main loop for the Pika consumer thread."""
        logger.info("Consumer Loop: Starting.")
        while not self._stop_event.is_set():
            if not self._ensure_connection_and_channel():
                logger.warning("Consumer Loop: Failed to ensure connection/channel. Retrying in 5s.")
                if self._stop_event.wait(5): break # Wait or break if stop is set
                continue

            try:
                # Always reconcile after ensuring connection/channel, or if changes were missed
                logger.info("Consumer Loop: Performing subscription reconciliation before starting consume loop.")
                self._pika_thread_reconcile_subscriptions() # Safe to call directly here

                if not self.channel or self.channel.is_closed:
                    logger.warning("Consumer Loop: Channel became invalid after reconciliation attempt. Retrying connection setup.")
                    time.sleep(1) # Small delay before retrying connection setup
                    continue

                if not self._consuming_tags and not self._target_queues: # Added check for target_queues
                    logger.info("Consumer Loop: No queues to consume from currently. Waiting for updates...")
                    # Process pika events to allow add_callback_threadsafe to run
                    # and check stop_event periodically.
                    wait_interval = 1.0 # seconds
                    deadline = time.monotonic() + wait_interval
                    while time.monotonic() < deadline and not self._stop_event.is_set():
                        if self.connection and self.connection.is_open:
                            self.connection.process_data_events(time_limit=0.1) # Non-blocking check for callbacks
                        if self._stop_event.wait(0.1): break # Check stop event
                    if self._stop_event.is_set(): break
                    continue # Re-check target queues in the next iteration

                if self._consuming_tags: # Only start consuming if there are actual subscriptions
                    logger.info(f"Consumer Loop: Starting Pika's internal I/O loop (start_consuming) for queues: {list(self._consuming_tags.keys())}.")
                    self._is_consuming_loop_active = True
                    self.channel.start_consuming() # Blocking call
                    self._is_consuming_loop_active = False
                    logger.info("Consumer Loop: start_consuming returned.")
                else:
                    # This case should ideally be caught by the above 'no queues to consume' block
                    logger.info("Consumer Loop: No active consumers after reconciliation, but target queues might exist. Will re-evaluate.")
                    time.sleep(1) # Brief pause before re-evaluating

            except (pika.exceptions.AMQPConnectionError, pika.exceptions.StreamLostError) as e:
                logger.error(f"Consumer Loop: Connection error: {e}. Resetting connection.")
                self.connection = None # Mark for full reconnect
                self.channel = None
                self._consuming_tags = {} # Tags are invalid
                self._is_consuming_loop_active = False
                if self._stop_event.wait(5): break
            except pika.exceptions.AMQPChannelError as e:
                logger.error(f"Consumer Loop: Channel error: {e}. Resetting channel.")
                self.channel = None # Mark for channel re-open
                self._consuming_tags = {} # Tags on this channel are invalid
                self._is_consuming_loop_active = False
                if self._stop_event.wait(1): break # Shorter wait for channel issues
            except Exception as e: # Catch-all for other unexpected issues
                logger.error(f"Consumer Loop: Unexpected error: {e}. Retrying in 5s.", exc_info=True)
                self._is_consuming_loop_active = False
                # Potentially reset connection/channel depending on the error
                self.connection = None
                self.channel = None
                self._consuming_tags = {}
                if self._stop_event.wait(5): break

        logger.info("Consumer Loop: Stop event set or loop exited. Cleaning up.")
        self._is_consuming_loop_active = False
        self._cleanup_pika_resources()
        logger.info("Consumer Loop: Finished.")


    def _cleanup_pika_resources(self):
        logger.info("Cleaning up Pika resources...")
        # Try to stop consuming loop if it was somehow still active and channel exists
        # This is a safeguard.
        if self._is_consuming_loop_active and self.channel and self.channel.is_open:
            try:
                logger.info("Cleanup: Attempting to stop consuming loop.")
                self.channel.stop_consuming()
            except Exception as e_stop:
                logger.warning(f"Cleanup: Error during final stop_consuming: {e_stop}")
        self._is_consuming_loop_active = False

        # Cancel remaining consumers if channel is still open
        if self.channel and self.channel.is_open:
            for queue_name, tag in list(self._consuming_tags.items()):
                logger.info(f"Cleanup: Cancelling consumer {tag} for {queue_name}")
                try:
                    self.channel.basic_cancel(tag)
                except Exception as e_cancel:
                    logger.error(f"Cleanup: Error cancelling consumer {tag} for {queue_name}: {e_cancel}")
            self._consuming_tags.clear()
            try:
                logger.info("Cleanup: Closing channel.")
                self.channel.close()
            except Exception as e:
                logger.error(f"Cleanup: Error closing channel: {e}")
        self.channel = None

        if self.connection and self.connection.is_open:
            try:
                logger.info("Cleanup: Closing connection.")
                self.connection.close()
            except Exception as e:
                logger.error(f"Cleanup: Error closing connection: {e}")
        self.connection = None
        logger.info("Pika resources cleanup complete.")


    def start(self):
        if self._consumer_thread and self._consumer_thread.is_alive():
            logger.warning("Consumer is already running.")
            return

        self._stop_event.clear()
        self._consumer_thread = threading.Thread(target=self._run_consumer_loop, name="PikaConsumerLoopThread")
        self._consumer_thread.daemon = True
        self._consumer_thread.start()
        logger.info("DynamicConsumer started.")

    def stop(self):
        logger.info("DynamicConsumer stop requested.")
        self._stop_event.set()

        # For BlockingConnection, signalling the thread via _stop_event is the primary way.
        # If start_consuming is blocking, it will only exit on error or explicit stop_consuming
        # from within a Pika callback or if the connection dies.
        # We can try to schedule a stop_consuming if the connection is still there.
        if self.connection and self.connection.is_open:
            def final_stop_consuming_callback():
                if self.channel and self.channel.is_open and self._is_consuming_loop_active: # Check if consuming
                    logger.info("Pika Thread (on stop): Executing final stop_consuming.")
                    try:
                        self.channel.stop_consuming()
                    except Exception as e:
                        logger.error(f"Pika Thread (on stop): Error in final stop_consuming: {e}")
            try:
                self.connection.add_callback_threadsafe(final_stop_consuming_callback)
            except Exception as e:
                logger.error(f"Error scheduling final stop_consuming on stop request: {e}")


        if self._consumer_thread and self._consumer_thread.is_alive():
            logger.info("Waiting for consumer thread to join...")
            self._consumer_thread.join(timeout=15) # Increased timeout
            if self._consumer_thread.is_alive():
                logger.warning("Consumer thread did not exit cleanly after timeout during stop.")
        logger.info("DynamicConsumer stop processing finished.")

# --- Example Usage (same as before) ---
def queue_monitor_simulation(consumer: DynamicConsumer):
    """Simulates an external mechanism that changes queue assignments."""
    threading.current_thread().name = "QueueMonitorThread"
    queue_sets = [  # test cases
        {'q0001', },
        {'q0001', 'q0005'},
        {'q0002', 'q0003','q0004'},
        {'q0004', 'q0005'},
        set(), # Unsubscribe from all
        {'q0006'} # Unknown queue
    ]
    for i, q_set in enumerate(queue_sets):
        if consumer._stop_event.is_set(): # Check if consumer is stopping
            logger.info("Monitor: Consumer is stopping, exiting monitor simulation.")
            break
        logger.info(f"Monitor: Simulating change {i+1}. Target queues: {q_set}")
        consumer.update_target_queues(q_set) # This will schedule reconciliation
        print("-----------------------------------------------------------------------------------")
        if consumer._stop_event.wait(15): # Wait, but break if consumer stops
            logger.info("Monitor: Consumer stopping during wait, exiting monitor simulation.")
            break
    logger.info("Monitor: Simulation finished.")
    if not consumer._stop_event.is_set(): # Only stop if not already stopping
        logger.info("Monitor: Requesting consumer to stop.")
        consumer.stop()


if __name__ == "__main__":
    dynamic_consumer = DynamicConsumer(rabbitmq_host=RABBITMQ_HOST)
    dynamic_consumer.start()

    # Give the consumer a moment to connect
    time.sleep(3) # Slightly longer for initial setup

    # Start the simulation of queue changes in a separate thread
    monitor_thread = threading.Thread(target=queue_monitor_simulation, args=(dynamic_consumer,))
    monitor_thread.start()

    try:
        # Keep the main thread alive while the monitor and consumer run
        monitor_thread.join() # Wait for monitor to finish
    except KeyboardInterrupt:
        logger.info("Main: KeyboardInterrupt received. Stopping consumer.")
        dynamic_consumer.stop() # Signal consumer to stop

    # Final wait for consumer thread if it's still running (e.g. after KeyboardInterrupt)
    if dynamic_consumer._consumer_thread and dynamic_consumer._consumer_thread.is_alive():
        logger.info("Main: Waiting for consumer to fully stop.")
        dynamic_consumer._consumer_thread.join(timeout=10)

    logger.info("Main: Application exiting.")