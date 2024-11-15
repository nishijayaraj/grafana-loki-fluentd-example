import logging
from fluent import handler



class CustomLogFW:
    """
    CustomLogFW sets up logging using OpenTelemetry with a specified service name and instance ID.
    """
    
    def __init__(self, service_name, instance_id):
        self.service_name = service_name
        self.instance_id = instance_id

        """
        Initialize the CustomLogFW with a service name and instance ID.

        :param service_name: Name of the service for logging purposes.
        :param instance_id: Unique instance ID of the service.
        """
        # Create an instance of LoggerProvider with a Resource object that includes
        # service name and instance ID, identifying the source of the logs.
        self.custom_format = {
            'host': '%(hostname)s',
            'where': '%(module)s.%(funcName)s',
            'type': '%(levelname)s',
            'stack_trace': '%(exc_text)s',
            'service': self.service_name,
            'instance_id': self.instance_id,
        }
        self.h = handler.FluentHandler(f"service.{service_name}", host='fluentd', port=24224)
        self.h2 = handler.FluentHandler(f"service.{service_name}", host='fluent-bit', port=24224)

    def __del__(self):
        self.h.close()
        self.h2.close()


    def setup_logging(self):
        """
        Set up the logging configuration.

        :return: LoggingHandler instance configured with the logger provider.
        """

        
    
        formatter = handler.FluentRecordFormatter(self.custom_format)
        self.h.setFormatter(formatter)
        self.h2.setFormatter(formatter)


        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)  # Set the desired logging level
        
        logger.addHandler(self.h)
        logger.addHandler(self.h2)  # Add both handlers to the logger
        
        return logger
