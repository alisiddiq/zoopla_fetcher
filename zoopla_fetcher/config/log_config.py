import logging

fmt = "%(asctime)s %(name)s %(levelname)s: %(message)s"

def init_stream_logger(level: int = logging.INFO):
    """
    Initialise a stream logger
    :param level: Logging level
    """
    logging.root.handlers = []
    logger = logging.getLogger('')
    logger.setLevel(level)
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(logging.Formatter(fmt))
    logger.addHandler(sh)